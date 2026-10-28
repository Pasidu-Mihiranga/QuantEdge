"""Seed documents, prompts and the run cache (Step 19 §3.4, §3.7, §3.8).

Seeds are generated from approved-data artifacts only (no hand edits). Replays are anonymised:
generic fund names instead of tickers, no calendar dates, and no data after the as-of date.
Every run directory carries a manifest of SHA-256 hashes; `ingest` validates a run (also used for
the manual fallback, when files are exported from the MiroFish UI by hand).
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import yaml

from quantedge.behavioral.schema import QUESTIONNAIRE, parse_json_answer
from quantedge.paths import DATA

BEHAVIORAL = DATA / "behavioral"
SCENARIOS_FILE = BEHAVIORAL / "scenarios.yaml"
ROLES = {
    "SPY": ("Broad US equity fund", "US large-cap equities"),
    "EFA": ("Developed ex-US equity fund", "Developed-market equities outside the US"),
    "EEM": ("Emerging-market equity fund", "Emerging-market equities"),
    "AGG": ("Investment-grade bond fund", "US investment-grade bonds"),
    "GLD": ("Gold fund", "Physical gold"),
    "XLE": ("Energy-sector equity fund", "US energy-sector equities"),
    "XLK": ("Technology-sector equity fund", "US technology-sector equities"),
}
MACRO_LABELS = {"DGS10": "10-year government bond yield (%)", "DTB3": "3-month bill rate (%)",
                "VIXCLS": "Equity implied volatility index", "BAA10Y": "Corporate credit spread (pp)",
                "DTWEXBGS": "Trade-weighted dollar index", "DCOILWTICO": "Crude oil price (USD)"}


def load_scenarios(path: Path = SCENARIOS_FILE) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def scenarios_sha256(path: Path = SCENARIOS_FILE) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_seed(scenario_id: str, scen: dict, returns: pd.DataFrame, macro: pd.DataFrame) -> str:
    s = scen["scenarios"][scenario_id]
    as_of = pd.Timestamp(s["as_of"])
    replay = s["kind"] == "replay"
    r = returns.loc[:as_of].iloc[-252:]
    m = macro.loc[:as_of].ffill().iloc[-1]
    name = (lambda t: ROLES[t][0]) if replay else (lambda t: f"{t} ({ROLES[t][1]})")
    lines = ["# Market briefing", "", "## Current conditions"]
    for code, label in MACRO_LABELS.items():
        if code in m and pd.notna(m[code]):
            lines.append(f"- {label}: {m[code]:.2f}")
    if "CPIAUCSL" in macro:
        cpi = macro["CPIAUCSL"].loc[:as_of].dropna()
        if len(cpi) > 260:
            lines.append(f"- Consumer-price inflation, year on year: {cpi.iloc[-1] / cpi.iloc[-253] - 1:.1%}")
    lines += ["", "## Investable funds (trailing one year)", "",
              "| Fund | Return | Volatility |", "|---|---|---|"]
    for t in returns.columns:
        lines.append(f"| {name(t)} | {(1 + r[t]).prod() - 1:.1%} | {r[t].std() * 252 ** 0.5:.1%} |")
    corr = r.corr()
    lines += ["", f"Correlation between the broad equity fund and the bond fund over the year: {corr.loc['SPY', 'AGG']:.2f}.",
              "", "## Market participants"]
    for a in scen["archetypes"]:
        lines.append(f"- **{a['id']}**: {a['profile']}")
    lines += ["", "## Event", "", s["trigger"]]
    return "\n".join(lines) + "\n"


def build_prompt(scenario_id: str, scen: dict) -> str:
    s = scen["scenarios"][scenario_id]
    return ("Simulate how the five groups of market participants in the briefing react to the event over the "
            "following days to months: who sells, who buys, where money flows, how panic or herding develops, "
            "and how the funds are likely to move. Report the main mechanisms, alternative paths, assumptions and "
            "limitations. Do not invent verified prices, returns or unsupported probabilities."
            + ("" if s["kind"] == "forward" else " Treat the event as hypothetical; do not identify real dates."))


def new_run_dir(scenario_id: str, k: int) -> Path:
    d = BEHAVIORAL / "runs" / scenario_id / f"run_{k}"
    d.mkdir(parents=True, exist_ok=True)
    return d


TEXT_SUFFIXES = {".md", ".json", ".jsonl", ".txt", ".yaml"}


def write_manifest(run_dir: Path) -> dict:
    """SHA-256 of every run file. Text files are first normalised to LF line endings (Windows
    `write_text` adds CR), matching .gitattributes, so the hashes hold on any fresh checkout."""
    files = {}
    for p in sorted(run_dir.iterdir()):
        if not p.is_file() or p.name == "manifest.json":
            continue
        data = p.read_bytes()
        if p.suffix in TEXT_SUFFIXES and b"\r\n" in data:
            data = data.replace(b"\r\n", b"\n")
            p.write_bytes(data)
        files[p.name] = hashlib.sha256(data).hexdigest()
    out = {"written_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "scenarios_sha256": scenarios_sha256(),
           "files": files}
    (run_dir / "manifest.json").write_text(json.dumps(out, indent=2), encoding="utf-8", newline="\n")
    return out


REQUIRED = ("seed.md", "prompt.txt", "run_config.json", "raw_report.md", "report_agent_answers.json")


def ingest(run_dir: Path) -> dict:
    """Validate a run directory (scripted or manual): required files present, questionnaire answer
    schema-valid, manifest written. Returns the validated answer."""
    missing = [f for f in REQUIRED if not (run_dir / f).exists()]
    if missing:
        raise FileNotFoundError(f"{run_dir}: missing {missing}")
    answer = parse_json_answer((run_dir / "report_agent_answers.json").read_text(encoding="utf-8"))
    write_manifest(run_dir)
    return answer


__all__ = ["QUESTIONNAIRE", "build_prompt", "build_seed", "ingest", "load_scenarios", "new_run_dir", "write_manifest"]
