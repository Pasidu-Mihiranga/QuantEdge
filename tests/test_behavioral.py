"""Behavioural Stress Lab (Step 19): schema, translation layer and replay validation."""

import json

import numpy as np
import pandas as pd
import pytest

from quantedge.behavioral import schema
from quantedge.behavioral import translate as tr


def answer(**over):
    a = {
        "factors": {f: {"direction": "+", "intensity": "high", "confidence": "medium"} for f in schema.FACTORS},
        "behaviour": {"panic_selling": 2, "flight_to_safety": ["GLD", "cash"], "contagion_breadth": 3,
                      "herding": 1, "investor_disagreement": 1, "duration": "weeks"},
        "asset_directions": {a: "-" for a in schema.ASSETS},
        "narrative_summary": "Rates jump and risk assets sell off.",
        "key_mechanisms": ["deleveraging"], "stated_limitations": ["one simulation"],
    }
    a.update(over)
    return a


def test_schema_accepts_valid_and_rejects_invalid_answers():
    schema.validate(answer())
    bad = answer()
    bad["factors"]["oil"]["intensity"] = "huge"
    with pytest.raises(schema.SchemaError, match="intensity"):
        schema.validate(bad)
    with pytest.raises(schema.SchemaError, match="asset_directions"):
        schema.validate(answer(asset_directions={"SPY": "-"}))


def test_parse_json_answer_tolerates_code_fences():
    text = "Here you go:\n```json\n" + json.dumps(answer()) + "\n```"
    assert schema.parse_json_answer(text)["behaviour"]["duration"] == "weeks"


@pytest.fixture(scope="module")
def macro():
    rng = np.random.default_rng(0)
    idx = pd.bdate_range("2005-01-03", "2022-12-30")
    n = len(idx)
    return pd.DataFrame({
        "DGS10": 3 + np.cumsum(rng.normal(0, 0.05, n)), "DCOILWTICO": 60 * np.exp(np.cumsum(rng.normal(0, 0.02, n))),
        "VIXCLS": np.clip(18 + np.cumsum(rng.normal(0, 0.5, n)) * 0.1, 9, 80),
        "DTWEXBGS": 100 * np.exp(np.cumsum(rng.normal(0, 0.003, n))), "BAA10Y": 2 + np.cumsum(rng.normal(0, 0.01, n)),
    }, index=idx)


def test_magnitudes_come_from_historical_quantiles_not_the_llm(macro):
    as_of = pd.Timestamp("2022-12-30")
    changes = tr.h_day_changes(macro, 20, as_of)
    up = tr.factor_shocks(answer(), changes)
    assert up["d_yield10_bp"] == pytest.approx(changes["d_yield10_bp"].quantile(0.975))
    down = answer()
    down["factors"]["rates_10y"] = {"direction": "-", "intensity": "extreme", "confidence": "high"}
    down["factors"]["oil"] = {"direction": "0", "intensity": "low", "confidence": "low"}
    s = tr.factor_shocks(down, changes)
    assert s["d_yield10_bp"] == pytest.approx(min(changes["d_yield10_bp"].quantile(0.005), 0))
    assert s["dln_oil"] == 0.0
    # no future data: changes after as_of must not affect the quantiles
    cut = tr.h_day_changes(macro, 20, pd.Timestamp("2015-12-31"))
    assert cut.index.max() <= pd.Timestamp("2015-12-31")


def test_translate_and_scenario_risk(macro):
    betas = pd.DataFrame(0.0, index=list(schema.ASSETS), columns=["d_yield10_bp", "dln_oil", "d_vix", "dln_usd", "d_credit_bp"])
    betas.loc["AGG", "d_yield10_bp"] = -0.0006            # bonds fall when yields rise
    betas.loc["SPY", "d_vix"] = -0.004                    # equities fall when VIX rises
    t = tr.translate(answer(), macro, betas, pd.Timestamp("2022-12-30"))
    assert t.horizon == 20 and t.lam == 1.0 and t.vol_mult == 1.5
    assert t.etf_shocks["AGG"] < 0 and t.etf_shocks["SPY"] < 0
    assert 0 <= t.consistency <= 1
    cov = pd.DataFrame(np.diag(np.full(7, 1e-4)), index=list(schema.ASSETS), columns=list(schema.ASSETS))
    w = pd.Series({"SPY": 0.4, "AGG": 0.6})
    risk = tr.scenario_risk(t, w, cov, cov * 4, np.random.default_rng(1), n=20_000)
    assert risk["loss"] == pytest.approx(-(0.4 * t.etf_shocks["SPY"] + 0.6 * t.etf_shocks["AGG"]))
    assert risk["es"] >= risk["var"] > risk["loss"]
    assert risk["contributions"].sum() == pytest.approx(risk["loss"])


