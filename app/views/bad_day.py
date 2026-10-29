"""Evidence: the risk dashboard (booklet item 3): VaR, ES and the EVT tail estimate side by side."""

import plotly.graph_objects as go
import streamlit as st

from components.controls import risk_controls
from components.ui import (
    ACCENT,
    GREY,
    TAIL,
    artifact,
    esc,
    layout,
    money,
    need_numbers,
    note,
    pct,
    per_year,
    show,
)

ctl = risk_controls(dates=False)
n = need_numbers()
nav = n["nav_usd"]
snap = artifact("decision_risk_snapshot.parquet")
rd = n["risk_day"]

st.title("How bad can a bad day get?")
st.markdown(esc(f"Three measures of a bad day for the recommended portfolio, in dollars, at **{ctl.alpha:.0%}** confidence "
                f"with the **{ctl.model}** model. Fitted on the last 500 trading days ({rd['window_start']} to "
                f"{rd['window_end']})."))

s = snap.set_index(["model", "alpha"])
var_, es_ = float(s.loc[(ctl.model, ctl.alpha), "var"]), float(s.loc[(ctl.model, ctl.alpha), "es"])
evt = float(s.loc[("EVT", ctl.alpha), "es"])
c1, c2, c3 = st.columns(3)
for col, label, v in ((c1, f"VaR: the loss exceeded on {per_year(ctl.alpha).split(' (')[0]}", var_),
                      (c2, "ES: the average loss on those days", es_), (c3, "EVT: the tail estimated from extremes only", evt)):
    col.metric(label, money(v * nav))
    col.caption(f"{pct(v, 2)} of the endowment")

fig = go.Figure(go.Bar(x=["VaR<br>threshold", "ES<br>average beyond VaR", "EVT tail<br>average beyond VaR"],
                       y=[var_ * nav, es_ * nav, evt * nav], marker_color=[TAIL["VaR"], TAIL["ES"], TAIL["EVT"]],
                       text=[money(var_ * nav), f"{money(es_ * nav)}<br>({es_ / var_ - 1:+.0%} vs VaR)",
                             f"{money(evt * nav)}<br>({evt / var_ - 1:+.0%} vs VaR)"], textposition="outside",
                       hovertemplate="%{x}: %{y:$,.0f}<extra></extra>"))
fig.update_yaxes(tickprefix="$", tickformat="~s", range=[0, max(var_, es_, evt) * nav * 1.3], title="One-day loss")
show(layout(fig, 360, f"The gap between the three measures, {ctl.alpha:.0%} confidence, one day"))
st.markdown(esc(f"**How to read it.** On {per_year(ctl.alpha)}, the fund should expect to lose more than "
                f"**{money(var_ * nav)}**. VaR says nothing about how much more; ES does: on those days the average loss "
                f"is **{money(es_ * nav)}**. EVT fits only the extreme losses of the history, so it is the most cautious "
                f"view of the far tail: **{money(evt * nav)}**."))

note(f"<b>Today versus through the cycle.</b> These figures use the last two years, a relatively calm period, and the "
     f"chosen model reacts to current volatility. The risk limit is set on 2004–2018 data, which include 2008: there the "
     f"average 1-in-100-day loss of the same portfolio is {money(n['risk']['es99_ttc'] * nav)} against a limit of "
     f"{money(n['limits']['es99_max'] * nav)}. The model's figure is a warning light (decision D9); the through-the-cycle "
     f"figure is the limit.")

c1, c2 = st.columns(2)
with c1:
    st.markdown("##### Over ten trading days")
    st.markdown(esc(f"Simulated from the volatility model's own paths (99%): the fund loses more than "
                    f"**{money(rd['var99_10d'] * nav)}** over ten days once in a hundred ten-day periods, and "
                    f"**{money(rd['es99_10d'] * nav)}** on average when it does."))
with c2:
    st.markdown("##### Once in a decade")
    st.markdown(esc(f"The worst single day expected about once in ten years: **{money(rd['once_in_10y_champion'] * nav)}** "
                    f"with the volatility model as of today, and up to **{money(rd['once_in_10y_evt'] * nav)}** from the "
                    "long-run tail (EVT). The gap is the honest uncertainty about rare events."))

st.markdown("##### Every model at the same confidence")
t = snap[snap.alpha == ctl.alpha].set_index("model")[["var", "es"]] * nav
fig = go.Figure()
for m, r in t.sort_values("es").iterrows():
    colour = ACCENT if m == ctl.model else GREY
    fig.add_scatter(x=[r["var"], r["es"]], y=[m, m], mode="lines+markers", line=dict(color=colour, width=2),
                    marker=dict(size=[8, 11], color=colour), showlegend=False,
                    hovertemplate=f"{m}: VaR {money(r['var'])}, ES {money(r['es'])}<extra></extra>")
fig.update_xaxes(tickprefix="$", tickformat="~s", title="One-day loss: left dot VaR, right dot ES")
show(layout(fig, 380))
st.caption("Models that ignore changing volatility (Historical, Normal, Student-t) or fat tails (Normal) give different "
           "answers; the selected model is in blue. Which one to trust is settled by the backtests on the next page.")
