"""Assemble the Step 13 evidence from pipeline artifacts (shared by the app and the memo).

Reads data/artifacts only; no model fitting.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from quantedge.config import Config
from quantedge.decision.ips import IPSLimits
from quantedge.decision.rules import Evidence, Verdict, evaluate, minimum_relaxation
from quantedge.paths import ARTIFACTS


@dataclass(frozen=True)
class DecisionBundle:
    verdict: Verdict
    evidence: Evidence
    focus: str
    champion: str
    champion_reason: str
    weights: dict[str, float]
    var99: float
    worst_hist_loss: float
    worst_hist_name: str


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def build(cfg: Config, artifacts: Path = ARTIFACTS) -> DecisionBundle | None:
    status = _json(artifacts / "status.json")
    names = ["portfolio_scorecard_val", "risk_snapshot", "stress_matrix", "backtest_selection_val_500",
             "risk_contributions"]
    paths = [artifacts / f"{n}.parquet" for n in names]
    if not status or not all(p.exists() for p in paths):
        return None
    card, snap, stress, val, contrib = (pd.read_parquet(p) for p in paths)
    champ_info = _json(artifacts / "champion.json")
    champ = champ_info.get("champion", "Conditional EVT")
    extras = _json(artifacts / "risk_extras.json")
    req = _json(artifacts / "required_return.json")
    focus = status["focus_portfolio"]
    row = card.loc[focus]
    snap99 = snap[snap.alpha == 0.99].set_index("model")
    hyp_col = cfg.stress["hypothetical"]["name"]
    hist_cols = list(cfg.stress["historical"])
    limits = IPSLimits.from_config(cfg.ips)

    # Minimum relaxation across IPS-compliant candidates, with ES measured the same way for each
    # (out-of-sample historical 99% ES) so the candidates are comparable.
    eligible = card[card["weights_within_ips"]]
    cands = pd.DataFrame({
        "vol_oos": eligible["volatility"], "worst_hist_drawdown": eligible["worst_crisis_drawdown"],
        "hypothetical_loss": -stress.loc[eligible.index, hyp_col], "es99_1d": eligible["es99_oos"]})
    ev = Evidence(
        vol_oos=float(row.volatility),
        worst_hist_drawdown=float(row.worst_crisis_drawdown),
        hypothetical_loss=float(-stress.loc[focus, hyp_col]),
        es99_1d=float(snap99.loc[champ, "es"]),
        evt_es99=float(snap99.loc["EVT", "es"]),
        # Once-in-10-years loss from the same model family as the 99% figures, so the numbers agree:
        # the conditional (current-regime) EVT when the champion is Conditional EVT.
        return_level_10y=float(extras.get("return_level_10y_cevt" if champ == "Conditional EVT"
                                          else "return_level_10y_evt", float("nan"))),
        champion_valid=bool(val.loc[champ, "passes"]),
        any_model_valid=bool(val["passes"].any()),
        max_risk_to_capital=float(contrib[contrib.method == "historical ES 99%"]["risk_to_capital"].max()),
        expected_return=float(row.cagr),
        required_return=float(req.get("required_return", float("nan"))),
        relaxation=minimum_relaxation(cands, limits) if len(cands) else None,
    )
    worst = stress.loc[focus, hist_cols]
    return DecisionBundle(
        verdict=evaluate(ev, limits, cfg.decision), evidence=ev, focus=focus, champion=champ,
        champion_reason=champ_info.get("reason", ""), weights=status.get("weights", {}),
        var99=float(snap99.loc[champ, "var"]), worst_hist_loss=float(-worst.min()),
        worst_hist_name=str(worst.idxmin()),
    )
