"""Seed document, prompt and run folder for one simulation. Every run carries a manifest of SHA-256 hashes."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import yaml

from quantedge.behavioral.schema import parse_json_answer
from quantedge.paths import DATA

BEHAVIORAL = DATA / "behavioral"
SCENARIOS_FILE = BEHAVIORAL / "scenarios.yaml"
ROLES = {"SPY": "US large-cap equities", "EFA": "Developed-market equities outside the US", "EEM": "Emerging-market equities",
         "AGG": "US investment-grade bonds", "GLD": "Physical gold", "XLE": "US energy-sector equities",
         "XLK": "US technology-sector equities"}
MACRO_LABELS = {"DGS10": "10-year government bond yield (%)", "DTB3": "3-month bill rate (%)",
                "VIXCLS": "Equity implied volatility index", "BAA10Y": "Corporate credit spread (pp)",
                "DTWEXBGS": "Trade-weighted dollar index", "DCOILWTICO": "Crude oil price (USD)"}
REQUIRED = ("seed.md", "prompt.txt", "run_config.json", "raw_report.md", "report_agent_answers.json")


def load_scenarios(path: Path = SCENARIOS_FILE) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def scenarios_sha256(path: Path = SCENARIOS_FILE) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_seed(scenario_id: str, scen: dict, returns: pd.DataFrame, macro: pd.DataFrame) -> str:
    """The market briefing the agents read: data up to the scenario's as-of date only."""
    s = scen["scenarios"][scenario_id]
    as_of = pd.Timestamp(s["as_of"])
    r = returns.loc[:as_of].iloc[-252:]
    m = macro.loc[:as_of].ffill().iloc[-1]
    lines = ["# Market briefing", "", "## Current conditions"]
    lines += [f"- {label}: {m[code]:.2f}" for code, label in MACRO_LABELS.items() if code in m and pd.notna(m[code])]
    lines += ["", "## Investable funds (trailing one year)", "", "| Fund | Return | Volatility |", "|---|---|---|"]
    lines += [f"| {t} ({ROLES[t]}) | {(1 + r[t]).prod() - 1:.1%} | {r[t].std() * 252 ** 0.5:.1%} |" for t in returns.columns]
    lines += ["", f"Correlation between US equities and bonds over the year: {r['SPY'].corr(r['AGG']):.2f}.", "",
              "## Market participants"]
    lines += [f"- **{a['id']}**: {a['profile']}" for a in scen["archetypes"]]
    lines += ["", "## Event", "", s["trigger"]]
    return "\n".join(lines) + "\n"


def build_prompt() -> str:
    return ("Simulate how the five groups of market participants in the briefing react to the event over the following "
            "days to months: who sells, who buys, where money flows, how panic or herding develops, and how the funds are "
            "likely to move. Report the main mechanisms, alternative paths, assumptions and limitations. Do not invent "
            "verified prices, returns or unsupported probabilities.")


def new_run_dir(scenario_id: str, k: int) -> Path:
    d = BEHAVIORAL / "runs" / scenario_id / f"run_{k}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_manifest(run_dir: Path) -> dict:
    files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(run_dir.iterdir())
             if p.is_file() and p.name != "manifest.json"}
    out = {"written_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "scenarios_sha256": scenarios_sha256(), "files": files}
    (run_dir / "manifest.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


def ingest(run_dir: Path) -> dict:
    """Validate a finished run: required files present and a schema-valid questionnaire answer."""
    missing = [f for f in REQUIRED if not (run_dir / f).exists()]
    if missing:
        raise FileNotFoundError(f"{run_dir}: missing {missing}")
    return parse_json_answer((run_dir / "report_agent_answers.json").read_text(encoding="utf-8"))
