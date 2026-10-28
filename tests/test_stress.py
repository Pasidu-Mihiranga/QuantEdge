import numpy as np
import pandas as pd
import pytest

from quantedge.stress.factor import FACTORS, estimate_factor_betas
from quantedge.stress.historical import replay, stress_matrix
from quantedge.stress.hypothetical import apply_shock, duration_check
from quantedge.stress.reverse import most_likely_breach, parametric_var_es, stressed_sigma


@pytest.fixture(scope="module")
def market():
    rng = np.random.default_rng(0)
    idx = pd.bdate_range("2019-01-01", periods=600)
    r = pd.DataFrame(rng.normal(0.0002, 0.01, (600, 3)), index=idx, columns=["A", "B", "C"])
    return r


def test_replay_contributions_sum_to_total(market):
    w = pd.Series({"A": 0.5, "B": 0.3, "C": 0.2})
    res = replay(market, w, "2019-06-03", "2019-12-31", 1e7)
    assert res.contributions.sum() == pytest.approx(res.total_return, abs=1e-10)
    assert res.loss_usd == pytest.approx(-res.total_return * 1e7)


def test_single_asset_replay_equals_its_own_return(market):
    w = pd.Series({"A": 1.0, "B": 0.0, "C": 0.0})
    res = replay(market, w, "2019-06-03", "2019-12-31", 1e7)
    expected = (1 + market.loc["2019-06-04":"2019-12-31", "A"]).prod() - 1   # starts after the peak close
    assert res.total_return == pytest.approx(expected, abs=1e-12)


def test_replay_excludes_the_return_dated_on_the_window_start():
    idx = pd.bdate_range("2020-01-01", periods=4)
    r = pd.DataFrame({"A": [-0.50, -0.10, 0.0, 0.0]}, index=idx)   # the -50% day is before the peak close
    res = replay(r, pd.Series({"A": 1.0}), idx[0], idx[2], 1.0)
    assert res.total_return == pytest.approx(-0.10)


def test_recovery_days():
    idx = pd.bdate_range("2020-01-01", periods=10)
    r = pd.DataFrame({"A": [0.0, -0.10, 0.0, 0.05, 0.05, 0.02, 0.0, 0.0, 0.0, 0.0]}, index=idx)
    res = replay(r, pd.Series({"A": 1.0}), idx[0], idx[2], 1.0)
    # after the window: 0.9 * 1.05 * 1.05 * 1.02 = 1.012 -> back above 1.0 three days later
    assert res.days_to_recover == 3
    assert res.max_drawdown == pytest.approx(0.10)
    matrix = stress_matrix({"p": pd.Series({"A": 1.0})}, r, {"w": (str(idx[0].date()), str(idx[2].date()))}, 1.0)
    assert matrix.loc["p", "w"] == pytest.approx(-0.10)


def test_factor_betas_recovered_within_standard_errors():
    rng = np.random.default_rng(1)
    idx = pd.date_range("2006-01-06", periods=800, freq="W-FRI")
    f = pd.DataFrame(rng.normal(0, 1, (800, 5)), index=idx, columns=FACTORS)
    true = np.array([-0.002, 0.03, -0.004, -0.05, -0.001])
    etf = pd.DataFrame({"X": f.to_numpy() @ true + rng.normal(0, 0.005, 800)}, index=idx)
    res = estimate_factor_betas(etf, f)
    se = np.sqrt(np.diag(res.cov["X"]))
    assert np.all(np.abs(res.betas.loc["X"].to_numpy() - true) < 3 * se)


def test_apply_shock_is_linear_in_betas():
    rng = np.random.default_rng(2)
    idx = pd.date_range("2006-01-06", periods=500, freq="W-FRI")
    f = pd.DataFrame(rng.normal(0, 1, (500, 5)), index=idx, columns=FACTORS)
    etf = pd.DataFrame({"X": f["d_yield10_bp"] * -0.001 + rng.normal(0, 0.002, 500),
                        "Y": f["dln_oil"] * 0.5 + rng.normal(0, 0.002, 500)}, index=idx)
    b = estimate_factor_betas(etf, f)
    shock = {"d_yield10_bp": 150, "dln_oil": np.log(1.4)}
    res = apply_shock(b, shock, pd.Series({"X": 0.5, "Y": 0.5}), 1e7, etf, f)
    manual = b.betas[FACTORS] @ pd.Series(shock).reindex(FACTORS).fillna(0)
    np.testing.assert_allclose(res.asset_returns, manual)
    assert res.portfolio_return == pytest.approx(0.5 * manual.sum())
    assert res.portfolio_se > 0
    assert duration_check(150) == pytest.approx(-0.09)


def test_reverse_stress_hits_the_loss_and_minimises_mahalanobis(market):
    sigma = market.cov()
    w = pd.Series({"A": 0.5, "B": 0.3, "C": 0.2})
    rs = most_likely_breach(sigma, w, 0.20, horizon_days=21)
    assert float(w @ rs.x_star) == pytest.approx(-0.20, abs=1e-12)
    S_inv = np.linalg.inv(sigma.to_numpy() * 21)
    best = rs.x_star.to_numpy() @ S_inv @ rs.x_star.to_numpy()
    assert best == pytest.approx(rs.d2)
    rng = np.random.default_rng(3)
    for _ in range(200):
        x = rng.normal(0, 0.1, 3)
        x = x - w.to_numpy() * ((w.to_numpy() @ x + 0.20) / (w.to_numpy() @ w.to_numpy()))  # project onto w'x = -L*
        assert x @ S_inv @ x >= best - 1e-9


def test_stressed_sigma_and_parametric_var(market):
    calm = market.cov()
    stressed = stressed_sigma(market * 3, {"x": ("2019-03-01", "2019-06-28")})
    w = pd.Series({"A": 1 / 3, "B": 1 / 3, "C": 1 / 3})
    v_calm, e_calm = parametric_var_es(calm, w)
    v_st, e_st = parametric_var_es(stressed, w)
    assert v_st > v_calm and e_st > e_calm > v_calm
