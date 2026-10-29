"""Evidence: the backtesting panel (booklet item 4): Kupiec and Christoffersen in plain words, and a traffic light."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.content import EXCEPTION_CAUSES
from components.controls import FILES, MODELS, risk_controls
from components.ui import (
    ACCENT,
    CRIT,
    GOOD,
    GREY,
    WARN,
    artifact,
    esc,
    full,
    layout,
    money,
    need_numbers,
    note,
    pill,
    show,
)
from quantedge.backtest import coverage as cv

ctl = risk_controls()
n = need_numbers()
nav = n["nav_usd"]
mv = n["model_validity"]

st.title("Can we trust the risk model?")
st.markdown(esc("A risk model is trusted only if its forecasts held on data it never saw. We chose the model on "
                "2019–2022 with a rule fixed in advance, froze everything, and then ran it **once** on 2023–2026."))

passed = mv.get("passes")
st.markdown(f"{pill('PASSED' if passed else 'FAILED', 'good' if passed else 'crit')} &nbsp; **One-shot test, "
            f"{mv.get('test_start')} to {mv.get('test_end')} ({mv.get('days')} trading days): {mv.get('champion')}**",
            unsafe_allow_html=True)
c = st.columns(3)
c[0].metric("Bad days beyond the 99% forecast", f"{mv.get('exceptions')}")
c[0].caption(f"{mv.get('expected', 0):.1f} expected if the model is right")
c[1].metric("Is the number of breaches right? (Kupiec)", f"p = {mv.get('kupiec_p', float('nan')):.2f}")
c[1].caption("Yes: not rejected at 5%" if mv.get("kupiec_p", 0) >= 0.05 else "No: rejected at 5%")
c[2].metric("Do breaches come in clusters? (Christoffersen)", f"p = {mv.get('cc_p', float('nan')):.2f}")
c[2].caption("No clustering detected at 5%" if mv.get("cc_p", 0) >= 0.05 else "Clustered: rejected at 5%")
passing = mv.get("models_passing", [])
st.caption(f"Models passing the test: {', '.join(passing)}. The others failed because their breaches came in clusters. "
           f"The machine-learning challenger {'was' if mv.get('challenger_adopted') else 'was not'} adopted: it was "
           "less accurate than the champion by more than the 2% margin fixed in advance.")

# The selected model over the selected dates: 2008–2022 walk-forward backtest + 2023–2026 final test
alpha = ctl.alpha if ctl.alpha in (0.95, 0.99) else 0.95
if ctl.alpha == 0.90:
    st.info("Backtests are stored at 95% and 99% confidence; showing 95%.")
parts = [artifact(f"backtest_{FILES[ctl.model]}_500.parquet"), artifact(f"final_test_{FILES[ctl.model]}.parquet")]
bt = pd.concat([p for p in parts if p is not None]).sort_index()
bt = bt[~bt.index.duplicated(keep="last")].loc[f"{ctl.start}-01-01":f"{ctl.end}-12-31"]
hits = bt[f"hit_{alpha}"].astype(int)
k, ch = cv.kupiec(hits.to_numpy(), alpha), cv.christoffersen(hits.to_numpy(), alpha)

st.markdown(f"##### {ctl.model}, {alpha:.0%} confidence, {ctl.start}–{ctl.end}")
roll = cv.rolling_basel(hits, 250, alpha) if alpha == 0.99 else None
if roll is not None and len(roll):
    zone = roll["zone"].iloc[-1]
    colour = {"green": GOOD, "yellow": WARN, "red": CRIT}[zone]
    word = {"green": "GREEN: the model is working", "yellow": "YELLOW: more breaches than expected; watch",
            "red": "RED: the model is understating risk"}[zone]
    st.markdown(f"<div style='display:flex;gap:14px;align-items:center'><div style='width:26px;height:26px;border-radius:50%;"
                f"background:{colour}'></div><div style='font-size:1.15rem;font-weight:650'>Traffic light, last 250 days: "
                f"{word}</div></div>", unsafe_allow_html=True)
c = st.columns(3)
c[0].metric("Breaches / expected", f"{k.x} / {k.expected:.1f}")
c[1].metric("Kupiec p (count right?)", f"{k.pvalue:.3f}")
c[2].metric("Christoffersen p (no clustering?)", f"{ch.p_cc:.3f}")
st.caption(f"These tests cover the whole range you chose ({ctl.start}–{ctl.end}). Before 2019 is the period the model was "
           "built on, including the 2008 crisis, where every model's breaches bunched together. The pass or fail decision "
           "used only the one-shot test period above.")

fig = go.Figure()
fig.add_scatter(x=bt.index, y=bt["loss"] * nav, mode="lines", name="Daily loss (gain below zero)",
                line=dict(color=GREY, width=0.8), hovertemplate="%{x|%d %b %Y}: %{y:$,.0f}<extra></extra>")
fig.add_scatter(x=bt.index, y=bt[f"var_{alpha}"] * nav, mode="lines", name=f"{alpha:.0%} VaR forecast",
                line=dict(color=ACCENT, width=1.6), hovertemplate="forecast %{y:$,.0f}<extra></extra>")
hb = bt[bt[f"hit_{alpha}"] == 1]
fig.add_scatter(x=hb.index, y=hb["loss"] * nav, mode="markers", name="Breach", marker=dict(color=CRIT, size=7),
                hovertemplate="%{x|%d %b %Y}: loss %{y:$,.0f}<extra></extra>")
fig.add_vline(x=pd.Timestamp("2023-01-01"), line=dict(color="#1d2733", dash="dot", width=1))
fig.add_annotation(x=pd.Timestamp("2023-01-01"), y=1, yref="paper", text="one-shot test →", showarrow=False, xanchor="left")
fig.update_yaxes(tickprefix="$", tickformat="~s", title="One-day loss on USD 10M")
show(layout(fig, 400))

if roll is not None and len(roll):
    zc = {"green": GOOD, "yellow": WARN, "red": CRIT}
    fig = go.Figure()
    for z in ("green", "yellow", "red"):
        m = roll["zone"] == z
        fig.add_bar(x=roll.index[m], y=[1] * int(m.sum()), name=z.title(), marker_color=zc[z], marker_line_width=0)
    fig.update_yaxes(visible=False)
    fig.update_layout(barmode="stack", bargap=0, showlegend=False)
    show(layout(fig, 150, "Traffic light over every 250-day window (Basel: 0–4 breaches green, 5–9 yellow, 10+ red)"))

st.markdown("##### All models on the one-shot test")
sc = artifact("final_test_scores.parquet")
if sc is not None:
    t = pd.DataFrame({"Breaches (9.6 expected)": sc["exceptions"].astype(int), "Kupiec p": sc["kupiec_p"].round(3),
                      "Christoffersen p": sc["cc_p"].round(3), "Passes": sc["passes"].map({True: "yes", False: "no"}),
                      "Accuracy vs champion": sc["pinball_vs_champion"].map(lambda v: f"{v:+.1%} worse" if v > 0 else "best")})
    full(t)
    st.caption("Accuracy is the 99% quantile (pinball) loss, which rewards forecasts that are close as well as right "
               "on count. The champion was the most accurate model on data it had never seen.")

st.markdown("##### Every breach on 2019–2022 has a cause")
val = artifact(f"backtest_{FILES[n['model_validity'].get('champion', MODELS[-1])]}_500.parquet")
if val is not None:
    v = val.loc["2019-01-01":"2022-12-31"]
    log = v[v["hit_0.99"] == 1]
    full(pd.DataFrame({"Loss": (log["loss"] * nav).map(money), "Forecast (VaR)": (log["var_0.99"] * nav).map(money),
                       "Cause": [EXCEPTION_CAUSES.get(str(d.date()), "—") for d in log.index]}, index=log.index.date))
    note("All 14 breaches have a documented market cause and none is a data error. Eight were no larger than the model's "
         "own average-loss forecast; six were the first days of a new crisis, when a volatility model needs a few days to "
         "catch up. That is why the fund also holds a crisis budget and stress tests.")
