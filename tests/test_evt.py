import math

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from quantedge.risk import evt


@pytest.fixture(scope="module")
def gpd_data():
    rng = np.random.default_rng(10)
    return stats.genpareto.rvs(0.25, scale=1.0, size=5000, random_state=rng)


def test_mle_recovers_parameters_within_two_se(gpd_data):
    f = evt.fit_gpd(gpd_data)
    assert abs(f.xi - 0.25) < 2 * f.se_xi
    assert abs(f.beta - 1.0) < 2 * f.se_beta


def test_mle_agrees_with_scipy(gpd_data):
    f = evt.fit_gpd(gpd_data)
    c, _, scale = stats.genpareto.fit(gpd_data, floc=0)
    ours = evt.gpd_nll(f.xi, f.beta, gpd_data)
    theirs = evt.gpd_nll(c, scale, gpd_data)
    assert ours <= theirs + 1e-6                      # at least as good a maximum
    assert f.xi == pytest.approx(c, abs=1e-3)
    assert f.beta == pytest.approx(scale, rel=1e-3)


def test_profile_ci_contains_estimate_and_truth(gpd_data):
    f = evt.fit_gpd(gpd_data)
    lo, hi = evt.profile_ci_xi(gpd_data, f)
    assert lo < f.xi < hi
    assert lo < 0.25 < hi
    assert hi - lo == pytest.approx(2 * 1.96 * f.se_xi, rel=0.25)  # close to Wald at this n


@pytest.mark.slow
def test_profile_ci_coverage_about_95_percent():
    rng = np.random.default_rng(3)
    hits = 0
    reps = 200
    for _ in range(reps):
        y = stats.genpareto.rvs(0.25, scale=1.0, size=500, random_state=rng)
        lo, hi = evt.profile_ci_xi(y)
        hits += lo <= 0.25 <= hi
    assert 0.90 <= hits / reps <= 0.99


def test_student_t_tail_index_is_positive_and_stable():
    """t(4) has tail index xi = 1/4, but GPD convergence is slow (second-order bias pulls the
    estimate to about 0.21 even at n = 2M), so test the range and the stability, not 0.25 exactly."""
    rng = np.random.default_rng(4)
    x = stats.t.rvs(4, size=500_000, random_state=rng)
    fits = []
    for q in (0.99, 0.995, 0.998):
        u = np.quantile(x, q)
        fits.append(evt.fit_gpd(x[x > u] - u))
    for f in fits:
        assert 0.15 <= f.xi <= 0.30
    lo = max(f.xi - 1.96 * f.se_xi for f in fits)
    hi = min(f.xi + 1.96 * f.se_xi for f in fits)
    assert lo <= hi  # confidence intervals overlap: the stability plot is flat


def test_var_at_threshold_level_equals_threshold(gpd_data):
    losses = gpd_data
    u = float(np.quantile(losses, 0.9))
    y = losses[losses > u] - u
    f = evt.fit_gpd(y)
    p_u = 1 - len(y) / len(losses)
    assert evt.evt_var(u, f, len(losses), len(y), p_u) == pytest.approx(u, abs=1e-12)


def test_es_exceeds_var_and_is_infinite_for_xi_at_least_one():
    f = evt.GPDFit(0.3, 1.0, 0.0, np.eye(2), 100)
    v = evt.evt_var(2.0, f, 1000, 100, 0.99)
    assert evt.evt_es(2.0, f, 1000, 100, 0.99) > v
    heavy = evt.GPDFit(1.1, 1.0, 0.0, np.eye(2), 100)
    assert math.isinf(evt.evt_es(2.0, heavy, 1000, 100, 0.99))


def test_evt_es_matches_monte_carlo():
    f = evt.GPDFit(0.2, 0.5, 0.0, np.eye(2), 0)
    rng = np.random.default_rng(1)
    u, n, n_u, p = 1.0, 10_000, 1000, 0.995
    y = stats.genpareto.rvs(0.2, scale=0.5, size=2_000_000, random_state=rng) + u
    v = evt.evt_var(u, f, n, n_u, p)
    # conditional tail beyond v given the exceedance distribution
    assert evt.evt_es(u, f, n, n_u, p) == pytest.approx(y[y > v].mean(), rel=0.01)


def test_gof_accepts_true_model_and_rejects_wrong_one(gpd_data):
    rng = np.random.default_rng(5)
    y = gpd_data[:400]
    good = evt.gof_bootstrap(y, evt.fit_gpd(y), rng, B=100)
    assert good["ad_p"] > 0.05
    lognormal = np.random.default_rng(6).lognormal(0, 1.2, 400)
    bad = evt.gof_bootstrap(lognormal, evt.fit_gpd(lognormal), rng, B=100)
    assert bad["ad_p"] < good["ad_p"]


def test_threshold_rules_return_valid_choices():
    rng = np.random.default_rng(8)
    losses = np.abs(stats.t.rvs(4, size=6000, random_state=rng)) * 0.01
    qs = [0.85, 0.875, 0.90, 0.925, 0.95, 0.975]
    ev = evt.threshold_evidence(losses, qs, rng, B=60)
    a = evt.select_threshold_diagnostic(losses, ev, min_exceed=50)
    b = evt.select_threshold_forwardstop(losses, ev)
    c = evt.select_threshold_fixed(losses, 0.95, ev)
    for ch in (a, b, c):
        assert ch.n_u >= 50
        assert ch.quantile in qs
    table = evt.sensitivity_table(losses, [a, b, c])
    assert (table["es_0.99"] > table["var_0.99"]).all()


def test_diagnostic_plots_data():
    rng = np.random.default_rng(9)
    losses = stats.genpareto.rvs(0.2, size=3000, random_state=rng)
    grid = np.quantile(losses, [0.8, 0.9, 0.95])
    me = evt.mean_excess(losses, grid)
    assert me["mean_excess"].is_monotonic_increasing  # xi > 0 -> rising mean excess
    st = evt.stability(losses, grid)
    assert st["xi"].between(-0.2, 0.6).all()
    hl = evt.hill(losses, [50, 100, 200])
    assert len(hl) == 3


def test_return_level_probability():
    assert evt.return_level_p(10) == pytest.approx(1 - 1 / 2520)


def test_evt_models_implement_risk_interface():
    rng = np.random.default_rng(12)
    r = pd.Series(stats.t.rvs(5, size=3000, random_state=rng) * 0.008)
    m = evt.EVTModel(threshold_q=0.95).fit(r)
    assert m.var(0.90) <= m.var(0.95) <= m.var(0.99) <= m.var(0.999)
    assert m.es(0.99) > m.var(0.99)
    c = evt.ConditionalEVTModel().fit(r)
    assert 0 < c.var(0.99) < c.es(0.99)


def test_bootstrap_ci_brackets_point_estimate(gpd_data):
    rng = np.random.default_rng(13)
    losses = gpd_data
    u = float(np.quantile(losses, 0.9))
    y = losses[losses > u] - u
    f = evt.fit_gpd(y)
    point = evt.evt_var(u, f, len(losses), len(y), 0.999)
    ci = evt.bootstrap_ci_var_es(u, f, len(losses), len(y), 0.999, rng, B=100)
    assert ci["var"][0] < point < ci["var"][1]
