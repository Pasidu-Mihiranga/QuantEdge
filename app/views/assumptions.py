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
              delta_color="off", delta_arrow="off", border=True, help="The most the committee accepts losing in a crisis; the other limits follow from it.")
    st.metric("Bad-day limit", f"−{money(lim['es99_max'] * nav)}", "average 1-in-100-day loss", delta_color="off",
              delta_arrow="off", border=True, help="The average loss on the worst 1 day in 100, measured over years that include 2008.")
    st.metric("Equity", "≤ 50%", "no fund > 40%; bonds ≤ 65%", delta_color="off", delta_arrow="off", border=True,
              help="Limits on concentration: energy, technology and emerging markets at most 10% each, gold at most 15%.")

st.subheader("What the model does not capture")
cols = st.columns(2, gap="medium")
for i, (title, text) in enumerate(NOT_CAPTURED):
    with cols[i % 2].container(border=True):
        st.markdown(f"**{title}**")
        st.caption(text.replace("$", "\\$"))

rob = n["robustness"]
st.info(f"Our return assumptions decide the verdict: over {sum(rob.values())} combinations it is ACCEPT in {rob.get('ACCEPT', 0)}, "
        f"ADJUST in {rob.get('ADJUST', 0)}, REJECT in {rob.get('REJECT', 0)}. The risk limits hold in every case. Try it "
        "yourself on 'Our recommendation', under What would change it.", icon=":material/tune:")

with st.expander("The choices we made, and why", icon=":material/gavel:"):
    st.table(pd.DataFrame([d[1:] for d in DECISIONS if d[0] not in ("D6", "D7")],
                          columns=["Choice", "What we chose", "Reasonable range", "Why"]).set_index("Choice"))
    st.caption("Agreed and signed on 29 October 2026, before the final 2023–2026 test was run.")

with st.expander("How the numbers were made", icon=":material/construction:"):
    say(f"- **Data:** daily prices of the seven funds (Yahoo Finance) and US economic data (FRED), November 2004 to "
        f"{n['data_end']}. Unusual days were checked against the news and kept, never deleted.\n"
        "- **No hindsight:** every forecast uses only information available at the time.\n"
        "- **A fair test:** 2004–2018 to build the models, 2019–2022 to choose between them, 2023–2026 to test them once, "
        "after every choice was fixed.\n"
        "- **Checked twice:** every result was computed by two separately written programs, which agree.")

st.subheader("Technical details")
TOPICS = {"Data and quality checks": "data_quality.py", "All risk models, 2008–2022": "models.py",
          "Tail risk (EVT) diagnostics": "tail_evt.py", "Regimes, risk overlay, copula and FX": "innovation.py",
          "Formulas, conventions and AI disclosure": "methodology.py"}
topic = st.selectbox("Technical details", list(TOPICS), index=None, placeholder="Choose a topic for the full technical detail",
                     label_visibility="collapsed", key="tech_topic")
if topic:
    with st.container(border=True):
        runpy.run_path(str(Path(__file__).resolve().parents[1] / "technical" / TOPICS[topic]), run_name="__main__")
