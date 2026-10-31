"""Run the MiroFish comparison and write its results for the app. MiroFish runs separately, on http://localhost:5001.

    python scripts/run_swarm.py run H1 --k 1 --max-rounds 40    # one simulation
    python scripts/run_swarm.py summarise H1                    # data/artifacts/swarm_comparison.json from finished runs
"""

from __future__ import annotations

import argparse
import json

import pandas as pd

from quantedge.behavioral.client import MiroFishClient
from quantedge.behavioral.seed import (
    BEHAVIORAL,
    build_prompt,
    build_seed,
    ingest,
    load_scenarios,
    new_run_dir,
    scenarios_sha256,
)
from quantedge.behavioral.translate import compare_run, evaluate
from quantedge.config import load_config
from quantedge.data.partition import load_returns
from quantedge.paths import ARTIFACTS


def run(scenario: str, k: int, max_rounds: int) -> None:
    cfg, scen = load_config(), load_scenarios()
    returns, macro = load_returns("all", cfg, frozen=True), pd.read_parquet(ARTIFACTS / "clean_macro.parquet")
    d, seed, prompt = new_run_dir(scenario, k), build_seed(scenario, scen, returns, macro), build_prompt()
    (d / "seed.md").write_text(seed, encoding="utf-8")
    (d / "prompt.txt").write_text(prompt, encoding="utf-8")
    (d / "run_config.json").write_text(json.dumps({"scenario": scenario, "k": k, "scenarios_sha256": scenarios_sha256(),
                                                   "mirofish_commit": scen["mirofish_commit"]}, indent=2), encoding="utf-8")
    print(MiroFishClient().run(d, seed, prompt, f"QuantEdge {scenario} run {k}", max_rounds))
    print("valid:", bool(ingest(d)))


def resume(scenario: str, k: int, sim_id: str) -> None:
    d = new_run_dir(scenario, k)
    print(MiroFishClient().finish(d, sim_id))
    print("valid:", bool(ingest(d)))


def summarise(scenario: str) -> None:
    cfg, scen = load_config(), load_scenarios()
    n = json.loads((ARTIFACTS / "decision_numbers.json").read_text(encoding="utf-8"))
    hyp = cfg.stress["hypothetical"]
    w = pd.Series(n["weights"])
    betas = pd.read_parquet(ARTIFACTS / "decision_scenario_betas.parquet")
    macro = pd.read_parquet(ARTIFACTS / "clean_macro.parquet")
    as_of = pd.Timestamp(scen["scenarios"][scenario]["as_of"])
    runs = []
    for d in sorted((BEHAVIORAL / "runs" / scenario).glob("run_*")):
        try:
            runs.append({"run": d.name, **compare_run(ingest(d), macro, betas, w, hyp.get("liquidity_day"), as_of)})
        except (FileNotFoundError, ValueError) as e:
            print(f"skipped {d.name}: {e}")
    if not runs:
        raise SystemExit("no valid runs")
    losses = [r["loss"] for r in runs]
    out = {"scenario": scen["scenarios"][scenario]["title"], "team": evaluate(hyp["shock"], betas, w, hyp.get("liquidity_day")),
           "runs": runs, "mean_loss": sum(losses) / len(losses), "min_loss": min(losses), "max_loss": max(losses)}
    (ARTIFACTS / "swarm_comparison.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"{len(runs)} runs; team {out['team']['loss']:.2%}; swarm mean {out['mean_loss']:.2%}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=["run", "summarise"])
    ap.add_argument("scenario")
    ap.add_argument("--k", type=int, default=1)
    ap.add_argument("--max-rounds", type=int, default=40)
    ap.add_argument("--resume", help="simulation id: go straight to the report and questionnaire")
    a = ap.parse_args()
    if a.action == "summarise":
        summarise(a.scenario)
    elif a.resume:
        resume(a.scenario, a.k, a.resume)
    else:
        run(a.scenario, a.k, a.max_rounds)
