"""Step 20 MVS scorecard and adoption rule."""

import numpy as np
import pandas as pd
import pytest
import yaml

from quantedge.behavioral import scorecard as sc
from quantedge.behavioral.seed import SCENARIOS_FILE

W = yaml.safe_load(SCENARIOS_FILE.read_text(encoding="utf-8"))["scorecard"]["mvs"]
COLS = ["SPY", "EFA", "EEM", "AGG", "GLD", "XLE", "XLK"]
CODING = {"behaviour": {"panic_selling": 2, "flight_to_safety": ["GLD"], "contagion_breadth": 2, "herding": 1,
                        "investor_disagreement": 1, "duration": "weeks"}}


def ctx(**human):
    cov = pd.DataFrame(np.diag(np.full(7, 2e-4)), index=COLS, columns=COLS)
    crises = pd.DataFrame([[-0.5, -0.55, -0.55, 0.07, 0.25, -0.45, -0.5], [-0.3, -0.3, -0.3, -0.01, -0.03, -0.5, -0.3]],
                          columns=COLS, index=["GFC", "COVID"])
    return sc.Context(cov, crises, ["min_cvar", "gmv", "erc"], 0.18, 0.03, W, human)


def result(kind="forward", shock=None, realised=None):
    s = pd.Series(shock or [-0.08, -0.09, -0.11, -0.03, 0.03, 0.02, -0.07], index=COLS)
    return sc.ScenarioResult("X", kind, 20, s, pd.Series({"d_yield10_bp": 60.0, "dln_oil": 0.2}), CODING, 0.8,
                             pd.Series({"min_cvar": 0.03, "gmv": 0.035, "erc": 0.06}), 0.03,
                             realised=realised, realised_focus_loss=0.025 if realised is not None else None)


def test_points_add_up_and_missing_human_inputs_are_flagged():
    compliance = {"compliant_toolkit": True, "approved_data_only": True, "runtime_within_budget": True,
                  "full_provenance": True, "ai_disclosure": True}
    real = pd.Series([-0.07, -0.08, -0.12, -0.02, 0.02, 0.01, -0.06], index=COLS)
    out = sc.dimension_scores([result(), result("replay", realised=real)], ctx(), compliance, replicate_cv=None)
    assert out["D6"] == 15
    assert 0 <= out["total"] <= 100
    assert out["total"] == pytest.approx(sum(out[d] for d in ("D1", "D2", "D3", "D4", "D5", "D6")))
    assert any("reviewer" in f for f in out["flags"]) and any("kappa" in f for f in out["flags"])
    assert out["D1"] > 15        # replay directions all correct, ranks highly correlated
    full = sc.dimension_scores([result(), result("replay", realised=real)], ctx(reviewer_rating=1.0, kappa=0.9,
                               cache_rebuild=1), compliance, replicate_cv=0.0)
    assert full["D5"] == pytest.approx(15) and full["total"] > out["total"]


def test_component_rules():
    assert sc.chi2_credit(1.0, 7, 99.9, 99.999) == 1.0
    assert sc.chi2_credit(200.0, 7, 99.9, 99.999) == 0.0
    assert sc.novelty_credit(3, (2, 4)) == 1.0 and sc.novelty_credit(1, (2, 4)) == 0.5 and sc.novelty_credit(8, (2, 4)) == 0.0
    shock = pd.Series([-0.08, -0.09, -0.11, -0.036, 0.03, 0.02, -0.07], index=COLS)
    assert sc.economic_rules(shock, CODING, pd.Series({"d_yield10_bp": 60.0, "dln_oil": 0.2}), 0.8) == 1.0


def test_naive_variant_scales_with_horizon():
    crises = pd.DataFrame([[-0.5] * 7, [-0.3] * 7], columns=COLS)
    n = sc.naive_shock(crises, pd.Series([350.0, 25.0]), h=20)
    assert n["SPY"] == pytest.approx(np.mean([-0.5 * np.sqrt(20 / 350), -0.3 * np.sqrt(20 / 25)]))


def test_adoption_rule_outcomes():
    rng = np.random.default_rng(0)
    ok = {"compliant_toolkit": True, "approved_data_only": True}
    assert sc.adoption(60, [70, 71, 69, 72, 70], 60, 65, 40, ok, rng)["outcome"] == "ADOPTED"
    assert sc.adoption(60, [62, 63, 61, 62, 62], 60, 65, 40, ok, rng)["outcome"] == "HYBRID"
    assert sc.adoption(60, [50, 51, 52, 49, 50], 60, 65, 40, ok, rng)["outcome"] == "APPENDIX"
    assert sc.adoption(60, [70, 71, 69, 72, 70], 60, 55, 40, ok, rng)["outcome"] == "HYBRID"   # BRS_B < BRS_A
    assert sc.adoption(60, [90] * 5, 60, 90, 40, {"compliant_toolkit": False}, rng)["outcome"] == "REJECTED"
