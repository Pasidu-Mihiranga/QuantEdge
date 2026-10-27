"""Leakage guards for the ML feature set (Step 22 M1)."""

import numpy as np
import pandas as pd
import pytest

from quantedge.ml.features import build_features, garch_sigma_path, pro_forma_returns

TICKERS = ["SPY", "EFA", "EEM", "AGG", "GLD", "XLE", "XLK"]


@pytest.fixture(scope="module")
def inputs():
    rng = np.random.default_rng(0)
    idx = pd.bdate_range("2015-01-01", periods=700)
    returns = pd.DataFrame(rng.normal(0.0003, 0.01, (700, 7)), index=idx, columns=TICKERS)
    macro = pd.DataFrame({"VIXCLS": 15 + rng.normal(0, 1, 700).cumsum() * 0.1,
                          "DGS10": 2 + rng.normal(0, 0.02, 700).cumsum(),
                          "BAA10Y": 2 + rng.normal(0, 0.01, 700).cumsum()}, index=idx)
    w = pd.DataFrame(np.tile([0.2, 0.1, 0.05, 0.4, 0.15, 0.05, 0.05], (700, 1)), index=idx, columns=TICKERS)
    w.iloc[400:] = [0.1, 0.1, 0.1, 0.4, 0.2, 0.05, 0.05]  # a rebalance
    return returns, macro, w


def test_features_unchanged_when_the_future_is_replaced_with_noise(inputs):
    returns, macro, w = inputs
    t = returns.index[500]
    base = build_features(returns, macro, w)
    rng = np.random.default_rng(99)
    r2, m2 = returns.copy(), macro.copy()
    r2.loc[r2.index > t] = rng.normal(0, 0.05, r2.loc[r2.index > t].shape)
    m2.loc[m2.index > t] = rng.normal(50, 10, m2.loc[m2.index > t].shape)
    shocked = build_features(r2, m2, w)
    pd.testing.assert_frame_equal(base.loc[:t], shocked.loc[:t])


def test_pro_forma_returns_use_todays_weights(inputs):
    returns, _, w = inputs
    pf = pro_forma_returns(returns, w)
    t = returns.index[450]
    lag3 = returns.index[447]
    assert pf.loc[t, "ret_lag3"] == pytest.approx(float(returns.loc[lag3] @ w.loc[t]))


def test_fred_values_are_lagged_one_day(inputs):
    returns, macro, w = inputs
    f = build_features(returns, macro, w)
    d = returns.index[300]
    assert f.loc[d, "vix"] == macro["VIXCLS"].iloc[299]


@pytest.mark.slow
def test_garch_sigma_path_has_no_look_ahead(inputs):
    returns, _, w = inputs
    r = returns["SPY"]
    t = r.index[620]
    base = garch_sigma_path(r, refit_every=50, min_obs=500)
    r2 = r.copy()
    r2.loc[r2.index > t] *= 5
    shocked = garch_sigma_path(r2, refit_every=50, min_obs=500)
    pd.testing.assert_series_equal(base.loc[:t], shocked.loc[:t])
    assert base.iloc[:499].isna().all() and base.iloc[499:].notna().all()
