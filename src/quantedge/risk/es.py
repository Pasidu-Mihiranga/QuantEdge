"""Expected Shortfall estimators (Step 09 §3.1–3.2).

ES_a = 1/(1-a) integral_a^1 VaR_u du   (quantile-integral definition, Acerbi-Tasche)
"""

from __future__ import annotations

import math

import numpy as np
from scipy import stats


def sample_var(losses: np.ndarray, alpha: float) -> float:
    """Empirical alpha-quantile of losses, `method="higher"` (conservative)."""
    return float(np.quantile(np.asarray(losses, dtype=float), alpha, method="higher"))


def sample_es(losses: np.ndarray, alpha: float) -> float:
    """Acerbi-Tasche estimator of the quantile-integral ES on a sample of n losses.

    With losses sorted descending L_(1) >= L_(2) >= ..., m = (1-a) n and k = floor(m):
        ES = [sum_{i<=k} L_(i) + (m - k) L_(k+1)] / m
    This handles ties and non-integer tail sizes exactly.
    """
    x = np.sort(np.asarray(losses, dtype=float))[::-1]
    m = (1.0 - alpha) * len(x)
    k = int(math.floor(m + 1e-12))
    total = x[:k].sum()
    if m - k > 1e-12:
        total += (m - k) * x[k]
    return float(total / m)


def normal_var(mu_loss: float, sigma: float, alpha: float) -> float:
    """VaR = mu_l + z_a sigma (mu_l is the mean loss = minus the mean return)."""
    return float(mu_loss + stats.norm.ppf(alpha) * sigma)


def normal_es(mu_loss: float, sigma: float, alpha: float) -> float:
    """ES = mu_l + sigma phi(z_a) / (1 - a)."""
    z = stats.norm.ppf(alpha)
    return float(mu_loss + sigma * stats.norm.pdf(z) / (1.0 - alpha))


def t_scale(sigma: float, nu: float) -> float:
    """Scale of a Student-t with variance sigma^2: s = sigma sqrt((nu - 2) / nu)."""
    return sigma * math.sqrt((nu - 2.0) / nu)


def t_var(mu_loss: float, sigma: float, nu: float, alpha: float) -> float:
    """VaR = mu_l + s t_nu^{-1}(a)."""
    return float(mu_loss + t_scale(sigma, nu) * stats.t.ppf(alpha, nu))


def t_es(mu_loss: float, sigma: float, nu: float, alpha: float) -> float:
    """ES = mu_l + s [g_nu(t_a) / (1 - a)] [(nu + t_a^2) / (nu - 1)]."""
    ta = stats.t.ppf(alpha, nu)
    return float(mu_loss + t_scale(sigma, nu) * stats.t.pdf(ta, nu) / (1.0 - alpha)
                 * (nu + ta**2) / (nu - 1.0))


def cornish_fisher_z(alpha: float, skew: float, exkurt: float) -> float:
    """z_cf = z + (z^2 - 1) S / 6 + (z^3 - 3z) K / 24 - (2 z^3 - 5z) S^2 / 36."""
    z = stats.norm.ppf(alpha)
    return float(z + (z**2 - 1) * skew / 6 + (z**3 - 3 * z) * exkurt / 24
                 - (2 * z**3 - 5 * z) * skew**2 / 36)


def cf_var(mu_loss: float, sigma: float, skew: float, exkurt: float, alpha: float) -> float:
    return float(mu_loss + cornish_fisher_z(alpha, skew, exkurt) * sigma)


def cf_es_numeric(mu_loss: float, sigma: float, skew: float, exkurt: float, alpha: float,
                  n: int = 4000) -> float:
    """ES by numerically integrating the Cornish-Fisher quantile over u in [a, 1) (midpoint rule)."""
    u = alpha + (1.0 - alpha) * (np.arange(n) + 0.5) / n
    z = stats.norm.ppf(u)
    zcf = z + (z**2 - 1) * skew / 6 + (z**3 - 3 * z) * exkurt / 24 - (2 * z**3 - 5 * z) * skew**2 / 36
    return float(mu_loss + sigma * zcf.mean())


NORMAL_ES_VAR_RATIO = {a: normal_es(0, 1, a) / normal_var(0, 1, a) for a in (0.90, 0.95, 0.975, 0.99)}
