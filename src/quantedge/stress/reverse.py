"""Reverse stress test and stressed covariance (Step 12 §3.3–3.4).

Most plausible asset-return vector x that produces a portfolio loss L*:
    minimise x' Sigma^-1 x  subject to  w'x = -L*   =>   x* = -L* Sigma w / (w' Sigma w)
    d^2 = L*^2 / (w' Sigma w)  (squared Mahalanobis distance of x*)
Two plausibility readings are reported: the directional loss probability Phi(-d) for the given
horizon (used for "1 in N years"), and the plan's chi2(n) tail probability of d^2.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats


@dataclass(frozen=True)
class ReverseStress:
    x_star: pd.Series
    d2: float
    loss_prob: float
    chi2_tail: float
    years_between: float
    horizon_days: int


def most_likely_breach(sigma_daily: pd.DataFrame, w: pd.Series, L_star: float,
                       horizon_days: int = 21) -> ReverseStress:
    S = sigma_daily.to_numpy() * horizon_days
    wv = w.reindex(sigma_daily.columns, fill_value=0.0).to_numpy()
    var_p = float(wv @ S @ wv)
    x = -L_star * (S @ wv) / var_p
    d2 = L_star**2 / var_p
    p_loss = float(stats.norm.sf(np.sqrt(d2)))
    periods_per_year = 252 / horizon_days
    years = float("inf") if p_loss == 0 else 1.0 / (p_loss * periods_per_year)
    return ReverseStress(pd.Series(x, index=sigma_daily.columns), float(d2), p_loss,
                         float(stats.chi2.sf(d2, len(wv))), years, horizon_days)


def stressed_sigma(returns: pd.DataFrame, windows: dict[str, tuple[str, str]]) -> pd.DataFrame:
    """Daily covariance estimated only on the union of the crisis windows."""
    mask = pd.Series(False, index=returns.index)
    for s, e in windows.values():
        mask |= (returns.index >= s) & (returns.index <= e)
    return returns.loc[mask].cov()


def parametric_var_es(sigma_daily: pd.DataFrame, w: pd.Series, alpha: float = 0.99,
                      mu_daily: pd.Series | None = None) -> tuple[float, float]:
    """Normal VaR and ES of the portfolio for a given covariance (calm vs stressed comparison)."""
    wv = w.reindex(sigma_daily.columns, fill_value=0.0).to_numpy()
    s = float(np.sqrt(wv @ sigma_daily.to_numpy() @ wv))
    m = 0.0 if mu_daily is None else float(wv @ mu_daily.reindex(sigma_daily.columns).to_numpy())
    z = stats.norm.ppf(alpha)
    return -m + z * s, -m + s * stats.norm.pdf(z) / (1 - alpha)
