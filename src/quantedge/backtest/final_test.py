"""The final out-of-sample test (Step 22 M7): run once, after the methodology freeze.

    python -m quantedge.backtest.final_test

- Refuses to run unless the git tag `methodology-freeze-v1` exists (TestLockedError).
- Refuses to run a second time: the result file is the record. A rerun is possible only with
  `--log-deviation "<reason>"`, which appends the reason to the freeze record as a post-hoc deviation.
- Uses the frozen champion and the frozen challenger configurations; nothing is re-tuned. Walk-forward
  forecasting still trains only on data before each forecast day.
- Applies adoption condition 3 (Step 22 §3.8): on the test period the challenger's primary loss
  (99% pinball) must be no more than `ml.noninferiority_margin` worse than the champion's.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime

import pandas as pd

from quantedge.config import Config, load_config
from quantedge.data.partition import Partition, TestLockedError
from quantedge.paths import ARTIFACTS, DECISIONS

RESULT = ARTIFACTS / "final_test_result.json"
FREEZE_RECORD = DECISIONS / "methodology_freeze.md"


def check_allowed(cfg: Config, frozen: bool | None = None, deviation: str | None = None) -> None:
    part = Partition.from_config(cfg)
    if not (part.frozen() if frozen is None else frozen):
        raise TestLockedError(f"The final test needs the git tag '{part.freeze_tag}'. Run scripts/freeze.py first.")
    if RESULT.exists() and not deviation:
        raise RuntimeError(f"The final test has already been run ({RESULT}). It runs once; a rerun needs "
                           "--log-deviation with a reason, which is recorded in the freeze record.")


def adoption_condition_3(test_scores: pd.DataFrame, champion: str, margin: float) -> pd.DataFrame:
    """Challenger passes condition 3 if its test pinball <= champion pinball x (1 + margin)."""
    base = float(test_scores.loc[champion, "pinball"])
    out = test_scores[["pinball", "exceptions", "kupiec_p", "cc_p", "passes"]].copy()
    out["pinball_vs_champion"] = out["pinball"] / base - 1.0
    out["condition_3"] = out["pinball"] <= base * (1.0 + margin)
    return out


def run(cfg: Config, deviation: str | None = None) -> dict:
    from quantedge import pipeline as p
    from quantedge.backtest.engine import run_models
    from quantedge.backtest.report import selection_table
    from quantedge.data.partition import load_returns
    from quantedge.ml.quantile_models import LinearQR, walk_forward_ml
    from quantedge.portfolio.walkforward import candidate_strategies, walk_forward
    from quantedge.portfolio.weights_path import point_in_time_weights

    check_allowed(cfg, deviation=deviation)
    part = Partition.from_config(cfg)
    champion_info = json.loads((ARTIFACTS / "champion.json").read_text(encoding="utf-8"))
    status = json.loads((ARTIFACTS / "status.json").read_text(encoding="utf-8"))
    champion, focus = champion_info["champion"], status["focus_portfolio"]

    returns = load_returns("all", cfg)
    rf = pd.read_parquet(ARTIFACTS / "returns_rf.parquet")["rf"].reindex(returns.index)
    from quantedge.decision.ips import IPSLimits

    strategies, _ = candidate_strategies(cfg, IPSLimits.from_config(cfg.ips), list(cfg.universe))
    wf = walk_forward(returns, strategies[focus], rf, window=cfg.portfolio.estimation_window_days,
                      cost_bps=cfg.portfolio.cost_bps_per_side, name=focus)
    wpath = point_in_time_weights(wf.weights_history, returns.index, cfg.partition.warmup_weights)
    start, end = part.test_start, returns.index.max()

    specs = [s for s in p.backtest_specs(cfg) if s.name == champion]
    results = run_models(specs, returns, wpath, cfg.risk.default_window, start=start, end=end)

    macro = pd.read_parquet(ARTIFACTS / "clean_macro.parquet")
    from quantedge.ml.features import build_features, garch_sigma_path
    from quantedge.portfolio.weights_path import pit_loss_target, pit_risk_returns

    sigma = garch_sigma_path(pit_risk_returns(returns, wpath), refit_every=cfg.ml["retrain_every"])
    X = build_features(returns, macro, wpath, sigma)
    y = pit_loss_target(returns, wpath)
    levels = (0.95, 0.975, 0.99)
    es_levels = {0.975: tuple(cfg.ml["es_integral_levels"]), 0.99: (0.99, 0.9925, 0.995, 0.9975)}
    kw = dict(retrain_every=cfg.ml["retrain_every"], start=start, end=end, es_levels=es_levels)
    results["Linear QR"] = walk_forward_ml(lambda lv: LinearQR(lv), X, y, levels, **kw)
    common = sorted(set.intersection(*(set(d.index) for d in results.values())))
    scores = selection_table({k: v.loc[common] for k, v in results.items()}, 0.99)
    verdict = adoption_condition_3(scores, champion, cfg.ml["noninferiority_margin"])
    for name, df in results.items():
        df.to_parquet(ARTIFACTS / f"final_test_{name.lower().replace(' ', '_').replace('-', '_')}.parquet")
    verdict.to_parquet(ARTIFACTS / "final_test_scores.parquet")
    result = {"run_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "test_start": str(start.date()),
              "test_end": str(end.date()), "days": len(common), "champion": champion,
              "condition_3": {k: bool(v) for k, v in verdict["condition_3"].items()}, "deviation": deviation}
    RESULT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    with FREEZE_RECORD.open("a", encoding="utf-8") as fh:
        fh.write(f"\n## Final test run {result['run_utc']}\n\n")
        if deviation:
            fh.write(f"**Post-hoc deviation:** {deviation}\n\n")
        fh.write(verdict.to_markdown() if hasattr(verdict, "to_markdown") else verdict.to_string())
        fh.write("\n")
    return {"scores": verdict, "result": result}


def main() -> None:
    ap = argparse.ArgumentParser(description="Run the locked final test once (after the methodology freeze).")
    ap.add_argument("--log-deviation", help="reason for a rerun; recorded as a post-hoc deviation")
    args = ap.parse_args()
    out = run(load_config(), deviation=args.log_deviation)
    print(out["scores"].to_string())


if __name__ == "__main__":
    main()
