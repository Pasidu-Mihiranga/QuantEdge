"""Return conventions and portfolio accounting (Step 04).

    asset simple return     R_i,t = P_i,t / P_i,t-1 - 1            aggregation across assets
    portfolio simple return R_p,t = sum_i w_i,t-1 R_i,t           exact
    portfolio log return    r_p,t = ln(1 + R_p,t)                 statistics on one series
    loss                    l_t = -R_p,t  (positive = loss);  L_t = l_t x NAV in USD

Two portfolio series are kept apart:
    performance series  drifting weights, quarterly rebalance, costs   -> KPIs, drawdown
    risk series         fixed (current / point-in-time) weights          -> VaR, ES, EVT, backtests
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

CASH = "CASH"


def simple_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """R_t = P_t / P_{t-1} - 1; the first (undefined) row is dropped."""
    return prices.pct_change(fill_method=None).iloc[1:]


def log_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """r_t = ln(P_t / P_{t-1}); for single-series statistics only, never summed across assets."""
    return np.log(prices).diff().iloc[1:]


def risk_free_daily(dtb3_pct: pd.Series, index: pd.DatetimeIndex) -> pd.Series:
    """Daily risk-free return from the 3-month T-bill discount rate, lagged one trading day.

    d = DTB3 / 100 (bank-discount, 360-day basis, 91-day bill)
    BEY = 365 d / (360 - 91 d)
    rf_t = (1 + BEY)^(1/252) - 1, using the rate known at t-1 (no look-ahead)
    """
    d = dtb3_pct.reindex(index, method="ffill") / 100.0
    bey = 365.0 * d / (360.0 - 91.0 * d)
    daily = (1.0 + bey) ** (1.0 / 252.0) - 1.0
    return daily.shift(1).bfill(limit=1).rename("rf")


def add_cash_asset(returns: pd.DataFrame, rf: pd.Series) -> pd.DataFrame:
    """Append a synthetic T-bill sleeve (return = rf, zero volatility) as the CASH column."""
    return returns.assign(**{CASH: rf.reindex(returns.index)})


def _weights(weights: dict[str, float] | pd.Series, columns: pd.Index) -> pd.Series:
    w = pd.Series(weights, dtype=float)
    missing = set(w.index) - set(columns)
    if missing:
        raise ValueError(f"weights reference tickers not in the returns: {sorted(missing)}")
    if abs(w.sum() - 1.0) > 1e-8:
        raise ValueError(f"weights must sum to 1, got {w.sum():.10f}")
    return w.reindex(columns, fill_value=0.0)


def risk_series(returns: pd.DataFrame, weights: dict[str, float] | pd.Series) -> pd.Series:
    """R_risk,t = sum_i w_i R_i,t with fixed weights: what today's portfolio would have experienced."""
    w = _weights(weights, returns.columns)
    return (returns * w).sum(axis=1, min_count=1).rename("portfolio")


def rebalance_flags(index: pd.DatetimeIndex, rule: str | None) -> np.ndarray:
    """True on rebalance days: last trading day of each quarter ('Q'), month ('M'), every day ('D')."""
    if rule in (None, "none"):
        return np.zeros(len(index), dtype=bool)
    if rule == "D":
        return np.ones(len(index), dtype=bool)
    if rule in ("Q", "quarterly"):
        period = index.to_period("Q")
    elif rule in ("M", "monthly"):
        period = index.to_period("M")
    else:
        raise ValueError(f"unknown rebalance rule {rule!r}")
    nxt = np.append(period[1:].to_numpy(), None)
    return period.to_numpy() != nxt


@dataclass(frozen=True)
class PerfResult:
    returns: pd.Series
    values: pd.Series
    weights_path: pd.DataFrame
    turnover: pd.Series
    costs: pd.Series


def performance_series(returns: pd.DataFrame, weights: dict[str, float] | pd.Series,
                       rebalance: str | None = "Q", cost_bps: float = 5.0) -> PerfResult:
    """Drifting-weights portfolio with periodic rebalancing and proportional costs.

    V_i,t = V_i,t-1 (1 + R_i,t); on a rebalance day: target = w* V_t,
    cost = c sum_i |target_i - V_i,t| (c = cost_bps / 1e4, per side), V_i,t = target_i - cost w*_i.
    ETF expense ratios are already in the prices and are not deducted again.
    """
    w = _weights(weights, returns.columns).to_numpy()
    r = returns.to_numpy()
    flags = rebalance_flags(returns.index, rebalance)
    c = cost_bps / 1e4
    v = w.copy()
    n = len(r)
    total = np.empty(n)
    wpath = np.empty_like(r)
    turnover = np.zeros(n)
    costs = np.zeros(n)
    for t in range(n):
        v = v * (1.0 + r[t])
        if flags[t]:
            tot = v.sum()
            target = w * tot
            traded = np.abs(target - v).sum()
            cost = c * traded
            v = target - cost * w
            turnover[t] = traded / tot
            costs[t] = cost / tot
        total[t] = v.sum()
        wpath[t] = v / total[t]
    values = pd.Series(total, index=returns.index, name="value")
    perf = values.pct_change()
    perf.iloc[0] = values.iloc[0] - 1.0
    return PerfResult(
        returns=perf.rename("portfolio"),
        values=values,
        weights_path=pd.DataFrame(wpath, index=returns.index, columns=returns.columns),
        turnover=pd.Series(turnover, index=returns.index, name="turnover"),
        costs=pd.Series(costs, index=returns.index, name="cost"),
    )


def to_usd(loss_fraction: float | pd.Series, nav: float) -> float | pd.Series:
    """Loss in USD on the given NAV (positive = loss)."""
    return loss_fraction * nav


def horizon_returns(r: pd.Series, h: int, overlapping: bool = True) -> pd.Series:
    """Compounded h-day simple returns: prod(1 + R) - 1 over each h-day block."""
    agg = np.expm1(np.log1p(r).rolling(h).sum()).dropna()
    return agg if overlapping else agg.iloc[::h]


def build_returns(prices: pd.DataFrame, macro: pd.DataFrame, write: bool = True) -> dict[str, pd.DataFrame]:
    """Asset simple and log returns plus the daily risk-free rate, persisted as artifacts.

    Analysis code must read these through `quantedge.data.partition.load_returns(split)`.
    """
    from quantedge.paths import ARTIFACTS

    simple = simple_returns(prices)
    out = {
        "simple": simple,
        "log": log_returns(prices),
        "rf": risk_free_daily(macro["DTB3"], simple.index).to_frame(),
    }
    if write:
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        for name, df in out.items():
            df.to_parquet(ARTIFACTS / f"returns_{name}.parquet")
    return out
