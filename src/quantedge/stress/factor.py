"""Macro factor betas for the hypothetical scenario (Step 12 §3.2). Also drive the scenario sliders on the Stress Testing page.

Weekly data reduce asynchronous noise. Factors: change in the 10-year yield (bp), log change in oil,
change in VIX (points), log change in the broad USD index, change in the Baa credit spread (bp).
Each ETF's weekly return is regressed on the factors with Newey-West (HAC) errors.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm

FACTORS = ["d_yield10_bp", "dln_oil", "d_vix", "dln_usd", "d_credit_bp"]


def weekly_factors(macro: pd.DataFrame) -> pd.DataFrame:
    m = macro.resample("W-FRI").last()
    oil = m["DCOILWTICO"].where(m["DCOILWTICO"] > 0)   # WTI was negative on 2020-04-20: log undefined
    return pd.DataFrame({
        "d_yield10_bp": m["DGS10"].diff() * 100,
        "dln_oil": np.log(oil).diff(),
        "d_vix": m["VIXCLS"].diff(),
        "dln_usd": np.log(m["DTWEXBGS"]).diff(),
        "d_credit_bp": m["BAA10Y"].diff() * 100,
    })


def weekly_returns(returns: pd.DataFrame) -> pd.DataFrame:
    return (1 + returns).resample("W-FRI").prod() - 1


@dataclass(frozen=True)
class BetaResult:
    betas: pd.DataFrame          # assets x factors
    cov: dict[str, pd.DataFrame]  # per asset: covariance of the factor betas
    r2: pd.Series
    n_weeks: int
    sample: str


def estimate_factor_betas(etf_weekly: pd.DataFrame, factors_weekly: pd.DataFrame,
                          windows: dict[str, tuple[str, str]] | None = None, hac_lags: int = 4,
                          sample: str = "full") -> BetaResult:
    """OLS with HAC errors. `sample="stress"` keeps only weeks inside the given crisis windows."""
    data = pd.concat([etf_weekly, factors_weekly], axis=1, join="inner").dropna()
    if sample == "stress":
        mask = pd.Series(False, index=data.index)
        for s, e in windows.values():
            mask |= (data.index >= s) & (data.index <= e)
        data = data.loc[mask]
    X = sm.add_constant(data[FACTORS])
    betas, covs, r2 = {}, {}, {}
    for asset in etf_weekly.columns:
        fit = sm.OLS(data[asset], X).fit(cov_type="HAC", cov_kwds={"maxlags": hac_lags})
        betas[asset] = fit.params[FACTORS]
        covs[asset] = fit.cov_params().loc[FACTORS, FACTORS]
        r2[asset] = fit.rsquared
    return BetaResult(pd.DataFrame(betas).T, covs, pd.Series(r2), len(data), sample)
