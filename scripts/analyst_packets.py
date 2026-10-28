"""Variant A (analyst, without MiroFish): packets, validation and the blinding guard (Step 20 §3.1).

    .venv\\Scripts\\python scripts\\analyst_packets.py build   # one briefing + blank template per scenario
    .venv\\Scripts\\python scripts\\analyst_packets.py check   # which answers exist, are valid, are committed

The analyst reads only data/behavioral/analyst/packets/<id>_briefing.md (the same seed facts MiroFish
receives) and writes data/behavioral/analyst/<id>.json, using the form (tools/analyst_form.py) or by
editing the template. MiroFish runs for a scenario are refused until its answers are committed.
"""

from __future__ import annotations

import json
import sys

import pandas as pd

from quantedge.behavioral.blinding import ANALYST, status
from quantedge.behavioral.schema import ASSETS, FACTORS
from quantedge.behavioral.seed import build_prompt, build_seed, load_scenarios
from quantedge.config import load_config
from quantedge.data.partition import load_returns
from quantedge.paths import ARTIFACTS

PACKETS = ANALYST / "packets"


def template() -> dict:
    return {
        "factors": {f: {"direction": "", "intensity": "", "confidence": ""} for f in FACTORS},
        "behaviour": {"panic_selling": None, "flight_to_safety": [], "contagion_breadth": None, "herding": None,
                      "investor_disagreement": None, "duration": ""},
        "asset_directions": {a: "" for a in ASSETS},
        "narrative_summary": "", "key_mechanisms": [], "stated_limitations": [],
        "_analyst": {"name": "", "completed_utc": "", "declaration": "I wrote these answers without seeing any MiroFish output."},
    }


def build() -> None:
    cfg = load_config()
    scen = load_scenarios()
    returns = load_returns("dev+val", cfg)
    macro = pd.read_parquet(ARTIFACTS / "clean_macro.parquet")
    PACKETS.mkdir(parents=True, exist_ok=True)
    for sid in scen["scenarios"]:
        briefing = build_seed(sid, scen, returns, macro) + "\n## Task\n\n" + build_prompt(sid, scen) + "\n"
        (PACKETS / f"{sid}_briefing.md").write_text(briefing, encoding="utf-8")
        (PACKETS / f"{sid}_template.json").write_text(json.dumps(template(), indent=2), encoding="utf-8")
    print(f"packets written for {len(scen['scenarios'])} scenarios in {PACKETS}")


def check() -> int:
    scen = load_scenarios()
    rows = [(sid, *status(sid)) for sid in scen["scenarios"]]
    for sid, state, why in rows:
        print(f"{sid:3s} {state:12s} {why}")
    return 0 if all(r[1] == "ready" for r in rows) else 1


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "build":
        build()
    else:
        sys.exit(check())
