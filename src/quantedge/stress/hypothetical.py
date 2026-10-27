"""Factor-driven hypothetical scenario (Step 12 §3.2): R* = B f*, with a standard-error band.

The portfolio band comes from regressing the portfolio's own weekly return on the factors, which
captures the correlation between the assets' estimation errors exactly.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm

from quantedge.stress.factor import FACTORS, BetaResult


@dataclass(frozen=True)
class ShockResult:
    asset_returns: pd.Series
    asset_se: pd.Series
    portfolio_return: float
    portfolio_se: float
    loss_usd: float
    contributions: pd.Series


def apply_shock(betas: BetaResult, shock: dict[str, float], weights: pd.Series, nav: float,
                etf_weekly: pd.DataFrame | None = None, factors_weekly: pd.DataFrame | None = None
                ) -> ShockResult:
    f = pd.Series(shock, dtype=float).reindex(FACTORS).fillna(0.0)
    r_star = betas.betas[FACTORS] @ f
    se = pd.Series({a: float(np.sqrt(f @ betas.cov[a] @ f)) for a in betas.betas.index})
    w = weights.reindex(r_star.index, fill_value=0.0)
    port = float(w @ r_star)
    if etf_weekly is not None and factors_weekly is not None:
        data = pd.concat([(etf_weekly * w).sum(axis=1).rename("p"), factors_weekly], axis=1, join="inner").dropna()
        fit = sm.OLS(data["p"], sm.add_constant(data[FACTORS])).fit(cov_type="HAC", cov_kwds={"maxlags": 4})
        port_se = float(np.sqrt(f @ fit.cov_params().loc[FACTORS, FACTORS] @ f))
    else:
        port_se = float(np.sqrt((w**2) @ (se**2)))  # ignores cross-asset error correlation
    return ShockResult(r_star, se, port, port_se, -port * nav, (w * r_star).rename("contribution"))


def duration_check(delta_yield_bp: float, duration: float = 6.0) -> float:
    """First-order bond return -D x dy, the cross-check for AGG's factor-model shock."""
    return -duration * delta_yield_bp / 10_000