def test_replay_fidelity():
    t = tr.Translation(20, pd.Series(dtype=float), pd.Series({"SPY": -0.1, "AGG": -0.02, "GLD": 0.03}), 0.0, 1.0, 1.0, True)
    real = pd.Series({"SPY": -0.08, "AGG": -0.03, "GLD": 0.01})
    f = tr.replay_fidelity(t, real)
    assert f["direction_hit_rate"] == 1.0 and f["rank_corr"] == pytest.approx(1.0)


def test_seed_is_built_from_data_up_to_as_of_and_replays_are_anonymised(macro):
    from quantedge.behavioral.seed import build_prompt, build_seed, load_scenarios

    scen = load_scenarios()
    rng = np.random.default_rng(2)
    idx = pd.bdate_range("2010-01-04", "2022-12-30")
    rets = pd.DataFrame(rng.normal(0, 0.01, (len(idx), 7)), index=idx, columns=list(schema.ASSETS))
    replay = build_seed("R4", scen, rets, macro)
    for t in schema.ASSETS:
        assert t not in replay                              # no tickers in a blind replay
    assert "2022" not in replay and "Broad US equity fund" in replay
    fwd = build_seed("B2", scen, rets, macro)
    assert "SPY" in fwd and "oil" in fwd.lower()
    # data after the as-of date must not change the replay seed
    late = rets.copy()
    late.loc["2022-01-04":] *= 5
    assert build_seed("R4", scen, late, macro) == replay
    assert "do not invent" in build_prompt("B1", scen).lower()


def test_ingest_validates_and_hashes_a_run(tmp_path):
    from quantedge.behavioral.seed import ingest

    run = tmp_path / "run_1"
    run.mkdir()
    for f in ("seed.md", "prompt.txt", "raw_report.md"):
        (run / f).write_text("x", encoding="utf-8")
    (run / "run_config.json").write_text("{}", encoding="utf-8")
    (run / "report_agent_answers.json").write_text(json.dumps(answer()), encoding="utf-8")
    assert ingest(run)["behaviour"]["duration"] == "weeks"
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    assert set(manifest["files"]) == {"seed.md", "prompt.txt", "raw_report.md", "run_config.json", "report_agent_answers.json"}
    (run / "raw_report.md").unlink()
    with pytest.raises(FileNotFoundError):
        ingest(run)


def test_client_runs_the_full_pipeline_against_a_fake_service(tmp_path, monkeypatch):
    from quantedge.behavioral import client as cl

    calls = []

    class R:
        def __init__(self, data):
            self.ok, self.status_code, self._d = True, 200, {"success": True, "data": data}

        def json(self):
            return self._d

    def fake_post(url, timeout=None, **kw):
        path = url.split("5001")[1]
        calls.append(path)
        return R({
            "/api/graph/ontology/generate": {"project_id": "p1"},
            "/api/graph/build": {"task_id": "t1"},
            "/api/simulation/create": {"simulation_id": "s1"},
            "/api/simulation/prepare": {"task_id": "t2"},
            "/api/simulation/prepare/status": {"status": "completed"},
            "/api/simulation/start": {},
            "/api/report/generate": {"task_id": "t3"},
            "/api/report/generate/status": {"status": "completed"},
            "/api/report/chat": {"response": "```json\n" + json.dumps(answer()) + "\n```"},
        }[path])

    def fake_get(url, timeout=None):
        path = url.split("5001")[1]
        calls.append(path)
        if path.startswith("/api/graph/task/"):
            return R({"status": "completed"})
        if path.endswith("/run-status"):
            return R({"runner_status": "completed"})
        return R({"markdown_content": "# Report\nRates up, equities down."})

    monkeypatch.setattr(cl.requests, "post", fake_post)
    monkeypatch.setattr(cl.requests, "get", fake_get)
    run = tmp_path / "run_1"
    run.mkdir()
    for f, txt in (("seed.md", "seed"), ("prompt.txt", "prompt"), ("run_config.json", "{}")):
        (run / f).write_text(txt, encoding="utf-8")
    info = cl.MiroFishClient("http://localhost:5001", poll_s=0).run(run, "seed", "prompt", "test")
    assert info["simulation_id"] == "s1" and info["questionnaire_attempts"] == [True]
    assert (run / "raw_report.md").read_text(encoding="utf-8").startswith("# Report")
    assert calls.index("/api/simulation/start") > calls.index("/api/simulation/prepare")
    assert (run / "manifest.json").exists()
