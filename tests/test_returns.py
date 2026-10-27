import numpy as np
import pandas as pd
import pytest

from quantedge.portfolio.returns import (
    CASH,
    add_cash_asset,
    horizon_returns,
    log_returns,
    performance_series,
    rebalance_flags,
    risk_free_daily,
    risk_series,
    simple_returns,
)


@pytest.fixture
def two_assets():
    rng = np.random.default_rng(0)
    idx = pd.bdate_range("2020-01-01", periods=400)
    r = pd.DataFrame(rng.normal(0.0004, 0.01, (400, 2)), index=idx, columns=["A", "B"])
    return r


def test_fifty_fifty_aggregation_is_exact_and_log_average_is_not(two_assets):
    rp = risk_series(two_assets, {"A": 0.5, "B": 0.5})
    np.testing.assert_allclose(rp, two_assets.mean(axis=1))
    log_avg = np.log1p(two_assets).mean(axis=1)
    assert not np.allclose(log_avg, np.log1p(rp))  # documents the trap


def test_simple_and_log_returns_drop_first_row():
    p = pd.DataFrame({"A": [100.0, 110.0, 99.0]}, index=pd.bdate_range("2020-01-01", periods=3))
    np.testing.assert_allclose(simple_returns(p)["A"], [0.10, -0.10])
    np.testing.assert_allclose(log_returns(p)["A"], np.log([1.1, 0.9]))


def test_no_rebalance_zero_cost_equals_buy_and_hold(two_assets):
    w = {"A": 0.3, "B": 0.7}
    perf = performance_series(two_assets, w, rebalance=None, cost_bps=0)
    growth = (1 + two_assets).cumprod()
    bh = (growth * pd.Series(w)).sum(axis=1)
    np.testing.assert_allclose(perf.values, bh)


def test_daily_rebalance_zero_cost_equals_risk_series(two_assets):
    w = {"A": 0.3, "B": 0.7}
    perf = performance_series(two_assets, w, rebalance="D", cost_bps=0)
    np.testing.assert_allclose(perf.returns, risk_series(two_assets, w))


def test_costs_reduce_value_and_happen_only_on_quarter_ends(two_assets):
    w = {"A": 0.5, "B": 0.5}
    free = performance_series(two_assets, w, rebalance="Q", cost_bps=0)
    paid = performance_series(two_assets, w, rebalance="Q", cost_bps=5)
    assert paid.values.iloc[-1] < free.values.iloc[-1]
    flags = rebalance_flags(two_assets.index, "Q")
    assert (paid.costs[~flags] == 0).all()
    quarter_ends = two_assets.index[flags]
    assert all(d.month in (3, 6, 9, 12) for d in quarter_ends[:-1])
    np.testing.assert_allclose(paid.weights_path.loc[quarter_ends[0]], [0.5, 0.5])


def test_rf_daily_compounds_to_bey_and_is_lagged():
    idx = pd.bdate_range("2020-01-01", periods=300)
    dtb3 = pd.Series(4.0, index=idx)
    rf = risk_free_daily(dtb3, idx)
    d = 0.04
    bey = 365 * d / (360 - 91 * d)
    assert (1 + rf.iloc[10]) ** 252 - 1 == pytest.approx(bey, abs=1e-4)
    step = pd.Series(np.where(idx >= idx[100], 5.0, 1.0), index=idx)
    rf_step = risk_free_daily(step, idx)
    assert rf_step.loc[idx[100]] < rf_step.loc[idx[101]]  # day-100 rate used from day 101


def test_cash_asset_has_zero_variance(two_assets):
    rf = pd.Series(0.0001, index=two_assets.index)
    with_cash = add_cash_asset(two_assets, rf)
    assert with_cash[CASH].var() == pytest.approx(0.0)
    np.testing.assert_allclose(with_cash.cov()[CASH], 0.0, atol=1e-20)


def test_weights_validation(two_assets):
    with pytest.raises(ValueError, match="sum to 1"):
        risk_series(two_assets, {"A": 0.5, "B": 0.6})
    with pytest.raises(ValueError, match="not in the returns"):
        risk_series(two_assets, {"A": 0.5, "Z": 0.5})


def test_horizon_returns_compound(two_assets):
    r = two_assets["A"]
    h10 = horizon_returns(r, 10)
    expected = (1 + r.iloc[:10]).prod() - 1
    assert h10.iloc[0] == pytest.approx(expected)
    assert len(horizon_returns(r, 10, overlapping=False)) == len(h10[::10])
