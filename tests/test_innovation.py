"""Step 14 innovation extensions: acceptance tests."""

import numpy as np
import pandas as pd
import pytest

from quantedge.risk.regime import filtered_high_prob, fit_markov, regime_risk


@pytest.fixture(scope="module")
def two_regimes():
    """Simulated 2-regime returns: calm sigma 0.5%, high-vol sigma 2%, sticky transitions."""
    rng = np.random.default_rng(0)
    n, p_cc, p_hh = 3000, 0.99, 0.95
    s = np.zeros(n, dtype=int)
    for t in range(1, n):
        stay = p_cc if s[t - 1] == 0 else p_hh
        s[t] = s[t - 1] if rng.random() < stay else 1 - s[t - 1]
    sig = np.where(s == 0, 0.005, 0.02)
    idx = pd.bdate_range("2010-01-01", periods=n)
    return pd.Series(rng.normal(0, 1, n) * sig, index=idx), s


@pytest.mark.slow
def test_markov_recovers_regime_volatilities_and_persistence(two_regimes):
    r, _ = two_regimes
    fit = fit_markov(r)
    assert fit.sigma[0] == pytest.approx(0.005, rel=0.15)
    assert fit.sigma[1] == pytest.approx(0.02, rel=0.15)
    assert fit.p_stay[0] == pytest.approx(0.99, abs=0.01)
    assert fit.p_stay[1] == pytest.approx(0.95, abs=0.03)


@pytest.mark.slow
def test_filtered_probabilities_ignore_the_future(two_regimes):
    r, states = two_regimes
    fit = fit_markov(r.iloc[:2000])
    full = filtered_high_prob(r, fit)
    cut = filtered_high_prob(r.iloc[:2500], fit)
    pd.testing.assert_series_equal(full.iloc[:2500], cut)          # truncation test
    accuracy = ((full > 0.5).astype(int).to_numpy() == states).mean()
    assert accuracy > 0.9
    rr = regime_risk(r, full).set_index(["regime", "alpha"])
    assert rr.loc[("high-vol", 0.99), "es"] > 2 * rr.loc[("calm", 0.99), "es"]


def test_t_copula_recovers_nu_and_rho():
    from scipy import stats

    from quantedge.risk.copula import (
        fit_t_copula,
        kendall_correlation,
        pseudo_observations,
        simulate_copula,
    )

    rng = np.random.default_rng(1)
    R = np.array([[1.0, 0.6], [0.6, 1.0]])
    u = simulate_copula(R, 4000, rng, nu=5.0)
    x = pd.DataFrame(stats.norm.ppf(u), columns=["a", "b"])     # any marginals: the copula is rank-based
    R_hat = kendall_correlation(x)
    assert R_hat[0, 1] == pytest.approx(0.6, abs=0.05)
    nu = fit_t_copula(pseudo_observations(x), R_hat)
    assert 3.5 <= nu <= 7.0


def test_tail_dependence_t_vs_gaussian():
    from quantedge.risk.copula import tail_dependence

    assert tail_dependence(0.6, 4.0) > 0.25
    assert tail_dependence(0.6, 1e6) < 1e-6          # nu -> infinity is the Gaussian copula: no tail dependence


def test_semiparametric_marginal_round_trip_and_tails():
    from quantedge.risk.copula import SemiParametricMarginal

    rng = np.random.default_rng(2)
    x = rng.standard_t(4, 5000) * 0.01
    m = SemiParametricMarginal.fit(x)
    assert m.ppf(np.array([0.5]))[0] == pytest.approx(np.median(x), abs=1e-3)
    assert m.ppf(np.array([0.001]))[0] < np.quantile(x, 0.01)   # GPD extends beyond the 1% quantile
    assert np.all(np.diff(m.ppf(np.linspace(0.0005, 0.9995, 500))) >= -1e-12)


def test_copula_mc_t_has_more_joint_crashes_than_gaussian():
    from quantedge.risk.copula import CopulaMCModel

    rng = np.random.default_rng(3)
    R = np.array([[1, 0.7, 0.6], [0.7, 1, 0.6], [0.6, 0.6, 1]])
    from scipy import stats

    from quantedge.risk.copula import simulate_copula

    u = simulate_copula(R, 3000, rng, nu=4.0)
    hist = pd.DataFrame(stats.t.ppf(u, 4) * 0.01, columns=["A", "B", "C"])
    w = pd.Series({"A": 0.4, "B": 0.4, "C": 0.2})
    t = CopulaMCModel(n_sims=40_000, rng=np.random.default_rng(4)).fit(hist, w)
    g = CopulaMCModel(n_sims=40_000, rng=np.random.default_rng(4), gaussian=True).fit(hist, w)
    assert t.joint_crash_probability(["A", "B", "C"], history=hist) > g.joint_crash_probability(["A", "B", "C"], history=hist)
    assert t.es(0.99) >= t.var(0.99) > 0


