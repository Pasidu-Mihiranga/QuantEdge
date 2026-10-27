"""Unconditional VaR / ES models: historical, Normal, Student-t, Cornish-Fisher (Steps 08–09).

All parameters are estimated on losses l = -R. The estimated mean is included (it is tiny at 1 day).
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy import optimize, stats

from quantedge.risk import es as esf
from quantedge.risk.base import portfolio_returns


class HistoricalModel:
    """VaR = empirical a-quantile of the window's losses; ES = Acerbi-Tasche tail mean."""

    name = "Historical"

    def fit(self, returns, weights=None):
        self.losses = -portfolio_returns(returns, weights).to_numpy()
        return self

    def var(self, alpha):
        return esf.sample_var(self.losses, alpha)

    def es(self, alpha):
        return esf.sample_es(self.losses, alpha)

    def loss_sample(self):
        return self.losses


class NormalModel:
    """VaR = mu_l + z_a sigma;  ES = mu_l + sigma phi(z_a) / (1 - a)."""

    name = "Normal"

    def fit(self, returns, weights=None):
        losses = -portfolio_returns(returns, weights)
        self.mu, self.sigma = float(losses.mean()), float(losses.std(ddof=1))
        return self

    def var(self, alpha):
        return esf.normal_var(self.mu, self.sigma, alpha)

    def es(self, alpha):
        return esf.normal_es(self.mu, self.sigma, alpha)

    def loss_sample(self):
        return None


def fit_t_nu(z: np.ndarray, bounds=(2.05, 200.0)) -> float:
    """MLE of nu for a unit-variance Student-t on standardised data z (scale sqrt((nu-2)/nu))."""
    def nll(nu):
        s = math.sqrt((nu - 2.0) / nu)
        return -np.sum(stats.t.logpdf(z / s, nu) - math.log(s))

    return float(optimize.minimize_scalar(nll, bounds=bounds, method="bounded").x)


class StudentTModel:
    """VaR = mu_l + s t_nu^{-1}(a), s = sigma sqrt((nu-2)/nu); nu by maximum likelihood."""

    name = "Student-t"

    def fit(self, returns, weights=None):
        losses = -portfolio_returns(returns, weights)
        self.mu, self.sigma = float(losses.mean()), float(losses.std(ddof=1))
        self.nu = fit_t_nu(((losses - self.mu) / self.sigma).to_numpy())
        return self

    def var(self, alpha):
        return esf.t_var(self.mu, self.sigma, self.nu, alpha)

    def es(self, alpha):
        return esf.t_es(self.mu, self.sigma, self.nu, alpha)

    def loss_sample(self):
        return None


class CornishFisherModel:
    """VaR = mu_l + z_cf sigma with the skewness/kurtosis expansion; ES by numerical integration.

    Unreliable at extreme skew or kurtosis, where the expansion stops being monotone.
    """

    name = "Cornish-Fisher"

    def fit(self, returns, weights=None):
        losses = -portfolio_returns(returns, weights)
        self.mu, self.sigma = float(losses.mean()), float(losses.std(ddof=1))
        self.skew = float(stats.skew(losses))
        self.exkurt = float(stats.kurtosis(losses))
        self.monotone = self.is_monotone()
        return self

    def is_monotone(self, lo: float = 0.90, hi: float = 0.9999, n: int = 2000) -> bool:
        """False when the expansion's quantile stops increasing over [lo, hi]: the
        Cornish-Fisher result is then unreliable and is flagged rather than reported as valid."""
        u = np.linspace(lo, hi, n)
        z = np.array([esf.cornish_fisher_z(a, self.skew, self.exkurt) for a in u])
        return bool(np.all(np.diff(z) > 0))

    def var(self, alpha):
        return esf.cf_var(self.mu, self.sigma, self.skew, self.exkurt, alpha)

    def es(self, alpha):
        return esf.cf_es_numeric(self.mu, self.sigma, self.skew, self.exkurt, alpha)

    def loss_sample(self):
        return None


def var_table(models: list, alphas, nav: float) -> pd.DataFrame:
    rows = []
    for m in models:
        for a in alphas:
            v, e = m.var(a), m.es(a)
            rows.append({"model": m.name, "alpha": a, "var_pct": v, "es_pct": e,
                         "var_usd": v * nav, "es_usd": e * nav, "es_var_ratio": e / v if v > 0 else np.nan})
    return pd.DataFrame(rows)
