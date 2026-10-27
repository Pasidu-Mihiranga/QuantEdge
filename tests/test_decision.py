from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from quantedge.config import load_config
from quantedge.decision.ips import IPSLimits
from quantedge.decision.rules import Evidence, evaluate
from quantedge.risk.contributions import euler_parametric, euler_simulation_es, euler_simulation_var

CFG = load_config()
LIM = IPSLimits.from_config(CFG.ips)
GOOD = Evidence(vol_oos=0.07, worst_hist_drawdown=0.15, hypothetical_loss=0.12, es99_1d=0.012,
                evt_es99=0.014, return_level_10y=0.035, champion_valid=True, any_model_valid=True,
                max_risk_to_capital=1.4, expected_return=0.068, required_return=0.067)


@pytest.fixture(scope="module")
def dcfg():
    return CFG.decision


@pytest.mark.parametrize(
    "changes, status",
    [
        ({}, "ACCEPT"),
        ({"expected_return": 0.060}, "ACCEPT"),                                   # gap 0.7% < 1%: disclosed
        ({"expected_return": 0.050}, "ADJUST RISK LIMIT"),                        # C8 gap >= 1%
        ({"vol_oos": 0.09}, "ADJUST RISK LIMIT"),                                 # loosen vol to 9%
        ({"vol_oos": 0.09, "resized_passes": True, "resized_weights": {"AGG": 0.5}}, "ADJUST RISK LIMIT"),
        ({"es99_1d": 0.020}, "ADJUST RISK LIMIT"),                                # 1.33x budget: loosen ES
        ({"es99_1d": 0.024}, "REJECT"),                                           # 1.6x budget > 50% loosening
        ({"worst_hist_drawdown": 0.35}, "REJECT"),                                # needs > 50% loosening
        ({"any_model_valid": False, "champion_valid": False}, "REJECT"),
        ({"champion_valid": False}, "ADJUST RISK LIMIT"),
        ({"max_risk_to_capital": 2.5, "resized_passes": True}, "ADJUST RISK LIMIT"),
        ({"vol_oos": 0.08}, "ACCEPT"),                                            # boundary passes
        ({"evt_es99": 0.015 * 1.25 + 1e-6, "resized_passes": True}, "ADJUST RISK LIMIT"),
    ],
)
def test_verdict_branches(changes, status, dcfg):
    v = evaluate(replace(GOOD, **changes), LIM, dcfg)
    assert v.status == status, v.reasons
    assert len(v.checks) == 9


def test_adjust_names_the_limit_and_new_value(dcfg):
    v = evaluate(replace(GOOD, vol_oos=0.091), LIM, dcfg)
    assert v.adjustments["loosen_limits_to"]["vol_ann_max"] == pytest.approx(0.091)


def test_changing_a_limit_flips_the_verdict(dcfg):
    ev = replace(GOOD, vol_oos=0.085)
    assert evaluate(ev, LIM, dcfg).status == "ADJUST RISK LIMIT"
    assert evaluate(ev, replace(LIM, vol_ann_max=0.09), dcfg).status == "ACCEPT"


def test_euler_parametric_two_asset_hand_calculation():
    sigma = pd.DataFrame([[0.04, 0.006], [0.006, 0.01]], index=["A", "B"], columns=["A", "B"])
    w = pd.Series({"A": 0.6, "B": 0.4})
    t = euler_parametric(w, sigma, 0.99, "var")
    sp = np.sqrt(w @ sigma @ w)
    z = 2.3263478740408408
    assert t["component"].sum() == pytest.approx(z * sp, abs=1e-10)
    assert t.loc["A", "component"] == pytest.approx(0.6 * z * (0.04 * 0.6 + 0.006 * 0.4) / sp)
    assert t["pct_contribution"].sum() == pytest.approx(1.0)


def test_euler_simulation_es_sums_to_total():
    rng = np.random.default_rng(0)
    R = pd.DataFrame(rng.standard_t(4, (50_000, 3)) * 0.01, columns=list("ABC"))
    w = pd.Series({"A": 0.5, "B": 0.3, "C": 0.2})
    t = euler_simulation_es(w, R)
    loss = -(R.to_numpy() @ w.to_numpy())
    total = loss[loss >= np.quantile(loss, 0.99, method="higher")].mean()
    assert t["component"].sum() == pytest.approx(total, rel=1e-12)
    v = euler_simulation_var(w, R)
    assert v["component"].sum() == pytest.approx(np.quantile(loss, 0.99), rel=0.05)


def test_sizing_flags_and_swap():
    from quantedge.decision.sizing import before_after, concentration_flags, marginal_swap

    rng = np.random.default_rng(5)
    R = pd.DataFrame(rng.normal(0, [0.02, 0.005, 0.01], (20_000, 3)), columns=["EQ", "BOND", "GOLD"])
    w = pd.Series({"EQ": 0.4, "BOND": 0.4, "GOLD": 0.2})
    contrib = euler_simulation_es(w, R)
    flags = concentration_flags(contrib, 1.5)
    assert flags.index[0] == "EQ" and bool(flags.loc["EQ", "flag"])
    mu = pd.Series({"EQ": 0.07, "BOND": 0.03, "GOLD": 0.04})
    cut, add = marginal_swap(contrib, mu)
    assert cut == "EQ" and add == "BOND"
    table = before_after(w, pd.Series({"EQ": 0.3, "BOND": 0.5, "GOLD": 0.2}), R, mu, R.cov() * 252)
    assert table.loc["es", "after"] < table.loc["es", "before"]
    assert table.loc["expected_return", "after"] < table.loc["expected_return", "before"]


