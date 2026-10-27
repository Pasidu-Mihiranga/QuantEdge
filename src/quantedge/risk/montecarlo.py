"""Monte Carlo VaR / ES from a multivariate Student-t (Step 08 §3.2).

Asset returns x = mu + sqrt((nu-2)/nu) L z / sqrt(W / nu), z ~ N(0, I), W ~ chi2_nu, L L' = Sigma
(Ledoit-Wolf, daily), with nu chosen by maximum likelihood. Correlations are held fixed, so the
model does not capture crisis correlation (a stated limitation). Seeded for reproducibility.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy import optimize, special
from sklearn.covariance import LedoitWolf

from quantedge.risk import es as esf


def fit_mvt_nu(x: np.ndarray, sigma: np.ndarray, bounds=(2.05, 100.0)) -> float:
    """MLE of nu for a unit-covariance-scaled multivariate t (scale matrix = Sigma (nu-2)/nu)."""
    d = x.shape[1]
    centred = x - x.mean(axis=0)
    inv = np.linalg.inv(sigma)
    q = np.einsum("ij,jk,ik->i", centred, inv, centred)
    _, logdet = np.linalg.slogdet(sigma)

    def nll(nu):
        c = (nu - 2.0) / nu
        quad = q / c
        ll = (special.gammaln((nu + d) / 2) - special.gammaln(nu / 2) - 0.5 * d * math.log(nu * math.pi)
              - 0.5 * (logdet + d * math.log(c)) - 0.5 * (nu + d) * np.log1p(quad / nu))
        return -float(np.sum(ll))

    return float(optimize.minimize_scalar(nll, bounds=bounds, method="bounded").x)


class MonteCarloModel:
    name = "Monte Carlo"

    def __init__(self, n_sims: int = 100_000, rng: np.random.Generator | None = None, n_batches: int = 20):
        self.n_sims, self.n_batches = n_sims, n_batches
        self.rng = rng if rng is not None else np.random.default_rng(0)

    def fit(self, returns, weights=None):
        if isinstance(returns, pd.Series):
            x = returns.dropna().to_numpy()[:, None]
            w = np.ones(1)
        else:
            x = returns.dropna().to_numpy()
            w = weights.reindex(returns.columns).to_numpy() if isinstance(weights, pd.Series) else np.asarray(weights)
        mu = x.mean(axis=0)
        sigma = LedoitWolf().fit(x).covariance_ if x.shape[1] > 1 else np.atleast_2d(x.var(ddof=1))
        self.nu = fit_mvt_nu(x, sigma)
        chol = np.linalg.cholesky(sigma)
        z = self.rng.standard_normal((self.n_sims, x.shape[1]))
        mix = np.sqrt(self.rng.chisquare(self.nu, self.n_sims) / self.nu)[:, None]
        sims = mu + math.sqrt((self.nu - 2.0) / self.nu) * (z @ chol.T) / mix
        self.losses = -(sims @ w)
        return self

    def var(self, alpha):
        return esf.sample_var(self.losses, alpha)

    def es(self, alpha):
        return esf.sample_es(self.losses, alpha)

    def var_se(self, alpha):
        """Batch standard error of the VaR estimate (n_batches equal batches)."""
        batches = np.array_split(self.losses, self.n_batches)
        est = [esf.sample_var(b, alpha) for b in batches]
        return float(np.std(est, ddof=1) / math.sqrt(self.n_batches))

    def es_se(self, alpha):
        batches = np.array_split(self.losses, self.n_batches)
        est = [esf.sample_es(b, alpha) for b in batches]
        return float(np.std(est, ddof=1) / math.sqrt(self.n_batches))

    def loss_sample(self):
        return self.losses
