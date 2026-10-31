import math

import numpy as np
import pandas as pd
import pytest

from quantedge.portfolio import metrics as m
from quantedge.portfolio.capm import capm_expected_returns, capm_regression

TOY = pd.Series([0.01, -0.02, 0.015, 0.005, -0.01, 0.02, -0.005, 0.0, 0.012, -0.007],
                index=pd.bdate_range("2020-01-01", periods=10))
RF = 0.0001


def test_sharpe_matches_hand_calculation():
    e = np.array(TOY) - RF
    expected = e.mean() / e.std(ddof=1) * math.sqrt(252)
    assert m.sharpe(TOY, RF) == pytest.approx(expected, abs=1e-10)


def test_sortino_matches_hand_calculation():
    e = np.array(TOY) - RF
    dd = math.sqrt(np.mean(np.minimum(e, 0) ** 2)) * math.sqrt(252)
    assert m.sortino(TOY, RF) == pytest.approx(e.mean() * 252 / dd, abs=1e-10)


def test_max_drawdown_cagr_calmar_by_hand():
    v = np.cumprod(1 + np.array(TOY))
    peak = np.maximum.accumulate(np.r_[1.0, v])[1:]   # drawdown is measured from the initial $1
    mdd = (v / peak - 1).min()
    assert m.max_drawdown(TOY) == pytest.approx(mdd, abs=1e-12)
    cagr = v[-1] ** (252 / 10) - 1
    assert m.cagr(TOY) == pytest.approx(cagr, abs=1e-10)
    assert m.calmar(TOY) == pytest.approx(cagr / abs(mdd), abs=1e-10)


def test_omega_ulcer_information_ratio_by_hand():
    r = np.array(TOY)
    assert m.omega(TOY) == pytest.approx(r[r > 0].sum() / -r[r < 0].sum(), abs=1e-12)
    v = np.cumprod(1 + r)
    dd = v / np.maximum.accumulate(np.r_[1.0, v])[1:] - 1
    assert m.ulcer_index(TOY) == pytest.approx(math.sqrt(np.mean(dd**2)), abs=1e-12)
    bench = TOY * 0.5
    active = r - r * 0.5
    ir = active.mean() / active.std(ddof=1) * math.sqrt(252)
    assert m.information_ratio(TOY, bench) == pytest.approx(ir, abs=1e-10)


def test_max_drawdown_counts_a_first_day_loss():
    r = pd.Series([-0.10, 0.0, 0.05], index=pd.bdate_range("2020-01-01", periods=3))
    assert m.max_drawdown(r) == pytest.approx(-0.10)


def test_drawdown_info_dates():
    r = pd.Series([0.1, -0.5, 0.2, 1.0, 0.0], index=pd.bdate_range("2020-01-01", periods=5))
    info = m.max_drawdown_info(m.wealth(r))
    assert info["max_drawdown"] == pytest.approx(-0.5)
    assert info["peak"] == r.index[0] and info["trough"] == r.index[1]
    assert info["recovery"] == r.index[3]


def test_constant_returns_and_no_drawdown_edge_cases():
    flat = pd.Series([0.001] * 20, index=pd.bdate_range("2020-01-01", periods=20))
    with pytest.warns(UserWarning):
        assert math.isnan(m.sharpe(flat, 0.0))
    assert m.max_drawdown(flat) == 0.0
    assert math.isnan(m.calmar(flat))


def test_treynor_not_meaningful_for_tiny_beta():
    assert math.isnan(m.treynor(TOY, RF, beta=0.05))
    assert math.isfinite(m.treynor(TOY, RF, beta=0.8))


def test_capm_recovers_known_beta():
    rng = np.random.default_rng(42)
    idx = pd.bdate_range("2010-01-01", periods=5000)
    mkt = pd.Series(rng.normal(0.0003, 0.01, len(idx)), index=idx)
    asset = 0.7 * mkt + pd.Series(rng.normal(0, 0.005, len(idx)), index=idx)
    res = capm_regression(asset, mkt)
    assert res.beta == pytest.approx(0.7, abs=0.02)
    assert abs(res.alpha_t) < 2.5


def test_capm_on_itself_is_exact():
    mkt = TOY.copy()
    res = capm_regression(mkt, mkt)
    assert res.beta == pytest.approx(1.0, abs=1e-12)
    assert res.alpha_ann == pytest.approx(0.0, abs=1e-12)


def test_capm_expected_returns():
    mu = capm_expected_returns(pd.Series({"SPY": 1.0, "GLD": 0.0}), 0.03, 0.05)
    assert mu["SPY"] == pytest.approx(0.08) and mu["GLD"] == pytest.approx(0.03)
