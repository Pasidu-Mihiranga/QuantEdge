"""Decision-date numbers: hand checks of the building blocks, and the production module against notebook 06 Part B."""

import json

import numpy as np
import pandas as pd
import pytest

from quantedge.decision.decision_date import es_shares, resize_d8
from quantedge.paths import ARTIFACTS, ROOT
from quantedge.stress.factor import FACTORS, regime_stress_weeks, scenario_loss


def test_scenario_loss_maps_log_betas_and_adds_the_liquidity_day():
    betas = pd.DataFrame([[0.0, 0.1, 0.0, 0.0, 0.0], [-0.0005, 0.0, 0.0, 0.0, 0.0]], index=["XLE", "AGG"], columns=FACTORS)
    shock = {"d_yield10_bp": 200, "dln_oil": 0.3}
    w = pd.Series({"XLE": 0.2, "AGG": 0.8})
    port_log = 0.2 * 0.1 * 0.3 + 0.8 * (-0.0005 * 200)
    assert scenario_loss(betas, shock, w) == pytest.approx(-np.expm1(port_log))
    assert scenario_loss(betas, shock, w, {"AGG": -0.05}) == pytest.approx(-np.expm1(port_log) + 0.8 * 0.05)


def test_regime_stress_weeks_flags_hiking_cycles_and_crisis_quarters():
    days = pd.bdate_range("2005-01-03", "2009-12-31")
    tb = pd.Series(np.where(days < pd.Timestamp("2006-01-01"), 1.0, 3.0), index=days)   # bills up 2 pp during 2006
    weeks = regime_stress_weeks(days, tb)
    assert weeks.loc["2006-06-01":"2006-12-01"].all()          # within 252 days of the rise: a hiking cycle
    assert not weeks.loc["2005-03-01":"2005-12-01"].any()      # before it: normal
    assert weeks.loc["2008-10-10":"2008-12-26"].all()          # 2008 Q4 liquidity crisis
    assert not weeks.loc["2009-03-01":"2009-09-01"].any()


def test_es_shares_sum_to_one_and_d8_moves_weight_to_spy():
    rng = np.random.default_rng(3)
    r = pd.DataFrame(rng.normal(0, [0.010, 0.025, 0.003], (20_000, 3)), columns=["SPY", "EFA", "AGG"])
    w = pd.Series({"SPY": 0.10, "EFA": 0.25, "AGG": 0.65})
    sh = es_shares(w, r)
    assert sh.sum() == pytest.approx(1.0)
    assert sh.idxmax() == "EFA" and sh.max() > 0.40
    w2, moved = resize_d8(w, r, cap=0.40, spy_cap=0.40)
    assert es_shares(w2, r).max() <= 0.40 + 1e-9 and moved > 0
    assert w2.sum() == pytest.approx(1.0) and w2["AGG"] == pytest.approx(0.65)


NUMBERS = ARTIFACTS / "decision_numbers.json"
pytestmark_artifacts = pytest.mark.skipif(not NUMBERS.exists(), reason="run the decision-date stage first")


def _notebook() -> dict | None:
    n = json.loads(NUMBERS.read_text(encoding="utf-8"))
    f = ROOT / "notebooks" / "evidence" / f"06_partB_{n['data_end']}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


@pytestmark_artifacts
def test_production_decision_reproduces_notebook_06_part_b():
    n = json.loads(NUMBERS.read_text(encoding="utf-8"))
    nb = _notebook()
    if nb is None:
        pytest.skip("notebook 06 Part B has not been run on the same data")
    assert n["verdict"].split()[0] == nb["verdict"].split()[0]
    assert n["advised_equity"] == pytest.approx(nb["advised"])
    assert n["objective"]["required_return"] == pytest.approx(nb["required_return"], abs=1e-9)
    assert n["limits"]["vol_max"] == pytest.approx(nb["limits"]["volatility limit"], abs=1e-6)
    assert n["limits"]["es99_max"] == pytest.approx(nb["limits"]["99% ES limit"], abs=1e-6)
    fr = pd.read_parquet(ARTIFACTS / "decision_frontier.parquet")
    pairs = {"forward_return": "forward return", "vol_ttc": "vol (through the cycle)", "es99_ttc": "99% ES (through the cycle)",
             "worst_crisis_loss": "worst historical crisis", "hypothetical_loss": "hypothetical + liquidity day"}
    for label, row in nb["frontier"].items():
        x = float(label.strip("%")) / 100
        for ours, theirs in pairs.items():
            assert fr.loc[x, ours] == pytest.approx(row[theirs], abs=1e-4), (label, ours)
    for t, v in nb["weights"].items():
        assert n["weights"][t] == pytest.approx(v, abs=1e-4)
    assert n["erp_breakeven"] == pytest.approx(nb["erp_breakeven"], abs=1e-9)
    assert n["robustness"] == nb["robustness"]
    assert abs(n["ten_year"]["p_objective"] - nb["ten_year_35"]) < 0.03     # two Monte Carlo runs, s.e. about 0.7 pp each
