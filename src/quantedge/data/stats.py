"""Stationarity tests and stylised facts (Step 03 §3.3)."""

from __future__ import annotations

import warnings

import pandas as pd
from scipy import stats as sps
from statsmodels.stats.diagnostic import acorr_ljungbox, het_arch
from statsmodels.tools.sm_exceptions import InterpolationWarning
from statsmodels.tsa.stattools import adfuller, kpss


def stationarity_table(series: dict[str, pd.Series], alpha: float = 0.05) -> pd.DataFrame:
    """ADF (H0: unit root) and KPSS (H0: stationary), used together because ADF has low power.

    KPSS p-values are interpolated from a table and capped at [0.01, 0.10]; the cap is reported
    as-is (a KPSS p of 0.10 means "at least 0.10").
    """
    rows = []
    for name, x in series.items():
        x = x.dropna()
        adf_stat, adf_p, *_ = adfuller(x, autolag="AIC")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", InterpolationWarning)
            kpss_stat, kpss_p, *_ = kpss(x, regression="c", nlags="auto")
        if adf_p < alpha and kpss_p > alpha:
            verdict = "stationary"
        elif adf_p >= alpha and kpss_p <= alpha:
            verdict = "unit root"
        else:
            verdict = "inconclusive"
        rows.append({"series": name, "n": len(x), "adf_stat": adf_stat, "adf_p": adf_p,
                     "kpss_stat": kpss_stat, "kpss_p": kpss_p, "verdict": verdict})
    return pd.DataFrame(rows).set_index("series")


def stylised_facts(returns: pd.DataFrame, lags: int = 10) -> pd.DataFrame:
    """Skewness, excess kurtosis, Jarque-Bera, Ljung-Box on r and r^2, and ARCH-LM per column."""
    rows = []
    for name in returns.columns:
        r = returns[name].dropna()
        jb = sps.jarque_bera(r)
        lb_r = acorr_ljungbox(r, lags=[lags], return_df=True)["lb_pvalue"].iloc[0]
        lb_r2 = acorr_ljungbox(r**2, lags=[lags], return_df=True)["lb_pvalue"].iloc[0]
        arch_p = het_arch(r, nlags=lags)[1]
        rows.append({
            "series": name, "n": len(r),
            "mean_ann": r.mean() * 252, "vol_ann": r.std() * 252**0.5,
            "skew": sps.skew(r), "excess_kurtosis": sps.kurtosis(r),
            "jb_stat": jb.statistic, "jb_p": jb.pvalue,
            f"ljungbox_r_p_lag{lags}": lb_r, f"ljungbox_r2_p_lag{lags}": lb_r2,
            f"arch_lm_p_lag{lags}": arch_p,
        })
    return pd.DataFrame(rows).set_index("series")
