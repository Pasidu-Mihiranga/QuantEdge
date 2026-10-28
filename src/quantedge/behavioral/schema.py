"""Fixed questionnaire and its validation (Step 19 §3.5).

The same questionnaire is answered by MiroFish's ReportAgent (variant B), by a team analyst without
MiroFish (variant A), and by two human coders reading the raw narrative. Only validated answers are
translated into numbers.
"""

from __future__ import annotations

FACTORS = ("rates_10y", "oil", "vix", "usd", "credit_spread")
ASSETS = ("SPY", "EFA", "EEM", "AGG", "GLD", "XLE", "XLK")
DIRECTIONS = ("+", "0", "-")
INTENSITIES = ("low", "medium", "high", "extreme")
CONFIDENCE = ("low", "medium", "high")
DURATIONS = ("days", "weeks", "months")
SAFE_HAVENS = ("AGG", "GLD", "cash")

QUESTIONNAIRE = f"""Answer ONLY with a JSON object, no other text, using exactly this structure:
{{
  "factors": {{  // one entry for each of {list(FACTORS)}
    "rates_10y": {{"direction": "+|0|-", "intensity": "low|medium|high|extreme", "confidence": "low|medium|high"}}
  }},
  "behaviour": {{
    "panic_selling": 0-3, "flight_to_safety": subset of {list(SAFE_HAVENS)}, "contagion_breadth": 0-3,
    "herding": 0-3, "investor_disagreement": 0-3, "duration": "days|weeks|months"
  }},
  "asset_directions": {{  // one entry for each of {list(ASSETS)}: "+", "0" or "-"
  }},
  "narrative_summary": "two or three sentences",
  "key_mechanisms": ["..."],
  "stated_limitations": ["..."]
}}
Describe directions and intensities only. Do not invent prices, returns or probabilities."""


class SchemaError(ValueError):
    pass


def _level(x, name):
    if not isinstance(x, int) or not 0 <= x <= 3:
        raise SchemaError(f"{name} must be an integer 0-3, got {x!r}")


def validate(answer: dict) -> dict:
    """Return the answer if it matches the schema; raise SchemaError listing the first problem."""
    if not isinstance(answer, dict):
        raise SchemaError("answer must be a JSON object")
    f = answer.get("factors")
    if not isinstance(f, dict) or set(f) != set(FACTORS):
        raise SchemaError(f"factors must contain exactly {FACTORS}")
    for k, v in f.items():
        if v.get("direction") not in DIRECTIONS:
            raise SchemaError(f"factors.{k}.direction must be one of {DIRECTIONS}")
        if v.get("intensity") not in INTENSITIES:
            raise SchemaError(f"factors.{k}.intensity must be one of {INTENSITIES}")
        if v.get("confidence") not in CONFIDENCE:
            raise SchemaError(f"factors.{k}.confidence must be one of {CONFIDENCE}")
    b = answer.get("behaviour")
    if not isinstance(b, dict):
        raise SchemaError("behaviour missing")
    for k in ("panic_selling", "contagion_breadth", "herding", "investor_disagreement"):
        _level(b.get(k), f"behaviour.{k}")
    if not isinstance(b.get("flight_to_safety"), list) or not set(b["flight_to_safety"]) <= set(SAFE_HAVENS):
        raise SchemaError(f"behaviour.flight_to_safety must be a subset of {SAFE_HAVENS}")
    if b.get("duration") not in DURATIONS:
        raise SchemaError(f"behaviour.duration must be one of {DURATIONS}")
    a = answer.get("asset_directions")
    if not isinstance(a, dict) or set(a) != set(ASSETS) or any(v not in DIRECTIONS for v in a.values()):
        raise SchemaError(f"asset_directions must give +, 0 or - for each of {ASSETS}")
    for k in ("narrative_summary",):
        if not isinstance(answer.get(k), str):
            raise SchemaError(f"{k} must be text")
    return answer


def parse_json_answer(text: str) -> dict:
    """Extract and validate the first JSON object in a model reply (tolerates code fences)."""
    import json
    import re

    t = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    start, end = t.find("{"), t.rfind("}")
    if start < 0 or end <= start:
        raise SchemaError("no JSON object in the reply")
    return validate(json.loads(t[start:end + 1]))
