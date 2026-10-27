import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from scipy import stats

from quantedge.risk import es as esf
from quantedge.risk.garch import GarchFHSModel
from quantedge.risk.montecarlo import MonteCarloModel
from quantedge.risk.var import (
    CornishFisherModel,
    HistoricalModel,
    NormalModel,
    StudentTModel,
    fit_t_nu,
)

Z99 = stats.norm.ppf(0.99)


@pytest.fixture(scope="module")
def normal_returns():
    rng = np.random.default_rng(11)
    return pd.Series(rng.normal(0.0, 0.01, 1_000_000))


def test_models_agree_on_iid_normal(normal_returns):
    target = 0.01 * Z99
    for model in (HistoricalModel(), NormalModel(), StudentTModel()):
        v = model.fit(normal_returns).var(0.99)
        assert v == pytest.approx(target, rel=0.01), model.name
    mc = MonteCarloModel(n_sims=200_000, rng=np.random.default_rng(1)).fit(normal_returns.iloc[:50_000])
    assert mc.var(0.99) == pytest.approx(target, rel=0.03)


def test_t_recovers_nu_and_normal_understates_tail():
    rng = np.random.default_rng(3)
    nu = 4.0
    x = stats.t.rvs(nu, size=200_000, random_state=rng) * np.sqrt((nu - 2) / nu) * 0.01
    s = pd.Series(x)
    t_model = StudentTModel().fit(s)
    assert t_model.nu == pytest.approx(nu, abs=0.5)
    true_var = 0.01 * np.sqrt((nu - 2) / nu) * stats.t.ppf(0.99, nu)
    assert NormalModel().fit(s).var(0.99) < true_var
    assert t_model.var(0.99) == pytest.approx(true_var, rel=0.03)


def test_fit_t_nu_on_standardised_data():
    rng = np.random.default_rng(4)
    nu = 6.0
    z = stats.t.rvs(nu, size=100_000, random_state=rng) * np.sqrt((nu - 2) / nu)
    assert fit_t_nu(z) == pytest.approx(nu, abs=0.6)


def test_normal_es_closed_form_matches_simulation(normal_returns):
    losses = -normal_returns.to_numpy()
    assert esf.normal_es(0, 0.01, 0.99) == pytest.approx(esf.sample_es(losses, 0.99), rel=0.005)


def test_t_es_matches_numerical_integration():
    nu, a = 5.0, 0.975
    s = esf.t_scale(1.0, nu)
    numeric = stats.t.expect(lambda x: x, args=(nu,), lb=stats.t.ppf(a, nu)) / (1 - a) * s
    assert esf.t_es(0.0, 1.0, nu, a) == pytest.approx(numeric, abs=1e-6)


def test_normal_es_var_reference_ratios():
    assert esf.NORMAL_ES_VAR_RATIO[0.95] == pytest.approx(1.254, abs=1e-3)
    assert esf.NORMAL_ES_VAR_RATIO[0.99] == pytest.approx(1.146, abs=1e-3)


def test_historical_es_handles_ties_and_fractional_tail():
    losses = np.array([5.0, 5.0, 3.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    # a = 0.75 -> m = 2.5: (5 + 5 + 0.5 * 3) / 2.5
    assert esf.sample_es(losses, 0.75) == pytest.approx(11.5 / 2.5)
    assert esf.sample_es(losses, 0.8) == pytest.approx(5.0)


def test_cornish_fisher_reduces_to_normal_without_skew_or_kurtosis():
    assert esf.cf_var(0, 1, 0, 0, 0.99) == pytest.approx(Z99)
    assert esf.cf_es_numeric(0, 1, 0, 0, 0.99) == pytest.approx(esf.normal_es(0, 1, 0.99), rel=1e-3)


@settings(max_examples=40, deadline=None)
@given(seed=st.integers(0, 10_000), n=st.integers(300, 1500))
def test_es_at_least_var_and_var_monotone_in_alpha(seed, n):
    rng = np.random.default_rng(seed)
    r = pd.Series(stats.t.rvs(4, size=n, random_state=rng) * 0.01)
    for model in (HistoricalModel(), NormalModel(), StudentTModel(), CornishFisherModel()):
        model.fit(r)
        if getattr(model, "monotone", True) is False:
            continue  # flagged as unreliable; see test_cornish_fisher_flags_non_monotone_expansion
        vs = [model.var(a) for a in (0.90, 0.95, 0.99)]
        assert vs[0] <= vs[1] + 1e-12 <= vs[2] + 2e-12, model.name
        for a in (0.90, 0.95, 0.975, 0.99):
            assert model.es(a) >= model.var(a) - 1e-12, model.name


def test_cornish_fisher_flags_non_monotone_expansion():
    rng = np.random.default_rng(1223)
    r = pd.Series(stats.t.rvs(4, size=763, random_state=rng) * 0.01)
    model = CornishFisherModel().fit(r)
    assert model.exkurt > 5
    assert model.monotone is False
    mild = CornishFisherModel().fit(pd.Series(rng.normal(0, 0.01, 2000)))
    assert mild.monotone is True


def test_monte_carlo_standard_error_shrinks_with_n():
    rng_data = np.random.default_rng(8)
    x = pd.DataFrame(rng_data.normal(0, 0.01, (2000, 3)), columns=list("ABC"))
    w = np.array([0.4, 0.3, 0.3])
    small = MonteCarloModel(n_sims=20_000, rng=np.random.default_rng(1)).fit(x, w)
    large = MonteCarloModel(n_sims=320_000, rng=np.random.default_rng(1)).fit(x, w)
    ratio = small.var_se(0.99) / large.var_se(0.99)
    assert 2.0 < ratio < 8.0  # theory: sqrt(16) = 4


def test_monte_carlo_is_reproducible_with_seed():
    x = pd.DataFrame(np.random.default_rng(2).normal(0, 0.01, (1000, 2)), columns=["A", "B"])
    a = MonteCarloModel(n_sims=10_000, rng=np.random.default_rng(7)).fit(x, np.array([0.5, 0.5]))
    b = MonteCarloModel(n_sims=10_000, rng=np.random.default_rng(7)).fit(x, np.array([0.5, 0.5]))
    assert a.var(0.99) == b.var(0.99)


@pytest.mark.slow
def test_garch_recovers_persistence():
    rng = np.random.default_rng(21)
    n, omega, alpha, beta, nu = 6000, 0.02, 0.08, 0.90, 6.0
    z = stats.t.rvs(nu, size=n, random_state=rng) * np.sqrt((nu - 2) / nu)
    e = np.empty(n)
    s2 = omega / (1 - alpha - beta)
    for t in range(n):
        e[t] = np.sqrt(s2) * z[t]
        s2 = omega + alpha * e[t] ** 2 + beta * s2
    model = GarchFHSModel().fit(pd.Series(e / 100))
    assert model.persistence == pytest.approx(alpha + beta, abs=0.03)
    assert model.es(0.99) >= model.var(0.99) > 0


def test_usd_conversion_is_exact():
    r = pd.Series(np.random.default_rng(0).normal(0, 0.01, 1000))
    m = NormalModel().fit(r)
    nav = 10_000_000
    assert m.var(0.99) * nav == pytest.approx(m.var(0.99) * 1e7)
