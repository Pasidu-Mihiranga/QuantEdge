"""Candidate portfolios under the IPS constraints (Step 07 §3.1–3.3).

Inputs: Ledoit-Wolf covariance (annualised) and CAPM-implied expected returns (annualised).
Historical scenarios (daily simple returns) drive the CVaR / ES formulations.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import cvxpy as cp
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.covariance import LedoitWolf

from quantedge.decision.ips import OptimizerConstraints

A = 252
SOLVERS = ("CLARABEL", "ECOS", "SCS")


@dataclass(frozen=True)
class OptResult:
    weights: pd.Series
    status: str
    objective: float
    diagnostics: dict = field(default_factory=dict)


def estimate_inputs(window: pd.DataFrame, rf_annual: float, market: str = "SPY",
                    mrp: float = 0.05) -> tuple[pd.Series, pd.DataFrame]:
    """(mu, Sigma), both annualised.

    Sigma: Ledoit-Wolf shrinkage of daily simple returns x 252.
    mu: CAPM prior mu_i = rf + beta_i x MRP, with beta_i = cov(R_i, R_m) / var(R_m) on the window.
    """
    x = window.dropna()
    lw = LedoitWolf().fit(x.to_numpy())
    sigma = pd.DataFrame(lw.covariance_ * A, index=x.columns, columns=x.columns)
    sample = x.cov()
    betas = sample[market] / sample.loc[market, market]
    mu = (rf_annual + betas * mrp).rename("mu")
    return mu, sigma


def _ips_constraints(w, cons: OptimizerConstraints, scale=1.0) -> list:
    out = [cp.sum(w) == scale, w >= cons.lower * scale, w <= cons.upper * scale]
    if cons.A_ub.shape[0]:
        out.append(cons.A_ub @ w <= cons.b_ub * scale)
    return out


def _solve(problem: cp.Problem) -> str:
    for solver in SOLVERS:
        if solver not in cp.installed_solvers():
            continue
        try:
            problem.solve(solver=solver)
        except cp.error.SolverError:
            continue
        if problem.status in ("optimal", "optimal_inaccurate"):
            return problem.status
    return problem.status or "solver_failed"


def _result(w_val, tickers, status, objective, **diag) -> OptResult:
    w = np.clip(np.asarray(w_val, dtype=float).ravel(), 0.0, None)
    w = w / w.sum()
    return OptResult(pd.Series(w, index=list(tickers)), status, float(objective), diag)


def equal_weight(tickers) -> OptResult:
    n = len(tickers)
    return OptResult(pd.Series(1.0 / n, index=list(tickers)), "fixed", float("nan"),
                     {"note": "shown even if it breaches IPS group limits"})


def fixed(weights: dict[str, float], tickers) -> OptResult:
    w = pd.Series(weights, dtype=float).reindex(list(tickers), fill_value=0.0)
    return OptResult(w / w.sum(), "fixed", float("nan"))


def gmv(sigma: pd.DataFrame, cons: OptimizerConstraints) -> OptResult:
    """min w' Sigma w subject to the IPS constraints."""
    w = cp.Variable(len(cons.tickers))
    prob = cp.Problem(cp.Minimize(cp.quad_form(w, cp.psd_wrap(sigma.to_numpy()))),
                      _ips_constraints(w, cons))
    status = _solve(prob)
    return _result(w.value, cons.tickers, status, prob.value)


def max_sharpe(mu: pd.Series, sigma: pd.DataFrame, rf_annual: float,
               cons: OptimizerConstraints) -> OptResult:
    """Homogenised tangency: min y' Sigma y s.t. (mu - rf)' y = 1, sum y = kappa,
    lb kappa <= y <= ub kappa, group caps x kappa, kappa >= 0; then w = y / kappa."""
    excess = (mu - rf_annual).to_numpy()
    if excess.max() <= 0:
        res = gmv(sigma, cons)
        return OptResult(res.weights, "fallback_gmv", res.objective,
                         {"note": "no asset has expected return above rf"})
    n = len(cons.tickers)
    y, kappa = cp.Variable(n), cp.Variable(nonneg=True)
    constraints = [excess @ y == 1, cp.sum(y) == kappa, y >= cons.lower * kappa, y <= cons.upper * kappa]
    if cons.A_ub.shape[0]:
        constraints.append(cons.A_ub @ y <= cons.b_ub * kappa)
    prob = cp.Problem(cp.Minimize(cp.quad_form(y, cp.psd_wrap(sigma.to_numpy()))), constraints)
    status = _solve(prob)
    w = y.value / kappa.value
    sr = float(excess @ w / np.sqrt(w @ sigma.to_numpy() @ w))
    return _result(w, cons.tickers, status, sr, sharpe_ex_ante=sr)


def project_onto_constraints(target: np.ndarray, cons: OptimizerConstraints) -> np.ndarray:
    """Closest (least-squares) weights satisfying the IPS."""
    w = cp.Variable(len(cons.tickers))
    prob = cp.Problem(cp.Minimize(cp.sum_squares(w - target)), _ips_constraints(w, cons))
    _solve(prob)
    return np.asarray(w.value, dtype=float)


