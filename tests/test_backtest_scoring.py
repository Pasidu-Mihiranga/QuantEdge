import math

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from quantedge.backtest import coverage as cv
from quantedge.backtest import scoring as sc


def test_kupiec_textbook_example():
    lr = cv.kupiec_lr(6, 250, 0.01)
    assert lr == pytest.approx(3.55, abs=0.01)
    assert stats.chi2.sf(lr, 1) == pytest.approx(0.06, abs=0.005)


def test_kupiec_handles_zero_exceptions():
    res = cv.kupiec(np.zeros(250, dtype=int), 0.99)
    assert res.x == 0 and math.isfinite(res.lr)
    assert res.lr == pytest.approx(-2 * 250 * math.log(0.99))


def test_christoffersen_detects_clustering():
    spread = np.zeros(500, dtype=int)
    spread[::50] = 1
    clustered = np.zeros(500, dtype=int)
    clustered[200:210] = 1
    assert cv.christoffersen(spread, 0.98).p_ind > 0.05
    assert cv.christoffersen(clustered, 0.98).p_ind < 0.01
    no_exceptions = cv.christoffersen(np.zeros(100, dtype=int), 0.99)
    assert math.isnan(no_exceptions.lr_ind)


@pytest.mark.slow
def test_kupiec_size_is_about_five_percent():
    rng = np.random.default_rng(0)
    rejections = [cv.kupiec(rng.random(1000) < 0.05, 0.95).pvalue < 0.05 for _ in range(500)]
    assert 0.02 <= np.mean(rejections) <= 0.09


def test_basel_binomial_cutoffs_reproduce_canonical_table():
    assert cv.basel_cutoffs(250, 0.99) == (4, 10)
    assert [cv.basel_zone(x, 250) for x in (4, 5, 9, 10)] == ["green", "yellow", "yellow", "red"]
    g, r = cv.basel_cutoffs(1000, 0.99)
    assert g > 4 and r > 10      # never apply 4/9 to a 1,000-day count
    assert cv.basel_plus_factor(7) == 0.65 and cv.basel_plus_factor(12) == 1.0


def test_rolling_basel_windows():
    hits = pd.Series(np.zeros(600, dtype=int), index=pd.bdate_range("2020-01-01", periods=600))
    hits.iloc[300:312] = 1
    roll = cv.rolling_basel(hits)
    assert len(roll) == 351
    shares = cv.zone_shares(roll)
    assert shares["red"] > 0 and abs(sum(shares.values()) - 1) < 1e-12


def test_clopper_pearson():
    lo, hi = cv.clopper_pearson(0, 1000)
    assert lo == 0.0 and hi == pytest.approx(1 - 0.025 ** (1 / 1000), rel=1e-6)
    lo, hi = cv.clopper_pearson(10, 1000)
    assert lo < 0.01 < hi


def test_kupiec_power():
    size = cv.power_kupiec(1000, 0.01, 0.01)
    assert 0.02 <= size <= 0.08
    power_doubled = cv.power_kupiec(1000, 0.01, 0.02)
    assert 0.7 <= power_doubled <= 0.9
    assert cv.power_kupiec(250, 0.01, 0.02) < power_doubled


def test_pinball_and_fz0_by_hand():
    losses = np.array([0.01, 0.03, -0.005, 0.02, 0.0])
    var = np.full(5, 0.02)
    es = np.full(5, 0.025)
    a = 0.99
    expected_pin = [(a - 1) * (0.01 - 0.02), a * (0.03 - 0.02), (a - 1) * (-0.025), 0.0, (a - 1) * (-0.02)]
    np.testing.assert_allclose(sc.pinball(losses, var, a), expected_pin)
    p = 0.01
    v, e = -0.02, -0.025
    y = -losses
    hit = (y <= v).astype(float)
    expected_fz = -(1 / (p * e)) * hit * (v - y) + v / e + np.log(-e) - 1
    np.testing.assert_allclose(sc.fz0(losses, var, es, a), expected_fz)


def test_fz0_prefers_the_true_var_es():
    rng = np.random.default_rng(1)
    losses = rng.standard_normal(200_000)
    a = 0.99
    true_v = stats.norm.ppf(a)
    true_e = stats.norm.pdf(true_v) / (1 - a)
    good = sc.fz0(losses, true_v, true_e, a).mean()
    for v, e in [(true_v * 0.8, true_e * 0.8), (true_v * 1.2, true_e * 1.2), (true_v, true_e * 0.7)]:
        assert sc.fz0(losses, v, e, a).mean() > good


def test_dm_identical_forecasts_and_clear_winner():
    x = np.random.default_rng(2).random(500)
    same = sc.dm_test(x, x)
    assert same.stat == 0.0 and same.pvalue == 1.0
    better = sc.dm_test(x, x + 0.1 + 0.01 * np.random.default_rng(3).standard_normal(500))
    assert better.stat < 0 and better.pvalue < 0.01


def test_holm_adjustment():
    adj = sc.holm({"a": 0.01, "b": 0.04, "c": 0.03})
    assert adj["a"] == pytest.approx(0.03)
    assert adj["c"] == pytest.approx(0.06)
    assert adj["b"] == pytest.approx(0.06)


def test_model_confidence_set_drops_a_clearly_worse_model():
    rng = np.random.default_rng(4)
    base = rng.random(800)
    losses = pd.DataFrame({"good": base, "also_good": base + 0.001 * rng.standard_normal(800),
                           "bad": base + 0.5})
    out = sc.model_confidence_set(losses, reps=300, seed=1)
    assert bool(out.loc["good", "in_mcs"]) and not bool(out.loc["bad", "in_mcs"])


def test_score_table():
    idx = pd.bdate_range("2020-01-01", periods=5)
    losses = pd.Series([0.01, 0.03, -0.005, 0.02, 0.0], index=idx)
    f = pd.DataFrame({"var": 0.02, "es": 0.025}, index=idx)
    t = sc.score_table(losses, {"m": f})
    assert t.loc["m", "n"] == 5
    assert t.loc["m", "pinball"] == pytest.approx(sc.pinball(losses, f["var"], 0.99).mean())


def test_model_confidence_set_handles_duplicate_columns():
    rng = np.random.default_rng(7)
    base = rng.random(600)
    losses = pd.DataFrame({"a": base, "a_copy": base, "worse": base + 0.5})
    out = sc.model_confidence_set(losses, reps=200, seed=1)
    assert out.loc["a", "mcs_pvalue"] == out.loc["a_copy", "mcs_pvalue"]
    assert bool(out.loc["a_copy", "in_mcs"]) and not bool(out.loc["worse", "in_mcs"])
