"""Euler risk decomposition (Step 13 §3.1). For a measure homogeneous of degree 1,
rho(w) = sum_i w_i d rho / d w_i, so the component contributions add up to the total.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def euler_parametric(w: pd.Series, sigma: pd.DataFrame, alpha: float = 0.99, measure: str = "es") -> pd.DataFrame:
    """Normal (mu ~ 0) contributions. marginal_i = k (Sigma w)_i / sigma_p with k = z_a (VaR)
    or phi(z_a)/(1-a) (ES); component_i = w_i x marginal_i."""
    wv = w.reindex(sigma.columns, fill_value=0.0)
    sw = sigma.to_numpy() @ wv.to_numpy()
    sp = float(np.sqrt(wv.to_numpy() @ sw))
    z = stats.norm.ppf(alpha)
    k = z if measure == "var" else stats.norm.pdf(z) / (1 - alpha)
    marginal = k * sw / sp
    return _table(wv, marginal)


def euler_simulation_es(w: pd.Series, scenarios: pd.DataFrame, alpha: float = 0.99) -> pd.DataFrame:
    """component_i = -w_i E[r_i | l_p >= VaR_p], averaged over the tail scenarios."""
    wv = w.reindex(scenarios.columns, fill_value=0.0)
    R = scenarios.to_numpy()
    loss = -(R @ wv.to_numpy())
    tail = loss >= np.quantile(loss, alpha, method="higher")
    marginal = -R[tail].mean(axis=0)
    return _table(wv, marginal)


def euler_simulation_var(w: pd.Series, scenarios: pd.DataFrame, alpha: float = 0.99, k: int = 5) -> pd.DataFrame:
    """component_i = -w_i E[r_i | l_p ~ VaR_p], averaging the 2k+1 scenarios around the VaR order
    statistic. Noisy: report with a caveat and lead with ES."""
    wv = w.reindex(scenarios.columns, fill_value=0.0)
    R = scenarios.to_numpy()
    loss = -(R @ wv.to_numpy())
    order = np.argsort(loss)
    j = int(np.ceil(alpha * len(loss))) - 1
    near = order[max(0, j - k): j + k + 1]
    marginal = -R[near].mean(axis=0)
    return _table(wv, marginal)


def _table(w: pd.Series, marginal: np.ndarray) -> pd.DataFrame:
    comp = w.to_numpy() * marginal
    total = comp.sum()
    pct = comp / total
    with np.errstate(divide="ignore", invalid="ignore"):
        rc = np.where(w.to_numpy() > 0, pct / w.to_numpy(), np.nan)
    return pd.DataFrame({"weight": w.to_numpy(), "marginal": marginal, "component": comp,
                         "pct_contribution": pct, "risk_to_capital": rc}, index=w.index)