def erc(sigma: pd.DataFrame, cons: OptimizerConstraints) -> OptResult:
    """Equal risk contribution (Spinu): min 1/2 x' Sigma x - (1/n) sum ln x_i, w = x / sum x;
    then projected onto the IPS bounds, reporting the deviation."""
    s = sigma.to_numpy()
    n = len(s)
    x0 = np.ones(n) / np.sqrt(np.diag(s))
    fun = lambda x: 0.5 * x @ s @ x - np.log(x).sum() / n  # noqa: E731
    jac = lambda x: s @ x - 1.0 / (n * x)  # noqa: E731
    res = minimize(fun, x0, jac=jac, bounds=[(1e-10, None)] * n, method="L-BFGS-B",
                   options={"ftol": 1e-15, "gtol": 1e-12, "maxiter": 10_000})
    w_erc = res.x / res.x.sum()
    w = project_onto_constraints(w_erc, cons)
    rc = w_erc * (s @ w_erc)
    return _result(w, cons.tickers, "optimal" if res.success else "erc_not_converged",
                   float(res.fun), unconstrained=pd.Series(w_erc, index=list(cons.tickers)),
                   projection_l1=float(np.abs(w - w_erc).sum()),
                   rc_spread=float(rc.max() - rc.min()))


def _cvar_terms(scenarios: np.ndarray, w, alpha: float):
    s = scenarios.shape[0]
    zeta = cp.Variable()
    u = cp.Variable(s, nonneg=True)
    cvar = zeta + cp.sum(u) / ((1 - alpha) * s)
    cons = [u >= -scenarios @ w - zeta]
    return cvar, cons


def min_cvar(scenarios: pd.DataFrame, cons: OptimizerConstraints, alpha: float = 0.99) -> OptResult:
    """Rockafellar-Uryasev: min zeta + 1/((1-alpha) S) sum u_s, u_s >= -r_s'w - zeta, u_s >= 0."""
    w = cp.Variable(len(cons.tickers))
    cvar, extra = _cvar_terms(scenarios[list(cons.tickers)].to_numpy(), w, alpha)
    prob = cp.Problem(cp.Minimize(cvar), _ips_constraints(w, cons) + extra)
    status = _solve(prob)
    return _result(w.value, cons.tickers, status, prob.value, cvar_in_sample=float(prob.value))


def robust_mean_es(mu: pd.Series, sigma: pd.DataFrame, scenarios: pd.DataFrame,
                   cons: OptimizerConstraints, es_budget: float, vol_max: float,
                   alpha: float = 0.99) -> OptResult:
    """max mu'w s.t. RU-CVaR_alpha(w) <= es_budget (daily), w' Sigma w <= vol_max^2, IPS.

    If the budget is infeasible, fall back to the ES-minimising portfolio and say so.
    """
    w = cp.Variable(len(cons.tickers))
    cvar, extra = _cvar_terms(scenarios[list(cons.tickers)].to_numpy(), w, alpha)
    constraints = _ips_constraints(w, cons) + extra + [
        cvar <= es_budget, cp.quad_form(w, cp.psd_wrap(sigma.to_numpy())) <= vol_max**2]
    prob = cp.Problem(cp.Maximize(mu.reindex(list(cons.tickers)).to_numpy() @ w), constraints)
    status = _solve(prob)
    if status not in ("optimal", "optimal_inaccurate"):
        res = min_cvar(scenarios, cons, alpha)
        return OptResult(res.weights, "fallback_min_es", res.objective,
                         {**res.diagnostics, "note": f"ES/vol budget infeasible ({status})"})
    return _result(w.value, cons.tickers, status, prob.value, cvar_in_sample=float(cvar.value))


def efficient_frontier(mu: pd.Series, sigma: pd.DataFrame, cons: OptimizerConstraints,
                       n: int = 40) -> pd.DataFrame:
    """min w' Sigma w s.t. mu'w = target, IPS; targets span the feasible return range."""
    m = mu.reindex(list(cons.tickers)).to_numpy()
    s = sigma.to_numpy()
    lo = float(m @ gmv(sigma, cons).weights.to_numpy())
    w = cp.Variable(len(m))
    top = cp.Problem(cp.Maximize(m @ w), _ips_constraints(w, cons))
    _solve(top)
    rows = []
    for target in np.linspace(lo, float(top.value), n):
        w = cp.Variable(len(m))
        prob = cp.Problem(cp.Minimize(cp.quad_form(w, cp.psd_wrap(s))),
                          _ips_constraints(w, cons) + [m @ w == target])
        if _solve(prob) in ("optimal", "optimal_inaccurate"):
            wv = np.asarray(w.value)
            rows.append({"target": target, "mu": float(m @ wv), "vol": float(np.sqrt(wv @ s @ wv)),
                         **dict(zip(cons.tickers, wv, strict=True))})
    return pd.DataFrame(rows)


def diversification_ratio(w: pd.Series, sigma: pd.DataFrame) -> float:
    """sum_i w_i sigma_i / sigma_p (> 1 means diversification benefit)."""
    vols = np.sqrt(np.diag(sigma.to_numpy()))
    wv = w.reindex(sigma.columns).to_numpy()
    return float(wv @ vols / np.sqrt(wv @ sigma.to_numpy() @ wv))
