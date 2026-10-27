"""QuantEdge 1.0: Executive summary (Home)."""

import pandas as pd
import streamlit as st

from components import charts
from components.data import config, jsonfile, parquet, require, status
from components.evidence import verdict
from components.sidebar import pct, provisional_banner, sidebar, usd

st.set_page_config(page_title="QuantEdge: Serendib Endowment", layout="wide")
ctl = sidebar()
cfg = config()
s = status()

st.title("Serendib University Endowment: Risk-Aware Portfolio")
st.caption("USD 10M conservative endowment · 7 ETFs · every number is 1-day unless stated, losses are positive")
provisional_banner()

v, info = verdict()
if not require(v, "The decision evidence"):
    st.stop()

colors = {"ACCEPT": "#2e9d57", "ADJUST RISK LIMIT": "#e3b505", "REJECT": "#c0392b"}
st.markdown(
    f"<div style='background:{colors[v.status]};color:white;padding:0.9rem 1.2rem;border-radius:8px;"
    f"font-size:1.35rem;font-weight:700'>Rule-engine outcome: {v.status}</div>", unsafe_allow_html=True)
st.caption("The rule engine summarises the evidence. The final recommendation and its wording are the team's own judgement.")
for r in v.reasons:
    st.write(f"- {r}")

ev = info["evidence"]
scale = ctl.nav
c1, c2, c3, c4 = st.columns(4)
c1.metric("Expected return (OOS, a year)", pct(ev.expected_return), f"{ev.expected_return - ev.required_return:+.2%} vs required")
c2.metric(f"99% 1-day ES ({info['champion']})", usd(ev.es99_1d * scale), pct(ev.es99_1d), delta_color="off")
c3.metric("Worst historical stress", usd(-info["worst_hist_loss"] * scale), pct(-info["worst_hist_loss"], 1), delta_color="off")
val = parquet("backtest_selection_val_500.parquet")
zone = "green" if val is not None and val.loc[info["champion"], "rolling_red"] == 0 else "check"
c4.metric("Backtest (2019–2022)", "passes" if ev.champion_valid else "fails", f"rolling Basel: {zone}", delta_color="off")

left, right = st.columns([1, 1.3])
with left:
    w = pd.Series(s.get("weights", {}))
    st.plotly_chart(charts.donut(w, f"Allocation: {s.get('focus_portfolio')}"), width="stretch")
    st.dataframe(pd.DataFrame({"weight": w.map(lambda x: f"{x:.1%}"), "USD": (w * scale).map(usd)}),
                 width="stretch")
with right:
    st.subheader("Five committee questions")
    extras = jsonfile("risk_extras.json")
    snap = parquet("risk_snapshot.parquet")
    var99 = float(snap[(snap.model == info["champion"]) & (snap.alpha == 0.99)]["var"].iloc[0])
    st.markdown(f"""
1. **How much could we lose on a bad day?** On about 1 day in 100 the model expects a loss above
   {usd(var99 * scale)} (99% VaR); on those days the average loss is {usd(ev.es99_1d * scale)} (99% ES).
2. **What about a once-in-a-decade day?** EVT puts the 1-in-10-years daily loss at about
   {usd(extras.get('return_level_10y_evt', float('nan')) * scale)}.
3. **What happens in a crisis like 2008, 2020 or 2022?** The worst replayed crisis loses {pct(-info['worst_hist_loss'], 1)}.
4. **Can we trust the risk model?** {info['champion']} passed every pre-declared backtest on 2019–2022.
5. **Does it meet the return objective?** Expected {pct(ev.expected_return)} against a required {pct(ev.required_return)}.
""")
    st.caption("Draft wording generated from the numbers; the team writes the final committee memo.")

with st.expander("All decision checks"):
    st.dataframe(pd.DataFrame([c.__dict__ for c in v.checks]), width="stretch")
