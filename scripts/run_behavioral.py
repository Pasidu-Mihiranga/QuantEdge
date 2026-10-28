"""Behavioural Stress Lab runs (Step 19).

    # variant B: one MiroFish run (needs the Vertex proxy and `docker compose up` in mirofish-service/)
    .venv\\Scripts\\python scripts\\run_behavioral.py B2 --k 1
    # variant A: the team analyst's answers for the same trigger, through the identical translation
    .venv\\Scripts\\python scripts\\run_behavioral.py B2 --analyst data/behavioral/analyst/B2.json

    # feasibility gate: a neutral benchmark scenario that is NOT one of the pre-registered ones,
    # so the analyst's blinding and the scenarios.yaml hash are untouched
    .venv\\Scripts\\python scripts\run_behavioral.py G0 --gate --max-rounds 10

Outputs per run in data/behavioral/runs/<scenario>/<run_k | analyst>/: seed.md, prompt.txt,
run_config.json, raw_report.md, report_agent_answers.json, translated_shocks.parquet,
portfolio_impact.parquet and manifest.json (SHA-256 of every file).
"""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

import pandas as pd

from quantedge.behavioral.seed import (
    BEHAVIORAL,
    build_prompt,
    build_seed,
    ingest,
    load_scenarios,
    new_run_dir,
    scenarios_sha256,
    write_manifest,
)
from quantedge.behavioral.translate import (
    realised_returns,
    replay_fidelity,
    scenario_risk,
    translate,
)
from quantedge.config import load_config
from quantedge.data.partition import load_returns
from quantedge.paths import ARTIFACTS
from quantedge.stress.reverse import stressed_sigma

GATE_SCENARIO = {
    "kind": "forward",
    "title": "Feasibility benchmark (not pre-registered, not scored)",
    "trigger": "A very large technology company reports quarterly earnings far below expectations and cuts its "
               "outlook; its shares fall sharply in after-hours trading.",
    "as_of": "2022-12-30",
}


def translate_and_score(run_dir: Path, scenario_id: str, scen: dict, answer: dict, cfg, returns, macro) -> dict:
    s = scen["scenarios"][scenario_id]
    betas = pd.read_parquet(ARTIFACTS / "stress_betas_stress.parquet")
    t = translate(answer, macro, betas, pd.Timestamp(s["as_of"]))
    hist = returns.loc[: s["as_of"]]
    calm = hist.cov()
    stress = stressed_sigma(hist, {k: v for k, v in cfg.stress["historical"].items() if v[1] <= s["as_of"]}) \
        if any(v[1] <= s["as_of"] for v in cfg.stress["historical"].values()) else calm * 2
    rows = []
    for f in sorted(ARTIFACTS.glob("wf_weights_*.parquet")):
        name = f.stem.replace("wf_weights_", "")
        w = pd.read_parquet(f).iloc[-1]
        risk = scenario_risk(t, w, calm, stress, cfg.rng(stream=19), n=50_000)
        rows.append({"candidate": name, "loss": risk["loss"], "scenario_var99": risk["var"], "scenario_es99": risk["es"]})
    pd.DataFrame({"factor_shock": t.factor_shocks}).to_parquet(run_dir / "translated_factors.parquet")
    pd.DataFrame({"etf_shock": t.etf_shocks}).to_parquet(run_dir / "translated_shocks.parquet")
    pd.DataFrame(rows).set_index("candidate").to_parquet(run_dir / "portfolio_impact.parquet")
    out = {"horizon_days": t.horizon, "lambda": t.lam, "vol_mult": t.vol_mult, "consistency": t.consistency,
           "flight_to_safety_ok": t.flight_to_safety_ok}
    if s["kind"] == "replay":
        out["fidelity"] = replay_fidelity(t, realised_returns(returns, tuple(s["window"])))
    (run_dir / "translation_summary.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    write_manifest(run_dir)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("scenario")
    ap.add_argument("--k", type=int, default=1, help="replicate number (variant B)")
    ap.add_argument("--analyst", help="JSON answers written by the team without MiroFish (variant A)")
    ap.add_argument("--base-url", default="http://localhost:5001")
    ap.add_argument("--max-rounds", type=int, default=None)
    ap.add_argument("--gate", action="store_true", help="feasibility benchmark with the neutral G0 scenario")
    args = ap.parse_args()

    if not args.gate and not args.analyst:
        from quantedge.behavioral.blinding import require_analyst_first

        require_analyst_first(args.scenario)   # variant A must be committed before any MiroFish run
    cfg = load_config()
    scen = load_scenarios()
    if args.gate:
        scen["scenarios"] = {"G0": GATE_SCENARIO}
        args.scenario = "G0"
    returns = load_returns("dev+val", cfg)
    macro = pd.read_parquet(ARTIFACTS / "clean_macro.parquet")
    max_rounds = args.max_rounds or scen["scale"]["max_rounds"]
    if args.gate:
        run_dir = BEHAVIORAL / "gate" / f"run_{args.k}"
    elif args.analyst:
        run_dir = BEHAVIORAL / "runs" / args.scenario / "analyst"
    else:
        run_dir = new_run_dir(args.scenario, args.k)
    run_dir.mkdir(parents=True, exist_ok=True)
    seed, prompt = build_seed(args.scenario, scen, returns, macro), build_prompt(args.scenario, scen)
    (run_dir / "seed.md").write_text(seed, encoding="utf-8")
    (run_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
    meta = {"scenario": args.scenario,
            "variant": "gate benchmark" if args.gate else ("A (analyst)" if args.analyst else "B (MiroFish)"),
            "scenarios_sha256": scenarios_sha256(), "mirofish_commit": cfg.behavioral.get("mirofish_commit"),
            "llm": cfg.behavioral.get("llm"), "llm_thinking_budget": 0,
            "mirofish_image": cfg.behavioral.get("mirofish_image"), "max_rounds": max_rounds}
    (run_dir / "run_config.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    t0 = time.monotonic()
    if args.analyst:
        shutil.copyfile(args.analyst, run_dir / "report_agent_answers.json")
        (run_dir / "raw_report.md").write_text("Variant A: answers written by the team analyst without MiroFish.\n",
                                               encoding="utf-8")
    else:
        from quantedge.behavioral.client import MiroFishClient

        MiroFishClient(args.base_url).run(run_dir, seed, prompt, f"QuantEdge {args.scenario} run {args.k}", max_rounds)
    answer = ingest(run_dir)
    summary = translate_and_score(run_dir, args.scenario, scen, answer, cfg, returns, macro)
    print(f"{run_dir}: {time.monotonic() - t0:.0f}s, {json.dumps(summary)}")


if __name__ == "__main__":
    main()
