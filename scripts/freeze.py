"""Methodology freeze (gate G3): check the blocking items and write the freeze record.

    .venv\\Scripts\\python scripts\\freeze.py

1. Refuses if any item under "## Blocking" in doc/decisions/freeze_checklist.md is unticked.
2. Writes doc/decisions/methodology_freeze.md with the SHA-256 of the config, the data manifest,
   the requirements files, the artifact manifest, the selected ML configurations and the adoption
   rule text (Step 22 §3.8), plus the champion and the challenger list.
3. Prints the commands to commit the record and create the tag. It never creates the tag itself:
   the team does that deliberately, because the tag unlocks the final test.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import UTC, datetime

from quantedge.config import load_config
from quantedge.data.manifest import sha256_file
from quantedge.paths import ARTIFACTS, DECISIONS, MANIFEST, ROOT

CHECKLIST = DECISIONS / "freeze_checklist.md"
RECORD = DECISIONS / "methodology_freeze.md"


def open_blocking_items(text: str) -> list[str]:
    block = text.split("## Blocking", 1)[1].split("\n## ", 1)[0]
    return [line.strip()[6:] for line in block.splitlines() if line.strip().startswith("- [ ]")]


def adoption_rule_text() -> str:
    step = (ROOT / "doc" / "steps" / "22_ml_challenger_and_data_partition.md").read_text(encoding="utf-8")
    m = re.search(r"### 3\.8.*?(?=\n### |\n## )", step, flags=re.S)
    return m.group(0) if m else ""


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")   # checklist items contain symbols such as <=
    cfg = load_config()
    missing = open_blocking_items(CHECKLIST.read_text(encoding="utf-8"))
    if missing:
        print("Freeze refused. Open blocking items:")
        for item in missing:
            print(f"  - {item}")
        return 1
    rule = adoption_rule_text()
    files = {
        "config.yaml": cfg.sha256,
        "data/raw/manifest.json": sha256_file(MANIFEST),
        "requirements.txt": sha256_file(ROOT / "requirements.txt"),
        "requirements-research.txt": sha256_file(ROOT / "requirements-research.txt"),
        "data/artifacts/artifacts_manifest.json": sha256_file(ARTIFACTS / "artifacts_manifest.json"),
        "data/artifacts/ml_selected_configs.json": sha256_file(ARTIFACTS / "ml_selected_configs.json"),
        "adoption rule text (Step 22 §3.8)": hashlib.sha256(rule.encode("utf-8")).hexdigest(),
    }
    champion = json.loads((ARTIFACTS / "champion.json").read_text(encoding="utf-8"))
    chosen = json.loads((ARTIFACTS / "ml_selected_configs.json").read_text(encoding="utf-8"))
    lines = [
        "# Methodology freeze record",
        "",
        f"**Written:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')} · **Tag:** `{cfg.partition.freeze_tag}` "
        "(created by the team after committing this file)",
        "",
        f"**Champion:** {champion['champion']} ({champion['reason']}); window {champion['window']} days; "
        f"portfolio {champion['portfolio']}",
        f"**Challengers:** Linear QR; LightGBM {chosen.get('LightGBM', {}).get('config')}; "
        f"LSTM {chosen.get('LSTM', {}).get('config')}",
        f"**Seeds:** global {cfg.seed}; LSTM {cfg.ml['lstm']['seeds']}",
        "",
        "| Item | SHA-256 |",
        "|---|---|",
        *[f"| {k} | `{v}` |" for k, v in files.items()],
        "",
        "Any change after the tag is logged below as a post-hoc deviation, with its reason.",
        "",
    ]
    RECORD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Freeze record written: {RECORD}")
    print("Next, deliberately:")
    print(f"  git add {RECORD.relative_to(ROOT)} && git commit -m \"Record methodology freeze\"")
    print(f"  git tag {cfg.partition.freeze_tag}")
    print("  python -m quantedge.backtest.final_test   (runs once)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
