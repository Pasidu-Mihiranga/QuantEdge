"""Variant A questionnaire form for the team analyst (run separately from the committee app).

    .venv\\Scripts\\python -m streamlit run tools\\analyst_form.py

Shows only the scenario briefing (the same facts MiroFish receives) and saves schema-valid answers
to data/behavioral/analyst/<scenario>.json. It never shows or loads any MiroFish output.
"""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from quantedge.behavioral.schema import (  # noqa: E402
    ASSETS,
    CONFIDENCE,
    DIRECTIONS,
    DURATIONS,
    FACTORS,
    INTENSITIES,
    SAFE_HAVENS,
    SchemaError,
    validate,
)
from quantedge.behavioral.seed import BEHAVIORAL, load_scenarios  # noqa: E402

LABELS = {"rates_10y": "10-year government bond yield", "oil": "Oil price", "vix": "Equity volatility (VIX)",
          "usd": "US dollar", "credit_spread": "Corporate credit spread"}
ANALYST = BEHAVIORAL / "analyst"

st.set_page_config(page_title="Analyst questionnaire (variant A)", layout="wide")
st.title("Analyst questionnaire: variant A (without MiroFish)")
st.warning("Answer from the briefing and your own judgement only. Do not look at any MiroFish output before "
           "all seven scenarios are saved and committed.")

scen = load_scenarios()
sid = st.selectbox("Scenario", list(scen["scenarios"]), format_func=lambda s: f"{s}: {scen['scenarios'][s]['title']}")
briefing = ANALYST / "packets" / f"{sid}_briefing.md"
with st.expander("Briefing (identical to the facts MiroFish receives)", expanded=True):
    st.markdown(briefing.read_text(encoding="utf-8") if briefing.exists() else "Run `scripts/analyst_packets.py build` first.")

existing = {}
out = ANALYST / f"{sid}.json"
if out.exists():
    existing = json.loads(out.read_text(encoding="utf-8"))
    st.info("Answers for this scenario already exist; saving overwrites them (allowed only before they are committed).")

with st.form(f"form_{sid}"):
    st.subheader("How do the macro factors move?")
    factors = {}
    for f in FACTORS:
        c1, c2, c3 = st.columns(3)
        prev = existing.get("factors", {}).get(f, {})
        factors[f] = {
            "direction": c1.selectbox(f"{LABELS[f]}: direction", DIRECTIONS, key=f"{sid}{f}d",
                                      index=DIRECTIONS.index(prev.get("direction", "0"))),
            "intensity": c2.selectbox("intensity", INTENSITIES, key=f"{sid}{f}i",
                                      index=INTENSITIES.index(prev.get("intensity", "medium"))),
            "confidence": c3.selectbox("confidence", CONFIDENCE, key=f"{sid}{f}c",
                                       index=CONFIDENCE.index(prev.get("confidence", "medium"))),
        }
    st.subheader("How do market participants behave? (0 = none, 3 = severe)")
    pb = existing.get("behaviour", {})
    c = st.columns(4)
    behaviour = {
        "panic_selling": c[0].slider("Panic selling", 0, 3, pb.get("panic_selling", 1), key=f"{sid}ps"),
        "contagion_breadth": c[1].slider("Contagion breadth", 0, 3, pb.get("contagion_breadth", 1), key=f"{sid}cb"),
        "herding": c[2].slider("Herding", 0, 3, pb.get("herding", 1), key=f"{sid}hd"),
        "investor_disagreement": c[3].slider("Investor disagreement", 0, 3, pb.get("investor_disagreement", 1), key=f"{sid}id"),
        "flight_to_safety": st.multiselect("Flight to safety into", SAFE_HAVENS, default=pb.get("flight_to_safety", []),
                                           key=f"{sid}fts"),
        "duration": st.selectbox("How long does the stress last?", DURATIONS, key=f"{sid}dur",
                                 index=DURATIONS.index(pb.get("duration", "weeks"))),
    }
    st.subheader("Direction of each fund")
    cols = st.columns(len(ASSETS))
    pa = existing.get("asset_directions", {})
    assets = {a: cols[i].selectbox(a, DIRECTIONS, key=f"{sid}{a}", index=DIRECTIONS.index(pa.get(a, "0")))
              for i, a in enumerate(ASSETS)}
    summary = st.text_area("Narrative summary (two or three sentences)", existing.get("narrative_summary", ""))
    mechanisms = st.text_area("Key mechanisms (one per line)", "\n".join(existing.get("key_mechanisms", [])))
    limitations = st.text_area("Limitations of your assessment (one per line)", "\n".join(existing.get("stated_limitations", [])))
    name = st.text_input("Your name", existing.get("_analyst", {}).get("name", ""))
    declared = st.checkbox("I wrote these answers without seeing any MiroFish output.")
    submitted = st.form_submit_button("Save answers")

if submitted:
    answer = {"factors": factors, "behaviour": behaviour, "asset_directions": assets, "narrative_summary": summary.strip(),
              "key_mechanisms": [m.strip() for m in mechanisms.splitlines() if m.strip()],
              "stated_limitations": [m.strip() for m in limitations.splitlines() if m.strip()],
              "_analyst": {"name": name.strip(), "completed_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                           "declaration": "I wrote these answers without seeing any MiroFish output." if declared else ""}}
    try:
        if not name.strip() or not declared or not summary.strip():
            raise SchemaError("add your name, a narrative summary and tick the declaration")
        validate(answer)
        ANALYST.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(answer, indent=2), encoding="utf-8")
        st.success(f"Saved {out.name}. When all seven are done, commit them: git add data/behavioral/analyst && git commit")
    except SchemaError as e:
        st.error(f"Not saved: {e}")
