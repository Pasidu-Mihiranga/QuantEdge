"""BeST translation layer (Step 19 §3.6): coded behavioural answers -> data-anchored shocks.

Magnitudes come from history, never from the LLM:
    factor intensity  -> signed quantile of the factor's historical h-day change
                         (low 75th, medium 90th, high 97.5th, extreme 99.5th percentile)
    duration          -> h = 5 (days), 20 (weeks) or 60 (months) trading days
    factor shocks     -> ETF shocks = B f with the Step 12 stress-sample factor betas
    contagion 0-3     -> Sigma_lambda = (1 - lambda) Sigma_calm + lambda Sigma_stress, lambda in {0, 1/3, 2/3, 1}
    panic/herding 0-3 -> volatility multiplier {1, 1.25, 1.5, 2}
The LLM's asset directions are used only as a consistency check against the translated shocks.
The same machinery translates the analyst's answers (variant A) and MiroFish's (variant B).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from quantedge.behavioral.schema import ASSETS
from quantedge.risk import es as esf

QUANTILE = {"low": 0.75, "medium": 0.90, "high": 0.975, "extreme": 0.995}
HORIZON = {"days": 5, "weeks": 20, "months": 60}
LAMBDA = (0.0, 1 / 3, 2 / 3, 1.0)
VOL_MULT = (1.0, 1.25, 1.5, 2.0)
# questionnaire factor -> (Step 12 factor column, macro series, transform)
FACTOR_MAP = {
    "rates_10y": ("d_yield10_bp", "DGS10", "diff_bp"),
    "oil": ("dln_oil", "DCOILWTICO", "dlog"),
    "vix": ("d_vix", "VIXCLS", "diff"),
    "usd": ("dln_usd", "DTWEXBGS", "dlog"),
    "credit_spread": ("d_credit_bp", "BAA10Y", "diff_bp"),
}


def h_day_changes(macro: pd.DataFrame, h: int, as_of: pd.Timestamp) -> pd.DataFrame:
    """Historical h-day changes of each factor, using data up to `as_of` only."""
    m = macro.loc[:as_of]
    out = {}
    for _q, (col, series, how) in FACTOR_MAP.items():
        s = m[series].dropna()
        if how == "dlog":
            s = np.log(s.where(s > 0)).dropna()
            out[col] = s.diff(h)
        elif how == "diff_bp":
            out[col] = s.diff(h) * 100
        else:
            out[col] = s.diff(h)
    return pd.DataFrame(out).dropna(how="all")


def factor_shocks(coding: dict, changes: pd.DataFrame) -> pd.Series:
    """Signed historical quantiles for each coded factor (direction 0 -> no shock)."""
    shocks = {}
    for name, (col, _s, _h) in FACTOR_MAP.items():
        c = coding["factors"][name]
        q = QUANTILE[c["intensity"]]
        hist = changes[col].dropna()
        if c["direction"] == "+":
            shocks[col] = float(max(hist.quantile(q), 0.0))
        elif c["direction"] == "-":
            shocks[col] = float(min(hist.quantile(1 - q), 0.0))
        else:
            shocks[col] = 0.0
    return pd.Series(shocks)


@dataclass(frozen=True)
class Translation:
    horizon: int
    factor_shocks: pd.Series
    etf_shocks: pd.Series
    lam: float
    vol_mult: float
    consistency: float              # share of assets whose coded direction matches the shock's sign
    flight_to_safety_ok: bool


def translate(coding: dict, macro: pd.DataFrame, betas: pd.DataFrame, as_of: pd.Timestamp) -> Translation:
    b = coding["behaviour"]
    h = HORIZON[b["duration"]]
    f = factor_shocks(coding, h_day_changes(macro, h, as_of))
    etf = (betas[f.index] @ f).reindex(list(ASSETS))
    lam = LAMBDA[b["contagion_breadth"]]
    mult = VOL_MULT[max(b["panic_selling"], b["herding"])]
    sign = np.sign(etf).map({1.0: "+", -1.0: "-", 0.0: "0"})
    coded = pd.Series(coding["asset_directions"]).reindex(etf.index)
    consistency = float((sign == coded).mean())
    havens = [a for a in b["flight_to_safety"] if a in etf.index]
    fts_ok = all(etf[a] >= -0.01 for a in havens)        # havens should not be translated into large losses
    return Translation(h, f, etf, lam, mult, consistency, fts_ok)


def blended_cov(calm: pd.DataFrame, stress: pd.DataFrame, lam: float) -> pd.DataFrame:
    return (1 - lam) * calm + lam * stress


def scenario_risk(t: Translation, weights: pd.Series, calm: pd.DataFrame, stress: pd.DataFrame,
                  rng: np.random.Generator, n: int = 100_000, alpha: float = 0.99) -> dict:
    """Portfolio loss under the scenario and scenario-conditional VaR/ES over the horizon:
    h-day returns ~ Normal(mean = ETF shocks, cov = h x vol_mult^2 x Sigma_lambda)."""
    cols = list(ASSETS)
    w = weights.reindex(cols, fill_value=0.0).to_numpy()
    mu = t.etf_shocks.reindex(cols).fillna(0.0).to_numpy()
    cov = blended_cov(calm.reindex(index=cols, columns=cols), stress.reindex(index=cols, columns=cols), t.lam)
    sims = rng.multivariate_normal(mu, cov.to_numpy() * t.horizon * t.vol_mult**2, size=n)
    losses = -(sims @ w)
    return {"loss": float(-(w @ mu)), "var": esf.sample_var(losses, alpha), "es": esf.sample_es(losses, alpha),
            "contributions": pd.Series(-w * mu, index=cols)}


def realised_returns(returns: pd.DataFrame, window: tuple[str, str]) -> pd.Series:
    """Cumulative ETF returns over a replay window (used to validate blind replays, Step 20 D1)."""
    seg = returns.loc[window[0]:window[1]]
    return (1 + seg).prod() - 1


def replay_fidelity(t: Translation, realised: pd.Series) -> dict:
    """Direction hit rate, Spearman rank correlation and mean absolute error vs realised returns."""
    pred = t.etf_shocks.reindex(realised.index)
    hit = float((np.sign(pred) == np.sign(realised)).mean())
    rho = float(pred.rank().corr(realised.rank()))
    return {"direction_hit_rate": hit, "rank_corr": rho, "mae": float((pred - realised).abs().mean())}
