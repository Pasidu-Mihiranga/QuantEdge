"""D1/D2/D4 evidence (decision.objective): hand calculations, and the pipeline reproducing notebooks 03 §4 and 06 A2."""

import json

import numpy as np
import pandas as pd
import pytest

from quantedge.decision.objective import (
    calibrate_limits,
    crisis_loss,
    forward_asset_returns,
    forward_portfolio_return,
    path_loss,
    through_the_cycle,
)
from quantedge.paths import ARTIFACTS

FWD = {"erp": 0.045, "agg_spread": 0.005, "trading_cost": 0.0001,
       "expense_ratios": {"SPY": 0.001, "AGG": 0.0003, "GLD": 0.004}, "withholding": {"SPY": 0.15}}


def test_forward_returns_by_hand():
    beta = pd.Series({"SPY": 1.0, "AGG": 0.1, "GLD": 0.2})
    dy = pd.Series({"SPY": 0.02, "AGG": 0.03, "GLD": 0.0})
    net = forward_asset_returns(0.04, 0.025, beta, dy, FWD)
    assert net["SPY"] == pytest.approx(0.04 + 0.045 - 0.001 - 0.02 * 0.15 - 0.0001)
    assert net["AGG"] == pytest.approx(0.04 + 0.005 - 0.0003 - 0.0001)      # no withholding on AGG
    assert net["GLD"] == pytest.approx(0.025 - 0.004 - 0.0001)               # gold earns breakeven inflation
    cov = pd.DataFrame(np.diag([0.04, 0.0036, 0.0225]), index=net.index, columns=net.index)
    w = pd.Series({"SPY": 0.4, "AGG": 0.6, "GLD": 0.0})
    drag = 0.5 * (0.16 * 0.04 + 0.36 * 0.0036)
    assert forward_portfolio_return(w, net, cov) == pytest.approx(0.4 * net["SPY"] + 0.6 * net["AGG"] - drag)


def test_path_and_crisis_loss_by_hand():
    assert path_loss(pd.Series([0.10, -0.50, 0.20])) == pytest.approx(0.5)     # peak 1.10 -> 0.55
    assert path_loss(pd.Series([-0.10, 0.05])) == pytest.approx(0.10)          # a fall from the start counts
    idx = pd.bdate_range("2020-01-01", periods=6)
    r = pd.DataFrame({"A": [0.0, -0.1, -0.1, 0.0, 0.0, 0.0], "B": 0.0}, index=idx)
    out = crisis_loss(pd.Series({"A": 0.5, "B": 0.5}), r, {"x": (str(idx[0].date()), str(idx[3].date()))})
    assert out["x"] == pytest.approx(1 - 0.95 * 0.95)                           # constant mix: -5% a day


def test_through_the_cycle_uses_acerbi_tasche_es():
    r = pd.DataFrame({"A": -np.arange(1, 201) / 1000})                           # losses 0.001 ... 0.200
    out = through_the_cycle(pd.Series({"A": 1.0}), r)
    assert out["es99_1d"] == pytest.approx((0.200 + 0.199) / 2)                  # worst 1% of 200 = 2 days


def test_calibration_interpolates_the_budget_along_the_frontier():
    idx = pd.bdate_range("2007-01-01", periods=400)
    rng = np.random.default_rng(0)
    r = pd.DataFrame({"EQ": rng.normal(0, 0.012, 400), "BD": rng.normal(0, 0.002, 400)}, index=idx)
    r.iloc[200:260, 0] = -0.01                                                   # a crisis in equities
    frontier = {x: pd.Series({"EQ": x, "BD": 1 - x}) for x in (0.2, 0.4)}
    table, d = calibrate_limits(frontier, r.iloc[:300], r, {"c": (str(idx[199].date()), str(idx[259].date()))}, 0.0)
    lo, hi = table["worst_crisis_loss"]
    budget = (lo + hi) / 2
    _, d = calibrate_limits(frontier, r.iloc[:300], r, {"c": (str(idx[199].date()), str(idx[259].date()))}, budget)
    assert d["equity_share"] == pytest.approx(0.3, abs=0.01)
    assert d["vol_ann_max"] == pytest.approx(table["vol_ann"].mean(), rel=1e-9)


needs_artifacts = pytest.mark.skipif(not (ARTIFACTS / "limit_calibration.parquet").exists(),
                                     reason="run the pipeline first")


@needs_artifacts
def test_pipeline_reproduces_notebook_03_limit_calibration():
    d = json.loads((ARTIFACTS / "limit_calibration.json").read_text(encoding="utf-8"))
    assert d["equity_share"] == pytest.approx(0.36, abs=0.005)
    assert d["vol_ann_max"] == pytest.approx(0.0840, abs=0.00005)                # notebook 03 §4: 8.40%
    assert d["es99_1d_max"] == pytest.approx(0.0223, abs=0.00005)                # notebook 03 §4: 2.23%
    assert d["config_vol_ann_max"] == pytest.approx(d["vol_ann_max"], abs=0.0005)
    assert d["config_es99_1d_max"] == pytest.approx(d["es99_1d_max"], abs=0.0005)


@needs_artifacts
def test_pipeline_reproduces_notebook_06_forward_returns_and_required_return():
    nb06 = {0.20: (0.0432, 0.1817), 0.25: (0.0454, 0.2024), 0.30: (0.0475, 0.2236), 0.35: (0.0491, 0.2441),
            0.40: (0.0499, 0.2659), 0.45: (0.0504, 0.2900), 0.50: (0.0507, 0.3188)}
    cal = pd.read_parquet(ARTIFACTS / "limit_calibration.parquet")
    for x, (fwd, loss) in nb06.items():
        assert cal.loc[x, "forward_return"] == pytest.approx(fwd, abs=0.00006)
        assert cal.loc[x, "worst_crisis_loss"] == pytest.approx(loss, abs=0.00006)
    req = json.loads((ARTIFACTS / "required_return.json").read_text(encoding="utf-8"))
    assert req["required_return"] == pytest.approx(0.0590, abs=0.00005)          # notebook 06 A2: 5.90%
