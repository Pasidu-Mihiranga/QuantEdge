"""Regime-conditioned risk (Step 14 A): a two-regime Markov-switching model of portfolio returns.

    r_t = mu_{s_t} + sigma_{s_t} e_t,  s_t in {calm, high-vol},  P(s_t = j | s_{t-1} = i) = p_ij

Only *filtered* probabilities P(s_t | data up to t) are used. Parameters are estimated on an
estimation window and then held fixed while the filter runs, so the probability at t never uses
data after t (smoothed probabilities would).
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd
from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression

from quantedge.risk import es as esf


@dataclass(frozen=True)
class RegimeFit:
    params: np.ndarray
    sigma: tuple[float, float]       # daily volatility of (calm, high-vol)
    p_stay: tuple[float, float]      # P(stay calm), P(stay high-vol)
    high: int                        # index of the high-volatility regime in statsmodels' ordering

    @property
    def expected_duration(self) -> tuple[float, float]:
        """Expected days in each regime, 1 / (1 - p_ii)."""
        return tuple(1.0 / (1.0 - p) for p in self.p_stay)


def fit_markov(r: pd.Series, seed: int = 0) -> RegimeFit:
    """Two regimes with switching mean and variance, fitted by maximum likelihood (returns in %)."""
    x = 100.0 * r.dropna()
    model = MarkovRegression(x, k_regimes=2, trend="c", switching_variance=True)
    np.random.seed(seed % (2**32))          # statsmodels' search_reps uses the global generator  # noqa: NPY002
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = model.fit(search_reps=20, disp=False)
    var = np.array([res.params[f"sigma2[{i}]"] for i in range(2)])
    high = int(np.argmax(var))
    calm = 1 - high
    p = res.regime_transition                    # shape (2, 2, 1): [to, from]
    p_stay = (float(p[calm, calm, 0]), float(p[high, high, 0]))
    sig = np.sqrt(var) / 100.0
    return RegimeFit(np.asarray(res.params), (float(sig[calm]), float(sig[high])), p_stay, high)


def filtered_high_prob(r: pd.Series, fit: RegimeFit) -> pd.Series:
    """P(high-vol regime at t | returns up to t), with the parameters held fixed."""
    x = 100.0 * r.dropna()
    model = MarkovRegression(x, k_regimes=2, trend="c", switching_variance=True)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = model.filter(fit.params)
    probs = np.asarray(res.filtered_marginal_probabilities)
    col = probs[:, fit.high] if probs.ndim == 2 else probs[fit.high]
    return pd.Series(col, index=x.index, name="p_high")


def regime_risk(r: pd.Series, p_high: pd.Series, alphas=(0.95, 0.99), threshold: float = 0.5) -> pd.DataFrame:
    """Historical VaR/ES within each regime (days classified by the filtered probability)."""
    loss = -r.reindex(p_high.index)
    rows = []
    for name, mask in (("calm", p_high <= threshold), ("high-vol", p_high > threshold)):
        sample = loss[mask].dropna().to_numpy()
        for a in alphas:
            rows.append({"regime": name, "alpha": a, "days": len(sample),
                         "var": esf.sample_var(sample, a), "es": esf.sample_es(sample, a)})
    return pd.DataFrame(rows)


def vix_agreement(p_high: pd.Series, vix: pd.Series) -> pd.DataFrame:
    """Share of days in the high-vol regime within each VIX band (calm < 20, elevated 20–30, stressed > 30)."""
    v = vix.reindex(p_high.index)
    band = pd.cut(v, [-np.inf, 20, 30, np.inf], labels=["VIX < 20", "VIX 20–30", "VIX > 30"])
    return (p_high > 0.5).groupby(band, observed=False).mean().rename("share_high_vol").to_frame()
