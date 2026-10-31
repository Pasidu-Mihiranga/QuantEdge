"""Swarm comparison: magnitudes come from history, the loss comes from the stress engine, the page reads saved results."""

import json

import numpy as np
import pandas as pd
import pytest

from quantedge.behavioral.schema import SchemaError, parse_json_answer, validate
from quantedge.behavioral.seed import build_prompt, build_seed, ingest
from quantedge.behavioral.translate import FACTOR_MAP, compare_run, factor_shocks, h_day_changes
from quantedge.stress.factor import FACTORS, scenario_loss

ASSETS = ["SPY", "EFA", "EEM", "AGG", "GLD", "XLE", "XLK"]
ANSWER = {"factors": {k: {"direction": "+", "intensity": "high", "confidence": "medium"} for k in FACTOR_MAP},
          "behaviour": {"panic_selling": 2, "flight_to_safety": ["GLD", "cash"], "contagion_breadth": 2, "herding": 3,
                        "investor_disagreement": 1, "duration": "weeks"},
          "asset_directions": dict.fromkeys(ASSETS, "-"), "narrative_summary": "Retail sold first.",
          "key_mechanisms": ["Forced selling"], "stated_limitations": ["Agents are simulated"]}


@pytest.fixture
def macro():
    days = pd.bdate_range("2015-01-01", "2020-12-31")
    rng = np.random.default_rng(1)
    return pd.DataFrame({s: np.exp(rng.normal(0, 0.01, len(days)).cumsum()) * 50
                         for s in ("DGS10", "DCOILWTICO", "VIXCLS", "DTWEXBGS", "BAA10Y")}, index=days)


def test_schema_accepts_valid_and_rejects_invalid_answers():
    assert validate(ANSWER) is ANSWER
    with pytest.raises(SchemaError):
        validate({**ANSWER, "asset_directions": {"SPY": "-"}})
    with pytest.raises(SchemaError):
        validate({**ANSWER, "factors": {**ANSWER["factors"], "oil": None}})


def test_parse_json_answer_tolerates_code_fences():
    assert parse_json_answer("```json\n" + json.dumps(ANSWER) + "\n```")["behaviour"]["herding"] == 3


def test_magnitudes_come_from_historical_quantiles_not_the_llm(macro):
    as_of = pd.Timestamp("2020-06-30")
    ch = h_day_changes(macro, 20, as_of)
    s = factor_shocks(ANSWER, ch)
    assert s["d_vix"] == pytest.approx(max(ch["d_vix"].dropna().quantile(0.975), 0.0))
    neutral = {"factors": {k: {"direction": "0", "intensity": "extreme", "confidence": "low"} for k in FACTOR_MAP}}
    assert set(factor_shocks(neutral, ch).values()) == {0.0}
    assert macro.loc["2020-07-01":].shape[0] and h_day_changes(macro, 20, as_of).index.max() <= as_of     # no look-ahead


def test_loss_is_the_stress_engine_loss_with_the_same_panic_day(macro):
    betas = pd.DataFrame(np.full((3, len(FACTORS)), -0.0002), index=["SPY", "AGG", "XLE"], columns=FACTORS)
    w = pd.Series({"SPY": 0.3, "AGG": 0.6, "XLE": 0.1})
    r = compare_run(ANSWER, macro, betas, w, {"AGG": -0.05}, pd.Timestamp("2020-06-30"))
    assert r["loss"] == pytest.approx(scenario_loss(betas, r["shock"], w, {"AGG": -0.05}))
    assert "AGG panic day" in r["parts"] and sum(r["parts"].values()) == pytest.approx(r["loss"])
    assert r["horizon_days"] == 189 and r["summary"] == "Retail sold first."


def test_seed_uses_data_up_to_as_of_only(macro):
    days = macro.index
    rng = np.random.default_rng(2)
    returns = pd.DataFrame(rng.normal(0, 0.01, (len(days), 7)), index=days, columns=ASSETS)
    scen = {"archetypes": [{"id": "retail", "profile": "Panics."}], "scenarios": {"H1": {"as_of": "2019-12-31", "trigger": "Oil spike."}}}
    a = build_seed("H1", scen, returns, macro)
    b = build_seed("H1", scen, returns.assign(SPY=returns["SPY"].where(days <= "2019-12-31", 0.5)), macro)
    assert a == b and "Oil spike." in a and "retail" in a
    assert "Do not invent" in build_prompt()


def test_ingest_requires_a_complete_valid_run(tmp_path):
    with pytest.raises(FileNotFoundError):
        ingest(tmp_path)
    for f in ("seed.md", "prompt.txt", "run_config.json", "raw_report.md"):
        (tmp_path / f).write_text("x", encoding="utf-8")
    (tmp_path / "report_agent_answers.json").write_text(json.dumps(ANSWER), encoding="utf-8")
    assert ingest(tmp_path)["behaviour"]["duration"] == "weeks"


def test_page_is_hidden_until_a_real_run_exists_and_renders_saved_results(tmp_path, monkeypatch):
    from pathlib import Path

    from streamlit.testing.v1 import AppTest

    from quantedge import paths

    home = Path(paths.ROOT / "app" / "Home.py").read_text(encoding="utf-8")
    assert 'swarm_comparison.json").exists()' in home                      # no empty page for judges
    part = {"SPY": 0.05, "AGG": 0.10, "AGG panic day": 0.03}
    shock = {"d_yield10_bp": 200.0, "dln_oil": 0.3, "d_vix": 20.0, "dln_usd": 0.05, "d_credit_bp": 100.0}
    run = {"run": "run_1", "shock": shock, "loss": 0.18, "parts": part, "horizon_days": 60, "behaviour": ANSWER["behaviour"],
           "summary": "Retail sold first.", "mechanisms": ["Forced selling"], "limitations": []}
    data = {"scenario": "Hormuz stagflation 2027", "team": {"shock": shock, "loss": 0.21, "parts": part}, "runs": [run, {**run, "run": "run_2"}],
            "mean_loss": 0.18, "min_loss": 0.17, "max_loss": 0.19}
    (tmp_path / "swarm_comparison.json").write_text(json.dumps(data), encoding="utf-8")
    src = (paths.ROOT / "app" / "side" / "swarm.py").read_text(encoding="utf-8").replace(
        'ARTIFACTS / "swarm_comparison.json"', f'__import__("pathlib").Path(r"{tmp_path}") / "swarm_comparison.json"')
    page = paths.ROOT / "app" / "_swarm_test_page.py"
    page.write_text(src, encoding="utf-8")
    try:
        at = AppTest.from_file(str(page), default_timeout=30).run()
        assert not at.exception
        assert any("crowd simulation" in t.value.lower() for t in at.title)
        assert len(at.metric) == 3
    finally:
        page.unlink()


def test_the_saved_scenario_has_a_complete_trigger():
    from quantedge.behavioral.seed import load_scenarios

    scen = load_scenarios()
    assert len(scen["scenarios"]["H1"]["trigger"]) > 40 and len(scen["archetypes"]) == 5
