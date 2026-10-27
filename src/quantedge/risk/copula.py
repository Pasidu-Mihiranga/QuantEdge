"""t-copula Monte Carlo for joint crashes (Step 14 C).

Marginals: empirical body with GPD tails beyond the 10% / 90% quantiles (semi-parametric).
Dependence: Student-t copula with R from Kendall's tau (rho = sin(pi tau / 2)) and nu by profile
maximum likelihood on pseudo-observations u = rank / (n + 1). A Gaussian copula with the same R is
the comparison: it has zero tail dependence, the t-copula has
    lambda_L = 2 t_{nu+1}( -sqrt((nu + 1)(1 - rho) / (1 + rho)) ).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import optimize, stats

from quantedge.risk import es as esf
from quantedge.risk.evt import fit_gpd


def pseudo_observations(x: pd.DataFrame) -> np.ndarray:
    return x.rank().to_numpy() / (len(x) + 1)


def kendall_correlation(x: pd.DataFrame) -> np.ndarray:
    tau = x.corr(method="kendall").to_numpy()
    R = np.sin(np.pi * tau / 2)
    w, v = np.linalg.eigh(R)                  # repair to the nearest positive-definite matrix
    R = v @ np.diag(np.clip(w, 1e-6, None)) @ v.T
    d = np.sqrt(np.diag(R))
    return R / np.outer(d, d)


def t_copula_loglik(u: np.ndarray, R: np.ndarray, nu: float) -> float:
    """log c(u) = log f_t,R,nu(z) - sum_j log f_t,nu(z_j), with z_j = t_nu^{-1}(u_j)."""
    z = stats.t.ppf(u, nu)
    joint = stats.multivariate_t.logpdf(z, loc=np.zeros(R.shape[0]), shape=R, df=nu)
    return float(np.sum(joint - stats.t.logpdf(z, nu).sum(axis=1)))


def fit_t_copula(u: np.ndarray, R: np.ndarray, bounds=(2.1, 60.0)) -> float:
    """Profile maximum likelihood for nu with R held at its Kendall-tau estimate."""
    res = optimize.minimize_scalar(lambda nu: -t_copula_loglik(u, R, nu), bounds=bounds, method="bounded")
    return float(res.x)


def tail_dependence(rho: float, nu: float) -> float:
    return float(2 * stats.t.cdf(-np.sqrt((nu + 1) * (1 - rho) / (1 + rho)), nu + 1))


@dataclass
class SemiParametricMarginal:
    """Empirical quantiles in the body, GPD beyond the lower and upper `tail` quantiles."""

    sorted_x: np.ndarray
    lo_u: float
    hi_u: float
    lo_fit: object
    hi_fit: object
    tail: float

    @classmethod
    def fit(cls, x: np.ndarray, tail: float = 0.10) -> SemiParametricMarginal:
        s = np.sort(np.asarray(x, float))
        lo_u, hi_u = np.quantile(s, tail), np.quantile(s, 1 - tail)
        lo_fit = fit_gpd(lo_u - s[s < lo_u])
        hi_fit = fit_gpd(s[s > hi_u] - hi_u)
        return cls(s, float(lo_u), float(hi_u), lo_fit, hi_fit, tail)

    def ppf(self, u: np.ndarray) -> np.ndarray:
        u = np.asarray(u, float)
        out = np.quantile(self.sorted_x, np.clip(u, 0, 1))
        lo, hi = u < self.tail, u > 1 - self.tail
        if lo.any():
            p = 1 - u[lo] / self.tail                       # conditional exceedance probability
            out[lo] = self.lo_u - stats.genpareto.ppf(p, self.lo_fit.xi, scale=self.lo_fit.beta)
        if hi.any():
            p = (u[hi] - (1 - self.tail)) / self.tail
            out[hi] = self.hi_u + stats.genpareto.ppf(p, self.hi_fit.xi, scale=self.hi_fit.beta)
        return out


def simulate_copula(R: np.ndarray, n: int, rng: np.random.Generator, nu: float | None = None) -> np.ndarray:
    """Uniforms from a t-copula (nu given) or a Gaussian copula (nu None)."""
    L = np.linalg.cholesky(R)
    z = rng.standard_normal((n, R.shape[0])) @ L.T
    if nu is None:
        return stats.norm.cdf(z)
    w = np.sqrt(rng.chisquare(nu, n) / nu)[:, None]
    return stats.t.cdf(z / w, nu)


class CopulaMCModel:
    """RiskModel built from a copula plus semi-parametric marginals (asset returns -> portfolio losses)."""

    def __init__(self, n_sims: int = 100_000, rng: np.random.Generator | None = None, gaussian: bool = False):
        self.n_sims, self.gaussian = n_sims, gaussian
        self.rng = rng if rng is not None else np.random.default_rng(0)
        self.name = "Gaussian copula MC" if gaussian else "t-copula MC"

    def fit(self, returns: pd.DataFrame, weights) -> CopulaMCModel:
        x = returns.dropna()
        self.R = kendall_correlation(x)
        self.nu = None if self.gaussian else fit_t_copula(pseudo_observations(x), self.R)
        u = simulate_copula(self.R, self.n_sims, self.rng, self.nu)
        sims = np.column_stack([SemiParametricMarginal.fit(x[c].to_numpy()).ppf(u[:, j])
                                for j, c in enumerate(x.columns)])
        w = weights.reindex(x.columns).to_numpy() if isinstance(weights, pd.Series) else np.asarray(weights)
        self.asset_sims = pd.DataFrame(sims, columns=x.columns)
        self.losses = -(sims @ w)
        return self

    def var(self, alpha):
        return esf.sample_var(self.losses, alpha)

    def es(self, alpha):
        return esf.sample_es(self.losses, alpha)

    def loss_sample(self):
        return self.losses

    def joint_crash_probability(self, assets: list[str], q: float = 0.05, history: pd.DataFrame | None = None) -> float:
        """P(all `assets` below their own q-quantile on the same day) in the simulation."""
        sims = self.asset_sims[assets]
        cut = (history[assets] if history is not None else sims).quantile(q)
        return float((sims < cut).all(axis=1).mean())
