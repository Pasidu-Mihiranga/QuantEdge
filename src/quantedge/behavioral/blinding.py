"""Blinding guard for the with/without MiroFish comparison (Step 20 §3.1).

Variant A (the team analyst, without MiroFish) must be written and committed to git before any
variant B (MiroFish) run for the same scenario; the commit timestamp is the evidence.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from quantedge.behavioral.schema import SchemaError, validate
from quantedge.behavioral.seed import BEHAVIORAL
from quantedge.paths import ROOT

ANALYST = BEHAVIORAL / "analyst"


def committed(path: Path) -> bool:
    """True when the file is tracked by git and has no uncommitted changes."""
    rel = str(path.relative_to(ROOT)).replace("\\", "/")
    tracked = subprocess.run(["git", "-C", str(ROOT), "ls-files", "--error-unmatch", rel], capture_output=True).returncode == 0
    clean = subprocess.run(["git", "-C", str(ROOT), "diff", "--quiet", "HEAD", "--", rel], capture_output=True).returncode == 0
    return tracked and clean


def status(scenario_id: str) -> tuple[str, str]:
    f = ANALYST / f"{scenario_id}.json"
    if not f.exists():
        return "missing", "no answers yet"
    try:
        answer = json.loads(f.read_text(encoding="utf-8"))
        validate(answer)
    except (ValueError, SchemaError) as e:
        return "invalid", str(e)
    if not answer.get("_analyst", {}).get("name"):
        return "invalid", "_analyst.name is empty"
    if not committed(f):
        return "uncommitted", "valid, but not committed to git yet"
    return "ready", "valid and committed"


def require_analyst_first(scenario_id: str) -> None:
    """Blinding guard used by scripts/run_behavioral.py before any MiroFish run."""
    state, why = status(scenario_id)
    if state != "ready":
        raise SystemExit(f"Refused: variant A answers for {scenario_id} must be written and committed before any "
                         f"MiroFish run ({state}: {why}). See scripts/analyst_packets.py.")
