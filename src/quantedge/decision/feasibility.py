"""IPS feasibility study across the frontier (data <= 2022-12-31 only).

Can any IPS-compliant portfolio meet both the return objective and the risk limits? For each point
on the IPS-constrained mean-variance frontier, plus the full-sample minimum-ES portfolio:

- expected return: CAPM prior mu_i = rf + beta_i x MRP (the optimiser's own estimate), w'mu;
- realised over the sample: CAGR, annualised volatility, historical 99% 1-day ES
  (mean loss beyond the 99% loss quantile) and the worst drawdown in the historical stress windows;
- each risk figure is checked against its IPS limit, and w'mu against the required return.

Weights are held fixed (daily rebalanced) and chosen on the same sample they are evaluated on, so
this is an optimistic feasibility screen, not a backtest: a limit that no portfolio meets even
in-sample is infeasible. If no portfolio meets both the objective and the limits, that conflict is
the finding (Step 05 §3.5) and the verdict becomes "adjust".
"""

from __future__ import annotations

import pandas as pd

from quantedge.decision.ips import IPSLimits, constraints_for_optimizer
from quantedge.portfolio import metrics
from quantedge.portfolio import optimize as opt
from quantedge.portfolio.walkforward import historical_es, worst_window_drawdown

RISK_CHECKS = {"vol_ok": ("volatility", "vol_ann_max"), "es_ok": ("es99_1d", "es99_1d_max"),
               "stress_ok": ("stress_drawdown", "stress_drawdown_max")}


def evaluate(weights: pd.Series, returns: pd.DataFrame, windows: dict[str, tuple[str, str]]) -> dict:
    """Realised risk and return of fixed weights: R_p,t = sum_i w_i R_i,t (simple returns)."""
    r = returns[weights.index] @ weights
    dd, crisis = worst_window_drawdown(r, windows)
    return {"cagr": metrics.cagr(r), "volatility": metrics.volatility(r), "es99_1d": historical_es(r),
            "stress_drawdown": dd, "worst_crisis": crisis}


def frontier_feasibility(returns: pd.DataFrame, rf_annual: float, limits: IPSLimits, required_return: float,
                         windows: dict[str, tuple[str, str]], market: str = "SPY", mrp: float = 0.045,
                         n: int = 25) -> pd.DataFrame:
    """One row per frontier point (and the minimum-ES portfolio) with every IPS check."""
    tickers = list(returns.columns)
    cons = constraints_for_optimizer(limits, tickers)
    mu, sigma = opt.estimate_inputs(returns, rf_annual, market=market, mrp=mrp)
    front = opt.efficient_frontier(mu, sigma, cons, n=n)
    points = [(f"frontier {i + 1:02d}", row[tickers].astype(float)) for i, (_, row) in enumerate(front.iterrows())]
    points.append(("Min ES (full sample)", opt.min_cvar(returns, cons, alpha=0.99).weights))
    rows = []
    for label, w in points:
        w = w.clip(lower=0.0) / w.clip(lower=0.0).sum()
        row = {"point": label, "expected_return": float(mu[tickers] @ w), **evaluate(w, returns, windows)}
        for flag, (col, lim) in RISK_CHECKS.items():
            row[flag] = row[col] <= getattr(limits, lim) + 1e-12
        row["risk_ok"] = all(row[f] for f in RISK_CHECKS)
        row["return_ok"] = row["expected_return"] >= required_return
        row["all_ok"] = row["risk_ok"] and row["return_ok"]
        rows.append({**row, **w.to_dict()})
    return pd.DataFrame(rows).set_index("point")


def summarise(table: pd.DataFrame, limits: IPSLimits, required_return: float) -> dict:
    """Headline numbers: the best expected return the risk limits allow and the return gap."""
    risk_ok = table[table["risk_ok"]]
    best = risk_ok["expected_return"].idxmax() if len(risk_ok) else None
    out = {
        "required_return": required_return,
        "max_expected_return_on_frontier": float(table["expected_return"].max()),
        "points": int(len(table)), "points_meeting_risk_limits": int(table["risk_ok"].sum()),
        "points_meeting_everything": int(table["all_ok"].sum()),
        "best_risk_compliant_point": best,
        "best_risk_compliant_expected_return": float(risk_ok["expected_return"].max()) if best else None,
        "return_gap": float(required_return - risk_ok["expected_return"].max()) if best else None,
        "min_volatility": float(table["volatility"].min()), "min_es99_1d": float(table["es99_1d"].min()),
        "min_stress_drawdown": float(table["stress_drawdown"].min()),
    }
    # The limits that bind first: share of frontier points failing each check.
    out["fail_share"] = {flag: float(1 - table[flag].mean()) for flag in (*RISK_CHECKS, "return_ok")}
    if best is None:   # the point with the smallest worst-case ratio of risk figure to limit
        ratio = table.apply(lambda r: max(r[c] / getattr(limits, lim) for c, lim in RISK_CHECKS.values()), axis=1)
        out["closest_point"], out["closest_point_worst_ratio"] = str(ratio.idxmin()), float(ratio.min())
    if out["points_meeting_everything"]:
        out["finding"] = "feasible: at least one portfolio meets the return objective and every risk limit"
    elif best is not None:
        out["finding"] = (f"conflict: the risk limits allow at most {out['best_risk_compliant_expected_return']:.2%} "
                          f"expected return against {required_return:.2%} required")
    else:
        out["finding"] = "infeasible: no IPS-compliant portfolio meets every risk limit, even in-sample"
    return out