def test_minimum_relaxation_chooses_the_least_amended_candidate():
    from quantedge.decision.rules import minimum_relaxation

    cands = pd.DataFrame({
        "vol_oos": [0.095, 0.085, 0.07],
        "worst_hist_drawdown": [0.22, 0.24, 0.29],
        "es99_1d": [0.016, 0.017, 0.014],
    }, index=["A", "B", "C"])
    r = minimum_relaxation(cands, LIM)
    # A: vol +18.75%, dd +10%, ES +6.7% -> max 18.75%; B: vol +6.25%, dd +20%, ES +13% -> 20%; C: dd +45%
    assert r.candidate == "A"
    assert r.required["vol_ann_max"] == pytest.approx(0.095)
    assert r.max_relative == pytest.approx(0.095 / 0.08 - 1)


def test_adjust_requires_client_approval_and_reports_the_minimum_relaxation(dcfg):
    from quantedge.decision.rules import minimum_relaxation

    cands = pd.DataFrame({"vol_oos": [0.09, 0.10], "es99_1d": [0.016, 0.014]}, index=["low", "high"])
    ev = replace(GOOD, vol_oos=0.10, relaxation=minimum_relaxation(cands, LIM))
    v = evaluate(ev, LIM, dcfg)
    assert v.status == "ADJUST RISK LIMIT"
    assert v.adjustments["client_approval_required"] is True
    assert v.adjustments["minimum_relaxation"].candidate == "low"
    assert any("investment committee" in r for r in v.reasons)


def test_reject_when_even_the_best_candidate_needs_too_much(dcfg):
    from quantedge.decision.rules import minimum_relaxation

    cands = pd.DataFrame({"es99_1d": [0.024, 0.030]}, index=["a", "b"])   # +60% at best
    v = evaluate(replace(GOOD, es99_1d=0.030, relaxation=minimum_relaxation(cands, LIM)), LIM, dcfg)
    assert v.status == "REJECT" and "least-amended candidate (a)" in v.reasons[0]


def test_memo_fills_numbers_and_leaves_team_judgement(dcfg):
    from quantedge.decision.memo import render_memo

    v = evaluate(replace(GOOD, vol_oos=0.09), LIM, dcfg)
    numbers = {"portfolio": "Test", "weights": {"AGG": 0.6, "SPY": 0.4}, "expected_return": 0.06,
               "required_return": 0.067, "var99": 0.012, "es99": 0.015, "return_level_10y": 0.03,
               "worst_hist_loss": 0.18, "worst_hist_name": "GFC 2008", "worst_drawdown_held": 0.19,
               "hypothetical_loss": 0.12,
               "champion": "Conditional EVT", "champion_reason": "lowest pinball",
               "governance": ["Re-convene if the 250-day Basel zone turns yellow."],
               "es99_10d": 0.04, "es99_10d_limit": 0.05}
    memo = render_memo(v, numbers, 10_000_000)
    assert "$120,000" in memo and "$150,000" in memo and "$6,000,000" in memo
    assert "ADJUST RISK LIMIT" in memo and "investment committee" in memo
    assert memo.count("[TEAM:") >= 5


def test_risk_to_capital_ignores_residual_weights():
    rng = np.random.default_rng(6)
    R = pd.DataFrame(rng.normal(0, [0.02, 0.005, 0.03], (20_000, 3)), columns=["EQ", "BOND", "TECH"])
    w = pd.Series({"EQ": 0.3, "BOND": 0.7 - 1e-9, "TECH": 1e-9})   # optimiser residual on TECH
    t = euler_simulation_es(w, R)
    assert np.isnan(t.loc["TECH", "risk_to_capital"])
    assert t["risk_to_capital"].max() == pytest.approx(t.loc["EQ", "risk_to_capital"])


def test_propose_resize_reports_whether_the_target_is_reachable():
    from quantedge.decision.sizing import propose_resize

    rng = np.random.default_rng(9)
    R = pd.DataFrame(rng.normal(0, [0.025, 0.004, 0.012], (30_000, 3)), columns=["EQ", "BOND", "GOLD"])
    w = pd.Series({"EQ": 0.25, "BOND": 0.55, "GOLD": 0.20})
    mu = pd.Series({"EQ": 0.07, "BOND": 0.03, "GOLD": 0.04})
    assert euler_simulation_es(w, R)["risk_to_capital"].max() > 2.0
    # Plenty of room: equity can be sold down until it no longer dominates -> achieved.
    new, log, ok = propose_resize(w, R, mu, caps={"BOND": 1.0, "GOLD": 1.0}, rc_max=2.0, step=0.05)
    assert new.sum() == pytest.approx(1.0) and log
    if ok:
        assert euler_simulation_es(new, R)["risk_to_capital"].max() <= 2.0 + 1e-9
    # Tight caps: cutting the small equity sleeve raises its ratio -> reported as not achievable.
    new2, _, ok2 = propose_resize(w, R, mu, caps={"BOND": 0.65, "GOLD": 0.20}, rc_max=2.0)
    assert not ok2
    assert new2["BOND"] <= 0.65 + 1e-12 and new2["GOLD"] <= 0.20 + 1e-12