@pytest.fixture(scope="module")
def overlay_inputs():
    rng = np.random.default_rng(5)
    idx = pd.bdate_range("2015-01-01", periods=1500)
    vol = np.where((np.arange(1500) > 700) & (np.arange(1500) < 800), 0.03, 0.008)   # a stress episode
    r = pd.DataFrame({"SPY": rng.normal(0, 1, 1500) * vol, "AGG": rng.normal(0, 0.003, 1500)}, index=idx)
    taus = idx[[250, 500, 750, 1000, 1250]]
    wh = pd.DataFrame({"SPY": 0.4, "AGG": 0.6}, index=taus)
    port = r["SPY"] * 0.4 + r["AGG"] * 0.6
    sigma = port.rolling(20).std().shift(0)      # stand-in forecast known at each date
    return r, wh, sigma


def test_overlay_with_infinite_target_reproduces_static(overlay_inputs):
    from quantedge.portfolio.overlay import vol_target_backtest
    from quantedge.portfolio.walkforward import simulate

    r, wh, sigma = overlay_inputs
    over = vol_target_backtest(r, wh, sigma, target_ann=np.inf)
    static, _ = simulate(r, wh, 5.0)
    pd.testing.assert_series_equal(over.perf, static)


def test_overlay_derisks_in_stress_and_respects_turnover_cap(overlay_inputs):
    from quantedge.portfolio.overlay import vol_target_backtest

    r, wh, sigma = overlay_inputs
    over = vol_target_backtest(r, wh, sigma, target_ann=0.08, turnover_cap=0.20)
    stress_weeks = over.scale.loc[r.index[720]:r.index[790]]
    assert (stress_weeks < 1).any()
    added = over.weights_history.drop(index=wh.index, errors="ignore")
    monthly = (added.diff().abs().sum(axis=1) / 2).groupby(added.index.to_period("M")).sum()
    assert (monthly <= 0.20 + 1e-9).all()


def test_rolling_corr_matches_pandas_reference():
    from quantedge.macro.analysis import rolling_stock_bond_corr

    rng = np.random.default_rng(6)
    r = pd.DataFrame(rng.normal(size=(600, 2)), columns=["SPY", "AGG"], index=pd.bdate_range("2020-01-01", periods=600))
    pd.testing.assert_series_equal(rolling_stock_bond_corr(r), r["SPY"].rolling(252).corr(r["AGG"]),
                                   check_names=False)


def test_inflation_beta_and_lkr_context():
    from quantedge.macro.analysis import inflation_beta, lkr_context, rates_impact

    rng = np.random.default_rng(7)
    days = pd.bdate_range("2010-01-01", "2022-12-30")
    months = pd.date_range("2009-01-31", "2022-12-31", freq="ME")
    mom = 0.002 + rng.normal(0, 0.002, len(months))
    cpi = pd.Series(100 * np.cumprod(1 + mom), index=months)
    surprise = pd.Series(mom, index=months) - pd.Series(mom, index=months).rolling(12).mean().shift(1)
    # daily returns whose monthly sum responds -2 x the surprise
    daily = pd.Series(rng.normal(0, 0.001, len(days)), index=days)
    for m, s in surprise.dropna().items():
        mask = (days.year == m.year) & (days.month == m.month)
        daily[mask] += -2.0 * s / mask.sum()
    out = inflation_beta(daily, cpi)
    assert out["beta"] == pytest.approx(-2.0, abs=0.4)
    fx = pd.Series(np.linspace(100, 300, len(days)), index=days)
    ctx = lkr_context(fx, pd.Series(0.0, index=days))
    assert ctx["lkr_per_usd_end"] == pytest.approx(300) and ctx["growth_lkr"] == pytest.approx(2.0, abs=1e-9)
    betas = pd.DataFrame({"d_yield10_bp": [-0.0006, 0.0]}, index=["AGG", "GLD"])
    assert rates_impact(pd.Series({"AGG": 0.5, "GLD": 0.5}), betas) == pytest.approx(-0.03)
