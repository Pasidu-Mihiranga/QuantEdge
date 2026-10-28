"""Walk-forward portfolio construction and the pre-declared selection scorecard (Step 07 §3.4–3.5).

At each quarter-end rebalance date tau the strategy sees only returns dated <= tau; the new
weights apply from the next trading day. Costs of 5 bps per side are charged on every trade.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd

from quantedge.config import Config
from quantedge.decision.ips import IPSLimits, OptimizerConstraints, constraints_for_optimizer
from quantedge.portfolio import metrics
from quantedge.portfolio import optimize as opt
from quantedge.portfolio.returns import rebalance_flags

Strategy = Callable[[pd.DataFrame, float], opt.OptResult]


@dataclass(frozen=True)
class WFResult:
    name: str
    perf: pd.Series                 # daily performance returns after the first rebalance
    weights_history: pd.DataFrame   # target weights, indexed by rebalance date tau
    turnover: pd.Series             # one-way traded fraction of NAV at each rebalance
    statuses: pd.Series             # optimiser status at each rebalance


def rebalance_dates(index: pd.DatetimeIndex, window: int, rule: str = "Q") -> pd.DatetimeIndex:
    """Quarter-end trading days with at least `window` observations up to and including them."""
    flags = rebalance_flags(index, rule)
    flags[: window - 1] = False
    flags[-1] = False  # a rebalance on the last day would never be applied
    return index[flags]


def simulate(returns: pd.DataFrame, weights_history: pd.DataFrame, cost_bps: float
             ) -> tuple[pd.Series, pd.Series]:
    """Daily performance of drifting positions, rebalanced to `weights_history` rows on their dates."""
    taus = weights_history.index
    r = returns.loc[returns.index > taus[0], weights_history.columns]
    c = cost_bps / 1e4
    v = weights_history.iloc[0].to_numpy(dtype=float).copy()
    targets = {tau: weights_history.loc[tau].to_numpy(dtype=float) for tau in taus[1:]}
    out = np.empty(len(r))
    turnover = {taus[0]: 1.0}
    total_prev = 1.0
    for i, (date, row) in enumerate(zip(r.index, r.to_numpy(), strict=True)):
        v = v * (1.0 + row)
        if date in targets:
            tot = v.sum()
            target = targets[date] * tot
            traded = np.abs(target - v).sum()
            v = target - c * traded * targets[date]
            turnover[date] = traded / tot / 2.0
        total = v.sum()
        out[i] = total / total_prev - 1.0
        total_prev = total
    return pd.Series(out, index=r.index, name="portfolio"), pd.Series(turnover, name="turnover")


def walk_forward(returns: pd.DataFrame, strategy: Strategy, rf_daily: pd.Series,
                 window: int = 756, rebalance: str = "Q", cost_bps: float = 5.0,
                 name: str = "") -> WFResult:
    weights, statuses = {}, {}
    for tau in rebalance_dates(returns.index, window, rebalance):
        est = returns.loc[:tau].iloc[-window:]
        assert est.index.max() <= tau, "look-ahead: estimation window extends past the rebalance date"
        rf_annual = float((1.0 + rf_daily.loc[:tau].iloc[-1]) ** 252 - 1.0)
        res = strategy(est, rf_annual)
        weights[tau] = res.weights.reindex(returns.columns, fill_value=0.0)
        statuses[tau] = res.status
    wh = pd.DataFrame(weights).T
    wh.index.name = "rebalance_date"
    perf, turnover = simulate(returns, wh, cost_bps)
    return WFResult(name, perf.rename(name or "portfolio"), wh, turnover, pd.Series(statuses))


def candidate_strategies(cfg: Config, limits: IPSLimits, tickers: list[str], mrp: float = 0.05
                         ) -> tuple[dict[str, Strategy], OptimizerConstraints]:
    """The seven Step 07 candidates plus the pre-registered frontier point (`portfolio.frontier_equity`)
    as walk-forward strategies (`mrp`: CAPM market risk premium)."""
    cons = constraints_for_optimizer(limits, tickers)
    market = cfg.market_proxy

    def inputs(est, rf):
        return opt.estimate_inputs(est, rf, market=market, mrp=mrp)

    strategies: dict[str, Strategy] = {
        "Equal weight": lambda est, rf: opt.equal_weight(tickers),
        "60/40 benchmark": lambda est, rf: opt.fixed(cfg.benchmark, tickers),
        "Global min variance": lambda est, rf: opt.gmv(inputs(est, rf)[1], cons),
        "Max Sharpe": lambda est, rf: opt.max_sharpe(*inputs(est, rf), rf, cons),
        "Risk parity (ERC)": lambda est, rf: opt.erc(inputs(est, rf)[1], cons),
        "Min CVaR": lambda est, rf: opt.min_cvar(est, cons, alpha=0.99),
        "Robust Mean-ES": lambda est, rf: opt.robust_mean_es(
            *inputs(est, rf), est, cons, es_budget=limits.es99_1d_max,
            vol_max=limits.vol_ann_max, alpha=0.99),
    }
    x = cfg.portfolio.frontier_equity
    if x is not None and frontier_feasible(limits, tickers, x):   # e.g. not under the AGG <= 40% sensitivity
        strategies[frontier_name(x)] = lambda est, rf: opt.min_var_at_equity(
            inputs(est, rf)[1], cons, list(limits.equity_group), x)
    return strategies, cons


def frontier_feasible(limits: IPSLimits, tickers: list[str], equity_share: float) -> bool:
    """Can the caps hold exactly `equity_share` in equities and the rest outside them?"""
    eq = [t for t in tickers if t in limits.equity_group]
    rest = [t for t in tickers if t not in limits.equity_group]
    return (equity_share <= min(limits.equity_max, sum(limits.cap(t) for t in eq)) + 1e-12
            and 1.0 - equity_share <= sum(limits.cap(t) for t in rest) + 1e-12)


def frontier_name(equity_share: float) -> str:
    return f"Frontier {equity_share:.0%} equity"


def historical_es(r: pd.Series, alpha: float = 0.99) -> float:
    """Mean loss beyond the alpha-quantile of losses (positive number)."""
    loss = -r.dropna()
    var = loss.quantile(alpha)
    return float(loss[loss >= var].mean())


def worst_window_drawdown(r: pd.Series, windows: dict[str, tuple[str, str]]) -> tuple[float, str]:
    """Deepest max drawdown (positive) inside any crisis window covered by `r`."""
    worst, which = 0.0, "none covered"
    for name, (start, end) in windows.items():
        seg = r.loc[(r.index > pd.Timestamp(start)) & (r.index <= pd.Timestamp(end))]  # path after the peak close
        if len(seg) < 5:
            continue
        dd = -metrics.max_drawdown(seg)
        if dd > worst:
            worst, which = dd, name
    return worst, which


def scorecard(results: dict[str, WFResult], limits: IPSLimits, required_return: float,
              crisis_windows: dict[str, tuple[str, str]], end: pd.Timestamp,
              rf: pd.Series | float) -> pd.DataFrame:
    """Pre-declared selection scorecard on out-of-sample results up to `end`.

    Order: IPS pass/fail first, then the average rank of OOS 99% ES and max drawdown (capital
    preservation), then Calmar as the tie-breaker. Selection must use end <= 2022-12-31 (Step 22).
    """
    rows = []
    for name, res in results.items():
        r = res.perf.loc[:end]
        years = len(r) / 252
        es = historical_es(r)
        mdd = -metrics.max_drawdown(r)
        crisis_dd, crisis_name = worst_window_drawdown(r, crisis_windows)
        weight_checks = [c for _, w in res.weights_history.loc[:end].iterrows()
                         for c in limits.check({"weights": w})]
        weights_ok = all(c.passed for c in weight_checks)
        vol = metrics.volatility(r)
        ips_pass = bool(weights_ok and vol <= limits.vol_ann_max and es <= limits.es99_1d_max
                        and crisis_dd <= limits.stress_drawdown_max)
        rows.append({
            "candidate": name, "oos_start": r.index.min().date(), "oos_end": r.index.max().date(),
            "es99_oos": es, "max_drawdown": mdd, "calmar": metrics.calmar(r),
            "worst_crisis_drawdown": crisis_dd, "worst_crisis": crisis_name,
            "turnover_ann": float(res.turnover.loc[:end].iloc[1:].sum() / years),
            "cagr": metrics.cagr(r), "vs_required": metrics.cagr(r) - required_return,
            "volatility": vol, "sharpe": metrics.sharpe(r, rf), "weights_within_ips": weights_ok,
            "ips_pass": ips_pass,
        })
    card = pd.DataFrame(rows).set_index("candidate")
    card["preservation_rank"] = (card["es99_oos"].rank() + card["max_drawdown"].rank()) / 2
    card = card.sort_values(["ips_pass", "preservation_rank", "calmar"], ascending=[False, True, False])
    card["rank"] = np.arange(1, len(card) + 1)
    return card


def bootstrap_weights(window: pd.DataFrame, strategy: Strategy, rf_annual: float, rng: np.random.Generator,
                      n: int = 200, block: int = 20) -> pd.DataFrame:
    """Stationary block bootstrap (mean block length `block`) of the estimation window,
    re-optimised on each resample; returns one row of weights per resample."""
    T = len(window)
    p = 1.0 / block
    data = window.to_numpy()
    rows = []
    for _ in range(n):
        idx = np.empty(T, dtype=int)
        idx[0] = rng.integers(T)
        for t in range(1, T):
            idx[t] = rng.integers(T) if rng.random() < p else (idx[t - 1] + 1) % T
        sample = pd.DataFrame(data[idx], index=window.index, columns=window.columns)
        rows.append(strategy(sample, rf_annual).weights)
    return pd.DataFrame(rows).reset_index(drop=True)
