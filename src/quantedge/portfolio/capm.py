"""CAPM regressions and CAPM-implied expected returns (Step 06 §3.2).

    e_i,t = alpha + beta e_m,t + eps_t   (excess returns; market proxy = SPY)

Standard errors are Newey-West (HAC, 5 lags) because daily returns are autocorrelated and
heteroskedastic.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm

A = 252


@dataclass(frozen=True)
class CAPMResult:
    beta: float
    alpha_ann: float
    alpha_t: float
    alpha_p: float
    r2: float
    resid_vol_ann: float
    n: int


def capm_regression(asset_excess: pd.Series, market_excess: pd.Series, hac_lags: int = 5) -> CAPMResult:
    df = pd.concat([asset_excess.rename("y"), market_excess.rename("x")], axis=1).dropna()
    X = sm.add_constant(df["x"])
    fit = sm.OLS(df["y"], X).fit(cov_type="HAC", cov_kwds={"maxlags": hac_lags})
    return CAPMResult(
        beta=float(fit.params["x"]),
        alpha_ann=float(fit.params["const"] * A),
        alpha_t=float(fit.tvalues["const"]),
        alpha_p=float(fit.pvalues["const"]),
        r2=float(fit.rsquared),
        resid_vol_ann=float(np.std(fit.resid, ddof=2) * np.sqrt(A)),
        n=int(fit.nobs),
    )


def capm_table(returns: pd.DataFrame, rf: pd.Series, market: str) -> pd.DataFrame:
    """CAPM statistics for every column of `returns` against `market`."""
    excess = returns.sub(rf.reindex(returns.index), axis=0)
    rows = {c: capm_regression(excess[c], excess[market]).__dict__ for c in returns.columns}
    return pd.DataFrame(rows).T


def rolling_beta(asset: pd.Series, market: pd.Series, window: int = 756) -> pd.Series:
    """Trailing-window OLS beta: cov(asset, market) / var(market)."""
    cov = asset.rolling(window).cov(market)
    var = market.rolling(window).var()
    return (cov / var).rename(f"beta_{asset.name}")


def capm_expected_returns(betas: pd.Series, rf_annual: float, mrp: float = 0.05) -> pd.Series:
    """mu_i = rf + beta_i x MRP. MRP is an explicit assumption (base 5%, sensitivity 4-6%)."""
    return (rf_annual + betas * mrp).rename("mu_capm")
