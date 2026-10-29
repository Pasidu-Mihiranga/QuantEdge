"""Assumptions & Limitations (booklet item 6, graded): what we promised, what the model does not capture, and every
technical detail behind one dropdown."""

import runpy
from pathlib import Path

import pandas as pd
import streamlit as st

from components.content import DECISIONS, NOT_CAPTURED
from components.ui import money, need_numbers, pct, say

n = need_numbers()
obj, lim, nav = n["objective"], n["limits"], n["nav_usd"]

st.title("Assumptions & Limitations")
say("What the fund promised, what our analysis cannot see, and the choices behind every number, in plain language.")

st.subheader("What we promised")
with st.container(horizontal=True):
    st.metric("Return objective", "Inflation + 3.5%", f"{pct(obj['required_return'], 2)} a year today", delta_color="off",
              delta_arrow="off", border=True, help="3% for scholarships and research, plus 0.5% real growth, after US inflation "
              f"(the market's 10-year forecast: {pct(obj['inflation_breakeven'], 2)}).")
    st.metric("Crisis budget", f"−{pct(lim['crisis_budget'], 0)}", f"at most {money(lim['crisis_budget'] * nav)} in any crisis",
              delta_color="off", delta_arrow="off", border=True, help="The one preference the other limits are read from (decision D2).")
    st.metric("Bad-day limit", f"−{money(lim['es99_max'] * nav)}", "average 1-in-100-day loss", delta_color="off",
              delta_arrow="off", border=True, help="99% Expected Shortfall through the cycle, data including 2008, at the 25% budget.")
    st.metric("Equity", "≤ 50%", "no fund > 40%; bonds ≤ 65%", delta_color="off", delta_arrow="off", border=True,
              help="Concentration caps (decision D3); energy, technology and emerging markets at most 10% each, gold 15%.")

st.subheader("What the model does not capture")
cols = st.columns(2, gap="medium")
for i, (title, text) in enumerate(NOT_CAPTURED):
    with cols[i % 2].container(border=True):
        st.markdown(f"**{title}**")
        st.caption(text.replace("$", "\\$"))

rob = n["robustness"]
st.info(f"Our return assumptions decide the verdict: over {sum(rob.values())} combinations it is ACCEPT in {rob.get('ACCEPT', 0)}, "
        f"ADJUST in {rob.get('ADJUST', 0)}, REJECT in {rob.get('REJECT', 0)}. The risk limits hold in every case. Try it on "
        "'Our recommendation', under What would change it.", icon=":material/tune:")

with st.expander("The ten decisions the team locked before the test", icon=":material/gavel:"):
    st.table(pd.DataFrame(DECISIONS, columns=["#", "Decision", "Agreed value", "Plausible range", "Why"]).set_index("#"))
    st.caption("Signed and locked on 29 October 2026, before the 2023–2026 test was run; any later change is logged as a deviation.")

with st.expander("How the numbers were made", icon=":material/construction:"):
    say(f"- **Data:** daily prices of the seven funds (Yahoo Finance) and US macro series (FRED), November 2004 to {n['data_end']}, "
        "frozen and hashed; suspect days flagged, never deleted.\n"
        "- **No look-ahead:** every forecast uses only earlier data; weights are those actually held.\n"
        "- **Three periods:** 2004–2018 to build, 2019–2022 to choose, 2023–2026 to test once, after the methodology was frozen.\n"
        "- **Two independent codes:** the analysis notebooks were written separately from this app, and both give the same "
        "verdict, the same portfolio and the same test results.")

st.subheader("Technical details")
TOPICS = {"Data and quality checks": "data_quality.py", "All risk models, 2008–2022": "models.py",
          "Tail risk (EVT) diagnostics": "tail_evt.py", "Regimes, risk overlay, copula and FX": "innovation.py",
          "Formulas, conventions and AI disclosure": "methodology.py"}
topic = st.selectbox("Technical details", list(TOPICS), index=None, placeholder="Choose a topic for the full technical detail",
                     label_visibility="collapsed", key="tech_topic")
if topic:
    with st.container(border=True):
        runpy.run_path(str(Path(__file__).resolve().parents[1] / "technical" / TOPICS[topic]), run_name="__main__")
