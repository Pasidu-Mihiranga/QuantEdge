"""Decision page 2: what can go wrong. Every crisis with the recommended weights, against one budget."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.ui import (
    ACCENT,
    CRIT,
    GREY,
    MUTED,
    artifact,
    esc,
    layout,
    money,
    need_numbers,
    note,
    pct,
    show,
)
from quantedge.config import load_config
from quantedge.data.partition import load_returns
from quantedge.stress.factor import FACTORS, scenario_loss
from quantedge.stress.reverse import most_likely_breach, stressed_sigma

n = need_numbers()
cfg = load_config()
nav, budget = n["nav_usd"], n["limits"]["crisis_budget"]
w = pd.Series(n["weights"])

st.title("What can go wrong?")
st.markdown(esc(f"The portfolio is not built to win any one crisis. It is built to lose **less than {pct(budget, 0)} "
                f"({money(budget * nav)})** in every kind of crisis we can measure, and still pay the scholarships."))

KIND = {
    "GFC 2008": ("Deflationary crash", "Stocks fell about 55%; Treasuries rallied, so AGG cushioned the fall."),
    "COVID crash 2020": ("Liquidity panic", "Everything was sold for cash for a few days, bonds included; oil collapsed, hurting energy."),
    "Rate shock 2022": ("Inflation and rate shock", "Stocks and bonds fell together, so the bond hedge failed."),
    "2025 tariff shock (pre-registered)": ("'Sell America'", "US stocks, long Treasuries and the dollar fell together; fixed before the test."),
    "2026 Hormuz shock (pre-registered)": ("Oil supply shock", "Oil and yields rose; the energy holding gained. Fixed before the test."),
}
hyp_name = cfg.stress["hypothetical"]["name"]
KIND[f"{hyp_name} (scenario)"] = ("Our stagflation scenario", "10-year yield +250 bp, oil +40%, VIX +25, dollar +8%, credit +150 bp over three quarters, plus a panic day on AGG.")

windows = {**cfg.stress["historical"], **{f"{k} (pre-registered)": v for k, v in cfg.stress.get("preregistered", {}).items()}}
cm = pd.Series(n["crisis_map"]).sort_values()
years = {k: ((pd.Timestamp(b) - pd.Timestamp(a)).days / 365.25 if k in windows else 0.75)
         for k, (a, b) in {**windows, f"{hyp_name} (scenario)": ("2027-01-01", "2027-10-01")}.items()}

fig = go.Figure(go.Bar(
    x=cm.values * nav, y=[f"{k.replace(' (pre-registered)', '').replace(' (scenario)', '')}<br><span style='font-size:11px;color:{MUTED}'>{KIND.get(k, ('', ''))[0]}</span>" for k in cm.index],
    orientation="h", marker_color=[ACCENT if "scenario" in k else GREY for k in cm.index],
    text=[f"−{money(v * nav)} ({pct(v)})" for v in cm.values], textposition="outside",
    hovertemplate="%{y}<br>loss %{x:$,.0f}<extra></extra>"))
fig.add_vline(x=budget * nav, line=dict(color=CRIT, width=2), annotation_text=f"crisis budget {money(budget * nav)}",
              annotation_position="top")
fig.update_xaxes(range=[0, budget * nav * 1.25], tickprefix="$", tickformat="~s", title="Worst loss during the episode")
show(layout(fig, 420, "Every crisis, with the recommended weights held through it"))
st.caption("Historical crises replay the actual daily returns of each fund with today's weights, rebalanced to target "
           "every day (the cautious convention used for the crisis budget). Pre-registered episodes were chosen before "
           "the 2023–2026 data were looked at. The scenario is our own design (decision D5), mapped to the funds through "
           "factor sensitivities estimated in past stress periods.")

rows = []
for k in cm.index[::-1]:
    loss = cm[k]
    spend = 0.03 * nav * years.get(k, 0.0)
    rows.append({"Episode": k, "Kind of crisis": KIND.get(k, ("", ""))[0], "Loss": f"−\u2060{money(loss * nav)}",
                 "Endowment at the bottom, after scholarships paid": money(nav * (1 - loss) - spend),
                 "Inside the budget": "yes" if loss <= budget + 1e-9 else "NO", "What happened": KIND.get(k, ("", ""))[1]})
st.table(pd.DataFrame(rows).set_index("Episode"))
note("Two different crises threaten this fund: a deflationary crash (where bonds help) and an inflation shock (where "
     "bonds fall with stocks). No single hedge protects in both, which is why the limit is a loss budget, not a hedge.")

st.markdown("##### Build your own scenario")
betas = artifact("decision_scenario_betas.parquet")
if betas is not None:
    base = cfg.stress["hypothetical"]["shock"]
    c = st.columns(5)
    shock = {"d_yield10_bp": c[0].slider("10-year yield (bp)", -150, 400, int(base["d_yield10_bp"]), 10),
             "dln_oil": float(np.log1p(c[1].slider("Oil (%)", -60, 100, round((np.exp(base["dln_oil"]) - 1) * 100), 5) / 100)),
             "d_vix": c[2].slider("VIX (points)", -10, 60, int(base["d_vix"]), 1),
             "dln_usd": float(np.log1p(c[3].slider("Dollar (%)", -15, 20, round((np.exp(base["dln_usd"]) - 1) * 100), 1) / 100)),
             "d_credit_bp": c[4].slider("Credit spread (bp)", -50, 500, int(base["d_credit_bp"]), 10)}
    liq = st.toggle("Add one panic day on AGG (−5%)", value=True)
    loss = scenario_loss(betas, shock, w, cfg.stress["hypothetical"].get("liquidity_day") if liq else None)
    a, b = st.columns([1, 2])
    a.metric("Portfolio loss over the episode", f"−{money(loss * nav)}")
    a.caption(f"{pct(loss)} of the endowment")
    status = "inside" if loss <= budget else "OUTSIDE"
    b.markdown(esc(f"With these moves the recommended portfolio loses **{pct(loss)}**, **{status}** the {pct(budget, 0)} "
                   f"budget. Starting values are our agreed scenario."))
    etf = pd.Series(np.expm1((betas[FACTORS] @ pd.Series(shock).reindex(FACTORS)).to_numpy()), index=betas.index)
    st.caption("Fund moves in this scenario: " + ", ".join(f"{t} {v:+.1%}" for t, v in etf.items()))

with st.expander("Reverse stress: what would it take to lose 25%?"):
    returns = load_returns("all", cfg).loc[lambda r: r.index < pd.Timestamp(n["decision_date"])]
    h = int(cfg.stress["reverse"]["horizon_days"])
    calm = most_likely_breach(returns.cov(), w, budget, h)
    crisis = most_likely_breach(stressed_sigma(returns, cfg.stress["historical"]), w, budget, h)
    st.dataframe(pd.DataFrame({"with normal correlations": calm.x_star, "with crisis correlations": crisis.x_star})
                 .style.format("{:+.1%}"), width="stretch")
    st.markdown(esc(f"The most plausible way to lose {pct(budget, 0)} in {h} trading days is shown above: a broad equity "
                    f"crash with bonds not helping. Under a normal model this is about a 1-in-{calm.years_between:,.0f}-year "
                    f"event with normal correlations, but 1-in-{crisis.years_between:,.0f} years with crisis correlations. "
                    "Normal tails understate extremes, so read these as optimistic; the comparison is the point."))
