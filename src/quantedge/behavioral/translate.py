"""Agents' answers -> market shocks -> portfolio loss, through the same stress engine as the team's scenario.

Magnitudes come from history, never from the LLM. Each factor's direction and intensity pick a signed quantile of its
historical change over the team's scenario window of three quarters (low 75th, medium 90th, high 97.5th, extreme 99.5th
percentile), so both sides of the comparison cover the same period. The shocks then go through `stress.factor.scenario_contributions`, so fund moves aggregate as simple returns.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from quantedge.stress.factor import scenario_contributions

QUANTILE = {"low": 0.75, "medium": 0.90, "high": 0.975, "extreme": 0.995}
EPISODE_DAYS = 189                      # the three quarters of the team's scenario (config: episode_3q)
FACTOR_MAP = {  # questionnaire factor -> (stress-engine factor, macro series, transform)
    "rates_10y": ("d_yield10_bp", "DGS10", "diff_bp"),
    "oil": ("dln_oil", "DCOILWTICO", "dlog"),
    "vix": ("d_vix", "VIXCLS", "diff"),
    "usd": ("dln_usd", "DTWEXBGS", "dlog"),
    "credit_spread": ("d_credit_bp", "BAA10Y", "diff_bp"),
}


def h_day_changes(macro: pd.DataFrame, h: int, as_of: pd.Timestamp) -> pd.DataFrame:
    """Historical h-day changes of each factor, using data up to `as_of` only."""
    m, out = macro.loc[:as_of], {}
    for col, series, how in FACTOR_MAP.values():
        s = m[series].dropna()
        if how == "dlog":
            out[col] = np.log(s.where(s > 0)).dropna().diff(h)
        else:
            out[col] = s.diff(h) * (100 if how == "diff_bp" else 1)
    return pd.DataFrame(out).dropna(how="all")


def factor_shocks(coding: dict, changes: pd.DataFrame) -> dict[str, float]:
    """Signed historical quantile for each coded factor (direction 0 -> no shock)."""
    shocks = {}
    for name, (col, _series, _how) in FACTOR_MAP.items():
        c, hist = coding["factors"][name], changes[col].dropna()
        q = QUANTILE[c["intensity"]]
        shocks[col] = {"+": max(float(hist.quantile(q)), 0.0), "-": min(float(hist.quantile(1 - q)), 0.0), "0": 0.0}[c["direction"]]
    return shocks


def evaluate(shock: dict, betas: pd.DataFrame, weights: pd.Series, liquidity_day: dict | None) -> dict:
    """Portfolio loss (positive) and each fund's part, as the crises page computes them."""
    parts = scenario_contributions(betas, shock, weights, liquidity_day)
    return {"shock": shock, "loss": -float(parts.sum()), "parts": {k: -float(v) for k, v in parts.items()}}


def compare_run(answer: dict, macro: pd.DataFrame, betas: pd.DataFrame, weights: pd.Series, liquidity_day: dict | None,
                as_of: pd.Timestamp) -> dict:
    result = evaluate(factor_shocks(answer, h_day_changes(macro, EPISODE_DAYS, as_of)), betas, weights, liquidity_day)
    return {**result, "horizon_days": EPISODE_DAYS, "behaviour": answer["behaviour"], "summary": answer["narrative_summary"],
            "mechanisms": answer.get("key_mechanisms", []), "limitations": answer.get("stated_limitations", [])}
