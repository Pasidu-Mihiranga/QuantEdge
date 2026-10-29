"""What can go wrong: every crisis with the recommended weights, against one budget, and a scenario to try."""

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from components.ui import artifact, explain, money, need_numbers, pct, say
from quantedge.config import load_config
from quantedge.data.partition import load_returns
from quantedge.stress.factor import FACTORS, scenario_loss
from quantedge.stress.reverse import most_likely_breach, stressed_sigma

n = need_numbers()
cfg = load_config()
nav, budget = n["nav_usd"], n["limits"]["crisis_budget"]
w = pd.Series(n["weights"])
hyp = cfg.stress["hypothetical"]
ACCENT, GREY, CRIT = "#1F5FAE", "#A3ABB5", "#B42318"

KIND = {"GFC 2008": ("Deflationary crash", "Stocks fell about 55%; Treasuries rallied, so bonds cushioned the fall."),
        "COVID crash 2020": ("Liquidity panic", "Everything was sold for cash for a few days, bonds included; oil collapsed."),
        "Rate shock 2022": ("Inflation shock", "Stocks and bonds fell together, so the bond hedge failed."),
        "2025 tariff shock (pre-registered)": ("'Sell America'", "US stocks, Treasuries and the dollar fell together."),
        "2026 Hormuz shock (pre-registered)": ("Oil shock", "Oil and yields rose; the energy holding gained."),
        f"{hyp['name']} (scenario)": ("Our stagflation scenario", "Yields +250 bp, oil +40%, VIX +25, dollar +8%, credit +150 bp, "
                                     "plus one panic day on AGG.")}
cm = pd.Series(n["crisis_map"]).sort_values(ascending=False)

st.title("What can go wrong?")
say(f"The portfolio is built to lose **less than {pct(budget, 0)} ({money(budget * nav)})** in every kind of crisis we can "
    "measure, while still paying the scholarships.")

with st.container(horizontal=True):
    st.metric("Worst crisis on record", f"−{money(cm.max() * nav)}", cm.idxmax().replace(" (scenario)", ""), delta_color="off",
              delta_arrow="off", border=True, help="The largest peak-to-trough loss of today's portfolio in any crisis replay.")
    st.metric("Crises inside the budget", f"{int((cm <= budget).sum())} of {len(cm)}", f"budget {money(budget * nav)}",
              delta_color="off", delta_arrow="off", border=True,
              help="Historical crises, two recent episodes fixed before we looked at them, and our own scenario.")
    st.metric("Our stagflation scenario", f"−{money(n['scenario']['loss'] * nav)}", "the crisis bonds can't hedge",
              delta_color="off", delta_arrow="off", border=True,
              help="A crisis we designed in which stocks and bonds fall together (decision D5).")

df = pd.DataFrame({"crisis": [k.replace(" (pre-registered)", " ·").replace(" (scenario)", "") for k in cm.index],
                   "kind": [KIND[k][0] for k in cm.index], "loss": cm.values * nav,
                   "label": [f"−{money(v * nav)} ({pct(v)})" for v in cm.values],
                   "type": ["our scenario" if "scenario" in k else "happened" for k in cm.index]})
bars = alt.Chart(df).mark_bar(cornerRadiusEnd=4, height=24).encode(
    y=alt.Y("crisis:N", sort=None, title=None, axis=alt.Axis(labelLimit=260, labelFontSize=13)),
    x=alt.X("loss:Q", title="Worst loss during the episode (USD)", scale=alt.Scale(domain=[0, budget * nav * 1.22]),
            axis=alt.Axis(format="$~s", tickCount=6)),
    color=alt.Color("type:N", scale=alt.Scale(domain=["happened", "our scenario"], range=[GREY, ACCENT]),
                    legend=alt.Legend(title=None, orient="bottom")),
    tooltip=["crisis:N", "kind:N", alt.Tooltip("loss:Q", format="$,.0f")])
text = alt.Chart(df).mark_text(align="left", dx=6).encode(y=alt.Y("crisis:N", sort=None), x="loss:Q", text="label:N")
rule = alt.Chart(pd.DataFrame({"x": [budget * nav]})).mark_rule(color=CRIT, strokeWidth=2).encode(x="x:Q")
st.altair_chart((bars + text + rule).properties(height=330), alt="Every crisis against the 25% budget")
explain("Each bar replays a real crisis day by day with **today's** weights, rebalanced to target every day, which is the "
        "cautious way to measure it. The red line is the 25% budget the committee set. A dot after a name (·) marks the two "
        "2025–26 episodes, which we fixed *before* looking at the data. The blue bar is our own scenario. Bonds help in a "
        "crash (2008) but fall with stocks in an inflation shock (2022, our scenario), so the limit is a loss budget, not a hedge.")

