"""Evidence: the portfolio panel (booklet item 2): weights, cumulative return and drawdown."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.ui import ACCENT, GREY, artifact, layout, money, need_numbers, pct, show

n = need_numbers()
nav = n["nav_usd"]
FOCUS, BENCH = "Frontier 35% equity", "60/40 benchmark"
LABEL = {FOCUS: "Recommended strategy (35% equity)", BENCH: "60/40 stocks/bonds (outside our limits)"}

st.title("How is the money invested?")
st.markdown("The recommended mix, how the same strategy would have done since 2008, and what the other equity shares "
            "would have meant.")

w = pd.Series(n["weights"]).loc[lambda s: s > 1e-4]
role = {"SPY": "US stocks: growth", "EFA": "Developed-market stocks: diversification", "EEM": "Emerging-market stocks",
        "AGG": "US investment-grade bonds: income and crash protection", "GLD": "Gold: inflation and crisis hedge",
        "XLE": "Energy stocks: inflation and oil-shock hedge", "XLK": "Technology stocks"}
st.markdown("##### The recommended weights")
st.dataframe(pd.DataFrame({"Weight": w.map(lambda v: f"{v:.1%}"), "Dollars": w.map(lambda v: money(v * nav)),
                           "Role": [role[t] for t in w.index]}), width="stretch")
fr = artifact("decision_frontier.parquet")
if fr is not None:
    caps = fr.loc[n["advised_equity"], "caps_binding"]
    st.caption(f"Minimum risk at {n['advised_equity']:.0%} equity under the caps, estimated on the last three years. "
               f"Caps that bind here: {caps or 'none'}. Rebalanced every quarter.")

perf = artifact("decision_performance.parquet")
if perf is not None:
    st.markdown("##### The same strategy since 2008 (walk-forward: each quarter's weights use only earlier data)")
    wealth = (1 + perf.fillna(0)).cumprod()
    dd = wealth / wealth.cummax() - 1
    c1, c2 = st.columns(2)
    with c1:
        fig = go.Figure()
        for col, colour, width in ((BENCH, GREY, 1.4), (FOCUS, ACCENT, 2.2)):
            fig.add_scatter(x=wealth.index, y=wealth[col] * nav, name=LABEL[col], line=dict(color=colour, width=width),
                            hovertemplate="%{x|%b %Y}: %{y:$,.0f}<extra></extra>")
        fig.update_yaxes(tickprefix="$", tickformat="~s", title="Value of USD 10M invested in Jan 2008")
        show(layout(fig, 360, "Cumulative return"))
    with c2:
        fig = go.Figure()
        for col, colour, width in ((BENCH, GREY, 1.4), (FOCUS, ACCENT, 2.2)):
            fig.add_scatter(x=dd.index, y=dd[col], name=LABEL[col], line=dict(color=colour, width=width),
                            hovertemplate="%{x|%b %Y}: %{y:.1%}<extra></extra>")
        fig.update_yaxes(tickformat=".0%", title="Fall from the previous peak", range=[min(dd.min().min() * 1.1, -0.05), 0.01])
        show(layout(fig, 360, "Drawdown"))
    yrs = len(perf) / 252
    stats = {}
    for col in (FOCUS, BENCH):
        r = perf[col].dropna()
        cagr = float((1 + r).prod() ** (252 / len(r)) - 1)
        yearly = (1 + r).groupby(r.index.year).prod() - 1
        stats[LABEL[col]] = {"Return a year": pct(cagr), "Volatility": pct(float(r.std() * np.sqrt(252))),
                             "Worst fall from a peak": pct(float(dd[col].min())), "Worst calendar year": f"{pct(yearly.min())} ({yearly.idxmin()})",
                             "Best calendar year": f"{pct(yearly.max())} ({yearly.idxmax()})"}
    st.dataframe(pd.DataFrame(stats), width="stretch")
    st.caption(f"{perf.index[0]:%b %Y} to {perf.index[-1]:%b %Y} ({yrs:.1f} years), after 5 bp trading costs per side. "
               "The 60/40 mix earned more because it held 60% in US stocks during an exceptional decade for them; it "
               "breaks the committee's limits (equity above 50%, SPY above 40%, a 33% crisis loss) and is shown only as "
               "a reference. History is not a forecast: the expected returns on the first page are forward-looking.")

if fr is not None:
    st.markdown("##### Every equity share we considered")
    wts = artifact("decision_weights.parquet")
    t = pd.DataFrame({"Expected return": fr["forward_return"].map(lambda v: pct(v, 2)),
                      "Worst crisis loss": fr["d2_loss"].map(pct), "Volatility": fr["vol_ttc"].map(pct),
                      "Income": fr["income_yield"].map(lambda v: pct(v, 2)),
                      "Inside every limit": fr["within_limits"].map({True: "yes", False: "no"}),
                      "Meets the objective": fr["meets_objective"].map({True: "yes", False: "no"})})
    if wts is not None:
        t = t.join(wts.map(lambda v: f"{v:.0%}" if v > 1e-4 else "—"))
    t.index = [f"{x:.0%} equity" + (" (recommended)" if abs(x - n["advised_equity"]) < 1e-9 else "") for x in t.index]
    st.dataframe(t, width="stretch", height=35 * (len(t) + 1) + 3)
    st.caption("Expected returns: today's yields plus a 4.5% equity premium, after fees and withholding tax. Crisis loss: "
               "the worse of the historical crises and our scenario, with today's weights.")
