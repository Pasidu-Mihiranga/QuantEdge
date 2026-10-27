"""Macro and FX risk assessment (Step 14 D).

- Stock-bond correlation regime: rolling 1-year SPY-AGG correlation next to CPI inflation; it turns
  positive when inflation is high (2022), which is why bonds failed as a hedge.
- Inflation sensitivity: monthly portfolio return regressed on CPI surprises (HAC errors).
- Rates sensitivity: portfolio beta to the 10-year yield from the Step 12 factor model.
- USD/LKR context: the endowment spends in rupees; a USD portfolio gains in LKR terms when the rupee
  depreciates (a natural hedge). Outside the mandate's USD risk measures; disclosed as a limitation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm


def rolling_stock_bond_corr(returns: pd.DataFrame, window: int = 252, stock: str = "SPY",
                            bond: str = "AGG") -> pd.Series:
    return returns[stock].rolling(window).corr(returns[bond]).rename("stock_bond_corr")


def cpi_yoy(cpi: pd.Series) -> pd.Series:
    m = cpi.dropna().resample("ME").last()
    return m.pct_change(12).rename("cpi_yoy")


def inflation_beta(portfolio_daily: pd.Series, cpi: pd.Series) -> dict[str, float]:
    """Monthly portfolio return on the CPI surprise (month-on-month inflation minus its prior
    12-month average), with Newey-West errors. A negative beta means inflation surprises hurt."""
    monthly_ret = (1 + portfolio_daily).resample("ME").prod() - 1
    mom = cpi.dropna().resample("ME").last().pct_change()
    surprise = (mom - mom.rolling(12).mean().shift(1)).rename("surprise")
    df = pd.concat([monthly_ret.rename("ret"), surprise], axis=1).dropna()
    fit = sm.OLS(df["ret"], sm.add_constant(df["surprise"])).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
    return {"beta": float(fit.params["surprise"]), "t": float(fit.tvalues["surprise"]),
            "months": int(fit.nobs), "per_0p1pct_surprise": float(fit.params["surprise"] * 0.001)}


def rates_impact(weights: pd.Series, betas: pd.DataFrame, shock_bp: float = 100.0) -> float:
    """Portfolio return for a `shock_bp` move in the 10-year yield (factor betas per bp)."""
    w = weights.reindex(betas.index, fill_value=0.0)
    return float(w @ betas["d_yield10_bp"] * shock_bp)


def lkr_context(usd_lkr: pd.Series, portfolio_daily: pd.Series | None = None) -> dict:
    """Rupee depreciation and what it means for a USD portfolio valued in LKR."""
    s = usd_lkr.dropna()
    yearly = s.resample("YE").last()
    out = {
        "start": str(s.index[0].date()), "end": str(s.index[-1].date()),
        "lkr_per_usd_start": float(s.iloc[0]), "lkr_per_usd_end": float(s.iloc[-1]),
        "annual_depreciation": float((s.iloc[-1] / s.iloc[0]) ** (365.25 / (s.index[-1] - s.index[0]).days) - 1),
        "change_2022": float(yearly.loc["2022"].iloc[0] / yearly.loc["2021"].iloc[0] - 1)
        if "2021" in yearly.index.year.astype(str) else np.nan,
    }
    if portfolio_daily is not None:
        usd = (1 + portfolio_daily).cumprod()
        fx = s.reindex(usd.index).ffill()
        lkr = usd * fx / fx.iloc[0]
        out["growth_usd"] = float(usd.iloc[-1] - 1)
        out["growth_lkr"] = float(lkr.dropna().iloc[-1] - 1)
    return out
