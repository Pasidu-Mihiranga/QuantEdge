"""The portfolio: compare equity shares (interactive), and how the strategy did since 2008 (booklet item 2)."""

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from components.ui import artifact, explain, money, need_numbers, pct, say

n = need_numbers()
nav, eq, req = n["nav_usd"], n["advised_equity"], n["objective"]["required_return"]
fr, wts, perf = artifact("decision_frontier.parquet"), artifact("decision_weights.parquet"), artifact("decision_performance.parquet")
ACCENT, GREY = "#1F5FAE", "#A3ABB5"
NAMES = {"SPY": "US stocks", "EFA": "Developed-market stocks", "EEM": "Emerging-market stocks", "AGG": "US bonds",
         "GLD": "Gold", "XLE": "Energy stocks", "XLK": "Technology stocks"}

st.title("The portfolio")
say("Pick an equity share to see the portfolio the rule would build, what it is expected to earn and what a crisis would cost. "
    f"The recommendation is **{eq:.0%}**.")
x = st.select_slider("Equity share", options=list(fr.index), value=eq, format_func=lambda v: f"{v:.0%}", key="pf_x")
r = fr.loc[x]
ok_lim, ok_obj = bool(r.within_limits), bool(r.meets_objective)
with st.container(horizontal=True):
    st.metric("Expected return a year", pct(r.forward_return, 2), f"{money((r.forward_return - req) * nav, signed=True)} vs objective",
              delta_color="off", delta_arrow="off", border=True, help="Forward-looking: today's yields plus a 4.5% equity premium, after fees and taxes.")
    st.metric("Worst crisis", f"−{money(r.d2_loss * nav)}", f"{pct(r.d2_loss)} · budget 25%", delta_color="off", delta_arrow="off",
              border=True, help="The worse of the historical crisis replays and our stagflation scenario, with these weights.")
    st.metric("Income a year", money(r.income_yield * nav), f"{pct(r.income_yield, 2)} of the fund", delta_color="off",
              delta_arrow="off", border=True, help="Dividends and interest after withholding tax; the fund spends 3% a year.")
with st.container(horizontal=True):
    st.badge("Inside every risk limit" if ok_lim else "Breaks the crisis budget", color="green" if ok_lim else "red",
             icon=":material/shield:" if ok_lim else ":material/error:")
    st.badge("Meets the objective" if ok_obj else "Misses the objective", color="green" if ok_obj else "orange",
             icon=":material/flag:" if ok_obj else ":material/remove:")
    if abs(x - eq) < 1e-9:
        st.badge("Recommended", color="blue", icon=":material/verified:")

w = wts.loc[x].loc[lambda s: s > 1e-4].sort_values(ascending=False)
df = pd.DataFrame({"fund": [f"{NAMES[t]} ({t})" for t in w.index], "weight": w.values,
                   "label": [f"{v:.1%} · {money(v * nav)}" for v in w.values]})
base = alt.Chart(df).encode(y=alt.Y("fund:N", sort=None, title=None, axis=alt.Axis(labelLimit=300, labelFontSize=13)),
                            x=alt.X("weight:Q", axis=None, scale=alt.Scale(domain=[0, 1])))
st.altair_chart((base.mark_bar(color=ACCENT if abs(x - eq) < 1e-9 else GREY, cornerRadiusEnd=4, height=24)
                 + base.mark_text(align="left", dx=6).encode(text="label:N")).properties(height=46 * len(df) + 10),
                alt=f"Weights at {x:.0%} equity")
explain("For each equity share the rule builds the least-risky mix of the seven funds (estimated on the last three years, "
        "within the caps: bonds up to 65%, energy, technology and emerging markets up to 10% each). The rule then recommends "
        "the lowest equity share that meets the objective inside every risk limit. Below 35% the return falls short; above "
        "it the crisis loss breaks the 25% budget.")

st.subheader("How the recommended strategy did since 2008")
show = st.segmented_control("Show", ["Growth of the fund", "Falls from the peak"], default="Growth of the fund", required=True,
                            label_visibility="collapsed", key="pf_hist")
LABEL = {"Frontier 35% equity": "Recommended (35% equity)", "60/40 benchmark": "60/40 stocks/bonds (outside our limits)"}
wealth = (1 + perf.fillna(0)).cumprod()
series = wealth * nav if show == "Growth of the fund" else wealth / wealth.cummax() - 1
h = series.rename(columns=LABEL).reset_index().melt(series.index.name or "index", var_name="portfolio", value_name="value")
h = h.rename(columns={h.columns[0]: "date"})
fmt = "$~s" if show == "Growth of the fund" else ".0%"
st.altair_chart(alt.Chart(h).mark_line(strokeWidth=1.6).encode(
    x=alt.X("date:T", title=None), y=alt.Y("value:Q", title="Value of USD 10M (Jan 2008)" if show == "Growth of the fund" else "Fall from the previous peak",
                                           axis=alt.Axis(format=fmt)),
    color=alt.Color("portfolio:N", scale=alt.Scale(domain=list(LABEL.values()), range=[ACCENT, GREY]),
                    legend=alt.Legend(title=None, orient="bottom", labelLimit=400)),
    tooltip=[alt.Tooltip("date:T"), "portfolio:N", alt.Tooltip("value:Q", format="$,.0f" if fmt == "$~s" else ".1%")]).properties(height=300),
    alt="History of the recommended strategy and the 60/40 benchmark")
r_ = perf.dropna()
stats = {LABEL[c]: {"Return a year": pct(float((1 + r_[c]).prod() ** (252 / len(r_)) - 1)),
                    "Volatility": pct(float(r_[c].std() * np.sqrt(252))),
                    "Worst fall": pct(float(((1 + r_[c]).cumprod() / (1 + r_[c]).cumprod().cummax() - 1).min()))} for c in perf.columns}
st.dataframe(pd.DataFrame(stats), alt="Return, volatility and worst fall since 2008")
explain("Walk-forward: every quarter the weights were chosen using only data available then, and trading costs were paid. "
        "The 60/40 mix earned more because it held 60% in US stocks during an exceptional decade for them, but it breaks the "
        "committee's limits (a 33% crisis loss) and is shown only as a reference. History is not a forecast.")
