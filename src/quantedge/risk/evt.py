"""Extreme Value Theory: peaks-over-threshold with a Generalised Pareto tail (Step 10).

Exceedances y = l - u for losses l > u (N_u of n observations) follow GPD(xi, beta):
    NLL = N_u ln beta + (1 + 1/xi) sum ln(1 + xi y / beta)        (xi != 0)
    VaR_p = u + (beta/xi) [((n/N_u)(1-p))^(-xi) - 1]
    ES_p  = VaR_p / (1-xi) + (beta - xi u) / (1-xi),   valid for xi < 1
The threshold is chosen by an explicit rule (A diagnostic, B ForwardStop, C fixed 95%), never ad hoc.
"""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import optimize, stats

from quantedge.risk import es as esf
from quantedge.risk.base import portfolio_returns
from quantedge.risk.garch import GarchFHSModel

XI_ZERO = 1e-8


# ---------------------------------------------------------------- GPD fit

@dataclass(frozen=True)
class GPDFit:
    xi: float
    beta: float
    nll: float
    cov: np.ndarray      # covariance of (xi, beta) from the observed information
    n: int

    @property
    def se_xi(self) -> float:
        return float(math.sqrt(max(self.cov[0, 0], 0.0)))

    @property
    def se_beta(self) -> float:
        return float(math.sqrt(max(self.cov[1, 1], 0.0)))


def gpd_nll(xi: float, beta: float, y: np.ndarray) -> float:
    if beta <= 0:
        return np.inf
    z = 1.0 + xi * y / beta
    if np.any(z <= 0):
        return np.inf
    if abs(xi) < XI_ZERO:
        return float(len(y) * math.log(beta) + y.sum() / beta)
    return float(len(y) * math.log(beta) + (1.0 + 1.0 / xi) * np.log(z).sum())


def pwm_start(y: np.ndarray) -> tuple[float, float]:
    """Probability-weighted-moment starting values (Hosking & Wallis, 1987)."""
    x = np.sort(y)
    n = len(x)
    p = (np.arange(1, n + 1) - 0.35) / n
    a0 = x.mean()
    a1 = np.mean(x * (1.0 - p))
    xi = 2.0 - a0 / (a0 - 2.0 * a1)
    beta = 2.0 * a0 * a1 / (a0 - 2.0 * a1)
    return float(np.clip(xi, -0.45, 0.9)), float(max(beta, 1e-6 * a0 + 1e-12))


def _hessian(f, x: np.ndarray, rel: float = 1e-4) -> np.ndarray:
    h = rel * np.maximum(np.abs(x), 1e-3)
    k = len(x)
    out = np.empty((k, k))
    for i in range(k):
        for j in range(k):
            ei, ej = np.eye(k)[i] * h[i], np.eye(k)[j] * h[j]
            out[i, j] = (f(x + ei + ej) - f(x + ei - ej) - f(x - ei + ej) + f(x - ei - ej)) / (4 * h[i] * h[j])
    return out


