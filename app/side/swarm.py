"""Crowd simulation: what a simulated crowd of investors does in our crisis, next to the scenario the team designed."""

import json

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from components.palette import palette
from components.ui import explain, money, need_numbers, pct, say
from quantedge.paths import ARTIFACTS

n = need_numbers()
nav, budget = n["nav_usd"], n["limits"]["crisis_budget"]
s = json.loads((ARTIFACTS / "swarm_comparison.json").read_text(encoding="utf-8"))
team, runs = s["team"], s["runs"]
P = palette()
ACCENT, GREY = P.accent, P.grey
TEAM, SWARM = "Our scenario", "Simulated crowd"

st.title("Crowd simulation")
st.badge("For comparison only. Experimental, not tested against real events, not used in the recommendation.",
         icon=":material/science:", color="blue")
say(f"We gave the {s['scenario']} crisis to a crowd of AI investors (MiroFish): pension funds, retail savers, bond managers, "
    "traders and cautious holders. See how their reaction compares with the scenario the team designed.")

mean = s["mean_loss"]
with st.container(horizontal=True):
    st.metric(TEAM, f"−{money(team['loss'] * nav)}", pct(team["loss"]), delta_color="off", delta_arrow="off", border=True)
    st.metric(SWARM, f"−{money(mean * nav)}", f"average of {len(runs)} runs · {pct(mean)}" if len(runs) > 1 else pct(mean),
              delta_color="off", delta_arrow="off", border=True,
              help=f"Lowest run {pct(s['min_loss'])}, highest {pct(s['max_loss'])}." if len(runs) > 1 else None)
    st.metric("Difference", money((mean - team["loss"]) * nav, signed=True), "crowd against ours", delta_color="off",
              delta_arrow="off", border=True, help=f"The crisis budget is {pct(budget, 0)} ({money(budget * nav)}).")

choice = st.selectbox("Run", [r["run"].replace("_", " ").capitalize() for r in runs]) if len(runs) > 1 else None
r = runs[[x["run"].replace("_", " ").capitalize() for x in runs].index(choice)] if choice else runs[0]

funds = sorted(set(team["parts"]) | set(r["parts"]), key=lambda f: -team["parts"].get(f, 0.0))
d = pd.DataFrame([{"fund": f, "who": who, "loss": src.get(f, 0.0) * nav} for f in funds
                  for who, src in ((TEAM, team["parts"]), (SWARM, r["parts"]))])
st.altair_chart(alt.Chart(d).mark_bar(height=13, cornerRadiusEnd=3).encode(
    y=alt.Y("fund:N", sort=funds, title=None, axis=alt.Axis(labelFontSize=13)), yOffset=alt.YOffset("who:N", sort=[TEAM, SWARM]),
    x=alt.X("loss:Q", title="Share of the loss (USD)", axis=alt.Axis(format="$~s")),
    color=alt.Color("who:N", sort=[TEAM, SWARM], scale=alt.Scale(domain=[TEAM, SWARM], range=[GREY, ACCENT]),
                    legend=alt.Legend(title=None, orient="bottom")),
    tooltip=["fund:N", "who:N", alt.Tooltip("loss:Q", format="$,.0f")]).properties(height=alt.Step(17)),
    alt="Loss by fund, our scenario against the simulated crowd")

ROWS = [("10-year yield", "d_yield10_bp", lambda v: f"{v:+.0f} bp"), ("Oil", "dln_oil", lambda v: f"{np.expm1(v):+.0%}"),
        ("VIX", "d_vix", lambda v: f"{v:+.0f} points"), ("Dollar", "dln_usd", lambda v: f"{np.expm1(v):+.0%}"),
        ("Credit spread", "d_credit_bp", lambda v: f"{v:+.0f} bp")]
left, right = st.columns(2, gap="large")
with left:
    st.subheader("The market moves")
    st.table(pd.DataFrame({"Move": [x[0] for x in ROWS], TEAM: [f(team["shock"][k]) for _, k, f in ROWS],
                           SWARM: [f(r["shock"][k]) for _, k, f in ROWS]}).set_index("Move"))
with right:
    st.subheader("What the crowd did")
    say(r["summary"])
    b = r["behaviour"]
    st.table(pd.DataFrame({"Score, 0 to 3": {"Panic selling": b["panic_selling"], "Herding": b["herding"], "Contagion": b["contagion_breadth"],
                                             "Disagreement": b["investor_disagreement"]}}))
    st.caption(f"Money fled to: {', '.join(b['flight_to_safety']) or 'nowhere in particular'} · lasted: {b['duration']}")
if r["mechanisms"]:
    with st.expander("How the panic spread", icon=":material/hub:"):
        st.markdown("\n".join(f"- {m}" for m in r["mechanisms"]))
explain("The AI investors react and describe what happens; they never set a number. Their direction and strength for each market "
        "move pick a size from market history. Those moves then go through the same stress test as our scenario, with the same "
        "weights and the same panic day on bonds, so the only difference is the moves themselves.")
