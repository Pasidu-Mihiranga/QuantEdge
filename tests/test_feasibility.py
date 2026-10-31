import numpy as np
import pandas as pd
import pytest

from quantedge.decision.feasibility import evaluate, frontier_feasibility, summarise
from quantedge.decision.ips import IPSLimits
from quantedge.portfolio import metrics

IDX = pd.bdate_range("2010-01-01", periods=1500)
WINDOWS = {"stress": ("2012-01-02", "2012-12-31")}


def returns() -> pd.DataFrame:
    rng = np.random.default_rng(7)
    z = rng.standard_t(5, size=(len(IDX), 3)) / np.sqrt(5 / 3)
    vols = np.array([0.18, 0.06, 0.12]) / np.sqrt(252)
    drift = np.array([0.08, 0.035, 0.05]) / 252
    return pd.DataFrame(drift + z * vols, index=IDX, columns=["A", "B", "C"])


def limits(vol=0.08, es=0.015, dd=0.20) -> IPSLimits:
    return IPSLimits(vol_ann_max=vol, stress_drawdown_max=dd, es99_1d_max=es, es99_10d_max=0.05,
                     single_asset_max=0.8, asset_floors={"B": 0.1})


def test_evaluate_matches_the_fixed_weight_portfolio():
    r, w = returns(), pd.Series({"A": 0.3, "B": 0.5, "C": 0.2})
    out = evaluate(w, r, WINDOWS)
    p = r @ w
    assert out["volatility"] == pytest.approx(metrics.volatility(p))
    assert out["cagr"] == pytest.approx(metrics.cagr(p))
    loss = -p
    assert out["es99_1d"] == pytest.approx(loss[loss >= loss.quantile(0.99)].mean())
    assert out["worst_crisis"] == "stress"


def test_frontier_points_respect_the_ips_and_flags_match_the_limits():
    lim = limits()
    tab = frontier_feasibility(returns(), 0.02, lim, 0.04, WINDOWS, market="A", n=10)
    w = tab[["A", "B", "C"]]
    assert np.allclose(w.sum(axis=1), 1) and (w <= 0.8 + 1e-6).all().all() and (w["B"] >= 0.1 - 1e-6).all()
    assert (tab["vol_ok"] == (tab["volatility"] <= lim.vol_ann_max)).all()
    assert (tab["all_ok"] == (tab["risk_ok"] & tab["return_ok"])).all()
    assert tab["expected_return"].iloc[:-1].is_monotonic_increasing      # frontier ordered by target return
    assert "Min ES (full sample)" in tab.index


def test_summary_distinguishes_feasible_conflict_and_infeasible():
    r = returns()
    loose = limits(vol=0.5, es=0.5, dd=0.9)
    feasible = summarise(frontier_feasibility(r, 0.02, loose, 0.03, WINDOWS, market="A", n=8), loose, 0.03)
    assert feasible["finding"].startswith("feasible") and feasible["points_meeting_everything"] > 0

    conflict = summarise(frontier_feasibility(r, 0.02, loose, 0.50, WINDOWS, market="A", n=8), loose, 0.50)
    assert conflict["finding"].startswith("conflict") and conflict["return_gap"] > 0

    tight = limits(vol=0.001)
    none = summarise(frontier_feasibility(r, 0.02, tight, 0.03, WINDOWS, market="A", n=8), tight, 0.03)
    assert none["finding"].startswith("infeasible") and none["closest_point_worst_ratio"] > 1
    assert none["fail_share"]["vol_ok"] == 1.0