st.subheader("Try a crisis yourself", divider=False)
say("Move the market shocks and watch the loss. They start at our agreed scenario.")
betas = artifact("decision_scenario_betas.parquet")
base = hyp["shock"]
c = st.columns(5)
shock = {"d_yield10_bp": c[0].slider("10-year yield (bp)", -150, 400, int(base["d_yield10_bp"]), 10, key="s_y"),
         "dln_oil": float(np.log1p(c[1].slider("Oil (%)", -60, 100, round((np.exp(base["dln_oil"]) - 1) * 100), 5, key="s_o") / 100)),
         "d_vix": c[2].slider("VIX (points)", -10, 60, int(base["d_vix"]), 1, key="s_v"),
         "dln_usd": float(np.log1p(c[3].slider("Dollar (%)", -15, 20, round((np.exp(base["dln_usd"]) - 1) * 100), 1, key="s_d") / 100)),
         "d_credit_bp": c[4].slider("Credit spread (bp)", -50, 500, int(base["d_credit_bp"]), 10, key="s_c")}
liq = st.toggle("Add a panic day on bonds (AGG −5%)", value=True, key="s_l")
loss = scenario_loss(betas, shock, w, hyp.get("liquidity_day") if liq else None)
inside = loss <= budget
with st.container(horizontal=True, vertical_alignment="center"):
    st.metric("Portfolio loss", f"−{money(loss * nav)}", f"{pct(loss)} of the endowment", delta_color="off", delta_arrow="off",
              border=True)
    st.badge("Inside the budget" if inside else "Breaks the budget", icon=":material/check_circle:" if inside else ":material/error:",
             color="green" if inside else "red")
etf = pd.Series(np.expm1((betas[FACTORS] @ pd.Series(shock).reindex(FACTORS)).to_numpy()), index=betas.index)
contrib = (etf * w.reindex(etf.index).fillna(0)).loc[lambda s: w.reindex(s.index).fillna(0) > 1e-4]
cd = pd.DataFrame({"fund": contrib.index, "contribution": contrib.values * nav})
st.altair_chart(alt.Chart(cd).mark_bar(cornerRadiusEnd=3).encode(
    x=alt.X("contribution:Q", title="Contribution to the loss (USD)", axis=alt.Axis(format="$~s", tickCount=6)),
    y=alt.Y("fund:N", sort="x", title=None),
    color=alt.condition("datum.contribution < 0", alt.value(CRIT), alt.value("#0D7A2F")),
    tooltip=["fund:N", alt.Tooltip("contribution:Q", format="$,.0f")]).properties(height=170),
    alt="Where the scenario loss comes from")
explain("Each fund's move comes from how it reacted to these market factors in past stress periods (weekly data since 2004, "
        "re-estimated on data to the decision date). The bars show which holdings lose or gain in your scenario. The panic "
        "day adds the kind of one-day bond-fund discount seen on 10 October 2008.")

with st.expander("Every crisis in detail", icon=":material/table:"):
    years = {k: (pd.Timestamp(b) - pd.Timestamp(a)).days / 365.25
             for k, (a, b) in {**cfg.stress["historical"], **{f"{k} (pre-registered)": v for k, v in cfg.stress.get("preregistered", {}).items()}}.items()}
    rows = [{"Episode": k, "Kind": KIND[k][0], "Loss": f"−{money(v * nav)}",
             "Endowment at the bottom, after scholarships": money(nav * (1 - v) - 0.03 * nav * years.get(k, 0.75)),
             "What happened": KIND[k][1]} for k, v in cm.items()]
    st.table(pd.DataFrame(rows).set_index("Episode"))

with st.expander("What would it take to lose 25%? (reverse stress)", icon=":material/undo:"):
    returns = load_returns("all", cfg).loc[lambda r: r.index < pd.Timestamp(n["decision_date"])]
    h = int(cfg.stress["reverse"]["horizon_days"])
    calm = most_likely_breach(returns.cov(), w, budget, h)
    crisis = most_likely_breach(stressed_sigma(returns, cfg.stress["historical"]), w, budget, h)
    st.dataframe(pd.DataFrame({"normal correlations": calm.x_star, "crisis correlations": crisis.x_star}).style.format("{:+.1%}"),
                 alt="Most plausible fund moves that would cost 25%")
    say(f"The most plausible way to lose {pct(budget, 0)} in {h} trading days is a broad equity crash with bonds not helping: "
        f"about a 1-in-{calm.years_between:,.0f}-year event with normal correlations, 1-in-{crisis.years_between:,.0f} with "
        "crisis correlations (a normal model, so optimistic; the comparison is the point).")