def fit_gpd(y: np.ndarray) -> GPDFit:
    """Maximum likelihood over (xi, log beta): Nelder-Mead from PWM starts, then L-BFGS-B polish."""
    y = np.asarray(y, dtype=float)
    if len(y) < 10 or np.any(y < 0):
        raise ValueError("fit_gpd needs at least 10 non-negative exceedances")
    xi0, b0 = pwm_start(y)
    obj = lambda t: gpd_nll(t[0], math.exp(t[1]), y)  # noqa: E731
    res = optimize.minimize(obj, [xi0, math.log(b0)], method="Nelder-Mead",
                            options={"xatol": 1e-10, "fatol": 1e-12, "maxiter": 20_000})
    with np.errstate(invalid="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # finite differences may touch the inf boundary
        res2 = optimize.minimize(obj, res.x, method="L-BFGS-B")
    best = res2 if res2.fun <= res.fun else res
    xi, beta = float(best.x[0]), float(math.exp(best.x[1]))
    hess = _hessian(lambda t: gpd_nll(t[0], t[1], y), np.array([xi, beta]))
    try:
        cov = np.linalg.inv(hess)
    except np.linalg.LinAlgError:
        cov = np.full((2, 2), np.nan)
    return GPDFit(xi, beta, float(best.fun), cov, len(y))


def profile_ci_xi(y: np.ndarray, fit: GPDFit | None = None, level: float = 0.95) -> tuple[float, float]:
    """Profile-likelihood interval for xi: where 2 (NLL_profile(xi) - NLL_min) <= chi2_1(level)."""
    y = np.asarray(y, dtype=float)
    fit = fit or fit_gpd(y)
    crit = stats.chi2.ppf(level, 1) / 2.0

    def prof(xi):
        lo = max(1e-12, -xi * y.max() * (1 + 1e-9)) if xi < 0 else 1e-12
        r = optimize.minimize_scalar(lambda lb: gpd_nll(xi, math.exp(lb), y),
                                     bounds=(math.log(max(lo, 1e-12)) + 1e-9, math.log(10 * y.max() + 1)),
                                     method="bounded")
        return r.fun - fit.nll - crit

    step = max(4 * fit.se_xi, 0.2) if np.isfinite(fit.se_xi) else 0.5
    lo_x, hi_x = fit.xi - step, fit.xi + step
    while prof(lo_x) < 0 and lo_x > -2:
        lo_x -= step
    while prof(hi_x) < 0 and hi_x < 3:
        hi_x += step
    return (float(optimize.brentq(prof, lo_x, fit.xi)), float(optimize.brentq(prof, fit.xi, hi_x)))


# ---------------------------------------------------------------- tail estimates

def evt_var(u: float, fit: GPDFit, n: int, n_u: int, p: float) -> float:
    tail = (n / n_u) * (1.0 - p)
    if abs(fit.xi) < XI_ZERO:
        return float(u - fit.beta * math.log(tail))
    return float(u + fit.beta / fit.xi * (tail ** (-fit.xi) - 1.0))


def evt_es(u: float, fit: GPDFit, n: int, n_u: int, p: float) -> float:
    """ES_p = VaR_p/(1-xi) + (beta - xi u)/(1-xi); infinite when xi >= 1 (flagged)."""
    if fit.xi >= 1.0:
        return float("inf")
    v = evt_var(u, fit, n, n_u, p)
    return float(v / (1.0 - fit.xi) + (fit.beta - fit.xi * u) / (1.0 - fit.xi))


def return_level_p(years: float, days_per_year: int = 252) -> float:
    """The 1-in-`years` daily loss is the VaR at p = 1 - 1/(252 x years)."""
    return 1.0 - 1.0 / (days_per_year * years)


def gpd_sample(fit: GPDFit, size: int, rng: np.random.Generator) -> np.ndarray:
    return stats.genpareto.rvs(fit.xi, scale=fit.beta, size=size, random_state=rng)


def bootstrap_ci_var_es(u: float, fit: GPDFit, n: int, n_u: int, p: float, rng: np.random.Generator,
                        B: int = 500, level: float = 0.95) -> dict[str, tuple[float, float]]:
    """Parametric bootstrap: simulate N_u exceedances, refit, recompute VaR and ES; percentile CI."""
    vs, es = [], []
    for _ in range(B):
        try:
            f = fit_gpd(gpd_sample(fit, n_u, rng))
        except (ValueError, FloatingPointError):
            continue
        vs.append(evt_var(u, f, n, n_u, p))
        es.append(evt_es(u, f, n, n_u, p))
    a = (1 - level) / 2
    q = lambda x: (float(np.quantile(x, a)), float(np.quantile(x, 1 - a)))  # noqa: E731
    return {"var": q(vs), "es": q(np.array(es)[np.isfinite(es)])}


# ---------------------------------------------------------------- diagnostics

def mean_excess(losses: np.ndarray, thresholds: np.ndarray) -> pd.DataFrame:
    """e(u) = E[l - u | l > u] with a 95% band (approximately linear above a good u)."""
    rows = []
    for u in thresholds:
        y = losses[losses > u] - u
        if len(y) < 5:
            continue
        rows.append({"u": u, "n_u": len(y), "mean_excess": y.mean(),
                     "ci_half": 1.96 * y.std(ddof=1) / math.sqrt(len(y))})
    return pd.DataFrame(rows)


def stability(losses: np.ndarray, thresholds: np.ndarray, min_n: int = 20) -> pd.DataFrame:
    """xi and the modified scale beta* = beta - xi u across thresholds (flat above a good u)."""
    rows = []
    for u in thresholds:
        y = losses[losses > u] - u
        if len(y) < min_n:
            continue
        f = fit_gpd(y)
        rows.append({"u": u, "n_u": len(y), "xi": f.xi, "xi_lo": f.xi - 1.96 * f.se_xi,
                     "xi_hi": f.xi + 1.96 * f.se_xi, "beta": f.beta,
                     "beta_star": f.beta - f.xi * u})
    return pd.DataFrame(rows)


def hill(losses: np.ndarray, ks) -> pd.DataFrame:
    """Hill estimator of xi from the k largest positive losses: mean(ln X_(i)) - ln X_(k+1)."""
    x = np.sort(losses[losses > 0])[::-1]
    rows = [{"k": k, "xi_hill": float(np.mean(np.log(x[:k])) - math.log(x[k]))}
            for k in ks if k < len(x)]
    return pd.DataFrame(rows)


def _gpd_cdf(y: np.ndarray, fit: GPDFit) -> np.ndarray:
    return stats.genpareto.cdf(y, fit.xi, scale=fit.beta)


def ad_statistic(y: np.ndarray, fit: GPDFit) -> float:
    """Anderson-Darling A^2 = -n - (1/n) sum (2i-1)[ln F(y_(i)) + ln(1 - F(y_(n+1-i)))]."""
    F = np.clip(_gpd_cdf(np.sort(y), fit), 1e-12, 1 - 1e-12)
    n = len(F)
    i = np.arange(1, n + 1)
    return float(-n - np.mean((2 * i - 1) * (np.log(F) + np.log(1 - F[::-1]))))


def ks_statistic(y: np.ndarray, fit: GPDFit) -> float:
    return float(stats.kstest(y, lambda v: _gpd_cdf(v, fit)).statistic)


def gof_bootstrap(y: np.ndarray, fit: GPDFit, rng: np.random.Generator, B: int = 200) -> dict[str, float]:
    """Parametric-bootstrap p-values for AD and KS: fit, simulate, refit, recompute the statistic."""
    ad0, ks0 = ad_statistic(y, fit), ks_statistic(y, fit)
    ad_b, ks_b = [], []
    for _ in range(B):
        ys = gpd_sample(fit, len(y), rng)
        try:
            fs = fit_gpd(ys)
        except ValueError:
            continue
        ad_b.append(ad_statistic(ys, fs))
        ks_b.append(ks_statistic(ys, fs))
    return {"ad": ad0, "ad_p": float(np.mean(np.array(ad_b) >= ad0)),
            "ks": ks0, "ks_p": float(np.mean(np.array(ks_b) >= ks0))}


# ---------------------------------------------------------------- threshold rules

@dataclass(frozen=True)
class ThresholdChoice:
    rule: str
    u: float
    quantile: float
    n_u: int
    fit: GPDFit
    evidence: pd.DataFrame = field(repr=False)
    note: str = ""


def threshold_evidence(losses: np.ndarray, quantiles, rng: np.random.Generator, B: int = 200) -> pd.DataFrame:
    rows = []
    for q in quantiles:
        u = float(np.quantile(losses, q))
        y = losses[losses > u] - u
        f = fit_gpd(y)
        g = gof_bootstrap(y, f, rng, B)
        rows.append({"quantile": q, "u": u, "n_u": len(y), "xi": f.xi, "se_xi": f.se_xi,
                     "xi_lo": f.xi - 1.96 * f.se_xi, "xi_hi": f.xi + 1.96 * f.se_xi,
                     "beta": f.beta, "beta_star": f.beta - f.xi * u, **g})
    return pd.DataFrame(rows)


def select_threshold_diagnostic(losses: np.ndarray, evidence: pd.DataFrame, min_exceed: int = 50,
                                ad_p_min: float = 0.10) -> ThresholdChoice:
    """Rule A: the lowest candidate u where xi is stable (its CI overlaps every higher CI),
    N_u >= min_exceed and the AD bootstrap p > ad_p_min (the bias-variance trade-off)."""
    ev = evidence.sort_values("u").reset_index(drop=True)
    chosen, note = None, ""
    for i, row in ev.iterrows():
        higher = ev.iloc[i + 1:]
        stable = all((row.xi_lo <= h.xi_hi) and (h.xi_lo <= row.xi_hi) for _, h in higher.iterrows())
        if row.n_u >= min_exceed and row.ad_p > ad_p_min and stable:
            chosen = row
            break
    if chosen is None:
        ok = ev[ev.n_u >= min_exceed]
        chosen = ok.iloc[-1] if len(ok) else ev.iloc[0]
        note = "no candidate met all criteria; highest threshold with enough exceedances used"
    return _choice("A (diagnostic)", losses, chosen, ev, note)


def select_threshold_forwardstop(losses: np.ndarray, evidence: pd.DataFrame, alpha: float = 0.10
                                 ) -> ThresholdChoice:
    """Rule B: ForwardStop (Bader, Yan & Zhang, 2018) on the ordered AD p-values.

    Y_i = -ln(1 - p_i); k_hat = max{k : (1/k) sum_{i<=k} Y_i <= alpha}; reject H_1..H_k_hat and
    choose threshold k_hat + 1 (the first one after the rejections stop)."""
    ev = evidence.sort_values("u").reset_index(drop=True)
    p = np.clip(ev["ad_p"].to_numpy(), 0.0, 1 - 1e-12)
    yv = -np.log(1.0 - p)
    avg = np.cumsum(yv) / np.arange(1, len(yv) + 1)
    rejected = np.nonzero(avg <= alpha)[0]
    k_hat = int(rejected.max()) + 1 if len(rejected) else 0
    note = ""
    if k_hat >= len(ev):
        k_hat, note = len(ev) - 1, "every threshold rejected; highest candidate used"
    return _choice("B (ForwardStop)", losses, ev.iloc[k_hat], ev, note)


def select_threshold_fixed(losses: np.ndarray, q: float = 0.95, evidence: pd.DataFrame | None = None
                           ) -> ThresholdChoice:
    """Rule C: the naive fixed-quantile benchmark, shown only to measure rule sensitivity."""
    u = float(np.quantile(losses, q))
    y = losses[losses > u] - u
    return ThresholdChoice("C (fixed 95%)", u, q, len(y), fit_gpd(y),
                           evidence if evidence is not None else pd.DataFrame())


def _choice(rule, losses, row, ev, note) -> ThresholdChoice:
    u = float(row.u)
    y = losses[losses > u] - u
    return ThresholdChoice(rule, u, float(row["quantile"]), len(y), fit_gpd(y), ev, note)


def sensitivity_table(losses: np.ndarray, choices: list[ThresholdChoice], ps=(0.99, 0.999)) -> pd.DataFrame:
    n = len(losses)
    rows = []
    for c in choices:
        row = {"rule": c.rule, "u": c.u, "quantile": c.quantile, "n_u": c.n_u, "xi": c.fit.xi,
               "xi_se": c.fit.se_xi, "beta": c.fit.beta}
        for p in ps:
            row[f"var_{p}"] = evt_var(c.u, c.fit, n, c.n_u, p)
            row[f"es_{p}"] = evt_es(c.u, c.fit, n, c.n_u, p)
        rows.append(row)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- RiskModel implementations

class EVTModel:
    """Unconditional POT model. Uses a fixed threshold quantile (from the static Rule A/B analysis)
    so it is fast enough for walk-forward use. Below the threshold's own level the empirical
    quantile is used, because the GPD formula only describes the tail beyond u."""

    name = "EVT"

    def __init__(self, threshold_q: float = 0.95):
        self.threshold_q = threshold_q

    def fit(self, returns, weights=None):
        self.losses = -portfolio_returns(returns, weights).to_numpy()
        self.n = len(self.losses)
        self.u = float(np.quantile(self.losses, self.threshold_q))
        y = self.losses[self.losses > self.u] - self.u
        self.n_u = len(y)
        self.gpd = fit_gpd(y)
        return self

    def _in_tail(self, alpha):
        return 1.0 - alpha <= self.n_u / self.n

    def var(self, alpha):
        if not self._in_tail(alpha):
            return esf.sample_var(self.losses, alpha)
        return evt_var(self.u, self.gpd, self.n, self.n_u, alpha)

    def es(self, alpha):
        if not self._in_tail(alpha):
            return esf.sample_es(self.losses, alpha)  # alpha below the threshold level: empirical
        return evt_es(self.u, self.gpd, self.n, self.n_u, alpha)

    def loss_sample(self):
        return self.losses


class ConditionalEVTModel:
    """McNeil-Frey (2000): GARCH(1,1)-t filter (GJR-GARCH with o = 1), then a GPD on the
    standardised losses -z.

    VaR_{t+1} = -mu + sigma_{t+1} VaR_z,  ES_{t+1} = -mu + sigma_{t+1} ES_z.
    """

    def __init__(self, threshold_q: float = 0.90, o: int = 0):
        self.threshold_q = threshold_q
        self.garch = GarchFHSModel(o=o)
        self.name = "GJR conditional EVT" if o else "Conditional EVT"

    def fit(self, returns, weights=None):
        self.garch.fit(returns, weights)
        z = self.garch.neg_z
        self.n = len(z)
        self.u = float(np.quantile(z, self.threshold_q))
        y = z[z > self.u] - self.u
        self.n_u = len(y)
        self.gpd = fit_gpd(y)
        self.mu, self.sigma_next = self.garch.mu, self.garch.sigma_next
        return self

    def update(self, r_new: float) -> None:
        """Roll the GARCH filter forward one day; the GPD on -z is kept until the next refit."""
        self.garch.update(r_new)
        self.sigma_next = self.garch.sigma_next

    def _z_var(self, alpha):
        if 1.0 - alpha > self.n_u / self.n:
            return esf.sample_var(self.garch.neg_z, alpha)
        return evt_var(self.u, self.gpd, self.n, self.n_u, alpha)

    def _z_es(self, alpha):
        if 1.0 - alpha > self.n_u / self.n:
            return esf.sample_es(self.garch.neg_z, alpha)
        return evt_es(self.u, self.gpd, self.n, self.n_u, alpha)

    def var(self, alpha):
        return float(-self.mu + self.sigma_next * self._z_var(alpha))

    def es(self, alpha):
        return float(-self.mu + self.sigma_next * self._z_es(alpha))

    def loss_sample(self):
        return None
