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


def weekly_log_returns(returns: pd.DataFrame) -> pd.DataFrame:
    """Weekly log returns (sum of daily log returns), as notebook 05 uses for the scenario betas."""
    return np.log1p(returns).resample("W-FRI").sum()


def regime_stress_weeks(daily_index: pd.DatetimeIndex, dtb3: pd.Series,
                        crises: tuple[tuple[str, str], ...] = (("2008-10-01", "2008-12-31"), ("2020-01-01", "2020-03-31")),
                        hike_pp: float = 1.0) -> pd.Series:
    """D5 stress weeks (notebook 05): a week is a stress week if most of its days are in a rate-hiking
    cycle (3-month bill up more than `hike_pp` points over 252 days, known at t−1) or in a liquidity crisis."""
    tb = dtb3.reindex(daily_index, method="ffill").shift(1)
    hike = (tb - tb.shift(252)) > hike_pp
    crisis = pd.Series(False, index=daily_index)
    for a, b in crises:
        crisis |= (daily_index >= a) & (daily_index <= b)
    weekly = pd.DataFrame({"hike": hike.astype(float), "crisis": crisis.astype(float)}).resample("W-FRI").mean() > 0.5
    return weekly["hike"] | weekly["crisis"]


def scenario_loss(betas: pd.DataFrame, shock: dict[str, float], weights: pd.Series,
                  liquidity_day: dict[str, float] | None = None) -> float:
    """D5 scenario loss (positive). The factor betas act on each ETF's log return, x_i = (B s)_i, so each ETF's
    simple return is expm1(x_i), and simple returns aggregate across assets: R_p = Σ w_i expm1(x_i) (weights set at
    the start of the episode, buy and hold). The liquidity day adds each ETF's one-day gap (e.g. AGG −5%) on top."""
    return -float(scenario_contributions(betas, shock, weights, liquidity_day, min_weight=0.0).sum())


def scenario_contributions(betas: pd.DataFrame, shock: dict[str, float], weights: pd.Series,
                           liquidity_day: dict[str, float] | None = None, min_weight: float = 1e-4) -> pd.Series:
    """Each holding's part of the scenario return: w_i expm1(x_i), plus one "<ticker> panic day" row per liquidity
    shock. The parts add up exactly to −`scenario_loss`, up to the dropped holdings below `min_weight` (solver dust)."""
    f = pd.Series(shock, dtype=float).reindex(FACTORS).fillna(0.0)
    w = weights.reindex(betas.index, fill_value=0.0)
    parts = (w * np.expm1(betas[FACTORS] @ f))[w > min_weight]
    for t, v in (liquidity_day or {}).items():
        if w.get(t, 0.0) > min_weight:
            parts[f"{t} panic day"] = v * float(w[t])
    return parts


@dataclass(frozen=True)
class Plausibility:
    share_more_extreme: float      # share of historical episodes with a larger Mahalanobis distance
    per_factor: pd.Series          # per factor: share of episodes at least as large in the shock's direction
    n_episodes: int
    start: pd.Timestamp


def episode_plausibility(factors_weekly: pd.DataFrame, shock: dict[str, float], weeks: int = 39) -> Plausibility:
    """How unusual a shock is against every overlapping `weeks`-long change in history (D5: a 3-quarter episode).

    Joint: d²(x) = (x − μ)' Σ⁻¹ (x − μ) over the five factor changes; the result is the empirical share of episodes
    with d² ≥ d²(shock), which needs no normality assumption. Overlapping episodes, so it is a frequency, not a p-value.
    """
    h = factors_weekly[FACTORS].rolling(weeks).sum().dropna()
    x = pd.Series(shock, dtype=float).reindex(FACTORS).fillna(0.0)
    mu, inv = h.mean(), np.linalg.inv(np.cov(h.to_numpy().T))
    d2 = np.einsum("ij,jk,ik->i", h - mu, inv, h - mu)
    d2x = float((x - mu) @ inv @ (x - mu))
    per = pd.Series({f: float((h[f] >= x[f]).mean() if x[f] >= mu[f] else (h[f] <= x[f]).mean()) for f in FACTORS})
    return Plausibility(float((d2 >= d2x).mean()), per, len(h), h.index[0])


def estimate_factor_betas(etf_weekly: pd.DataFrame, factors_weekly: pd.DataFrame,
                          windows: dict[str, tuple[str, str]] | None = None, hac_lags: int = 4,
                          sample: str = "full", mask: pd.Series | None = None) -> BetaResult:
    """OLS with HAC errors. `sample="stress"` keeps only weeks inside the given crisis windows;
    `sample="regime"` keeps the weeks where `mask` is True (D5: rate-hiking and liquidity-crisis weeks)."""
    data = pd.concat([etf_weekly, factors_weekly], axis=1, join="inner").dropna()
    if sample == "regime":
        data = data.loc[mask.reindex(data.index, fill_value=False).astype(bool)]
    elif sample == "stress":
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
