"""Risk, and how sure we are: the booklet's risk dashboard (VaR, ES, EVT side by side) and backtesting panel."""

import altair as alt
import pandas as pd
import streamlit as st

from components.content import EXCEPTION_CAUSES
from components.controls import FILES, risk_controls
from components.ui import artifact, explain, money, need_numbers, per_year, say
from quantedge.backtest import coverage as cv

ctl = risk_controls()
n = need_numbers()
nav, rd, mv = n["nav_usd"], n["risk_day"], n["model_validity"]
ACCENT, GREY, CRIT, GOOD, WARN = "#1F5FAE", "#A3ABB5", "#B42318", "#0D7A2F", "#A15C00"
TAIL = ["#9EC1EA", "#4F86C6", "#1F3F73"]

st.title("Risk, and how sure we are")
say("How much can the fund lose on a bad day, and does the risk model get that right? Change the confidence level, the "
    "model and the dates under Risk controls in the sidebar.")
view = st.segmented_control("View", ["A bad day", "Is the model right?"], default="A bad day", required=True,
                            label_visibility="collapsed", key="risk_view",
                            format_func=lambda v: {"A bad day": ":material/trending_down: A bad day",
                                                   "Is the model right?": ":material/fact_check: Is the model right?"}[v])

if view == "A bad day":
    snap = artifact("decision_risk_snapshot.parquet").set_index(["model", "alpha"])
    var_, es_ = float(snap.loc[(ctl.model, ctl.alpha), "var"]), float(snap.loc[(ctl.model, ctl.alpha), "es"])
    evt = float(snap.loc[("EVT", ctl.alpha), "es"])
    freq = per_year(ctl.alpha)
    with st.container(horizontal=True):
        st.metric("VaR: the line", f"−{money(var_ * nav)}", f"exceeded on {freq.split(' (')[0]}", delta_color="off",
                  delta_arrow="off", border=True, help=f"Value at Risk: on {freq}, the loss is worse than this. It says nothing "
                  "about how much worse.")
        st.metric("ES: beyond the line", f"−{money(es_ * nav)}", "the average loss on those days", delta_color="off",
                  delta_arrow="off", border=True, help="Expected Shortfall: the average loss on the days that cross the VaR "
                  "line. The committee's tail-risk limit uses this measure.")
        st.metric("EVT: the far tail", f"−{money(evt * nav)}", "estimated from extremes only", delta_color="off",
                  delta_arrow="off", border=True, help="Extreme Value Theory fits only the most extreme past losses, so it is "
                  "the most cautious view of rare events.")
    df = pd.DataFrame({"measure": ["VaR", "ES", "EVT"], "loss": [var_ * nav, es_ * nav, evt * nav],
                       "label": [money(var_ * nav), f"{money(es_ * nav)} ({es_ / var_ - 1:+.0%})", f"{money(evt * nav)} ({evt / var_ - 1:+.0%})"]})
    bars = alt.Chart(df).mark_bar(cornerRadiusEnd=4, size=70).encode(
        x=alt.X("measure:N", sort=None, title=None, axis=alt.Axis(labelAngle=0, labelFontSize=14)),
        y=alt.Y("loss:Q", title="One-day loss (USD)", axis=alt.Axis(format="$~s"), scale=alt.Scale(domain=[0, max(df.loss) * 1.25])),
        color=alt.Color("measure:N", scale=alt.Scale(domain=["VaR", "ES", "EVT"], range=TAIL), legend=None),
        tooltip=["measure:N", alt.Tooltip("loss:Q", format="$,.0f")])
    st.altair_chart((bars + bars.mark_text(dy=-10, fontSize=13).encode(text="label:N", color=alt.value("#1D2733"))).properties(height=300),
                    alt=f"VaR, ES and EVT at {ctl.alpha:.0%}")
    explain(f"All three use the **{ctl.model}** model on the last 500 trading days ({rd['window_start']} to {rd['window_end']}) "
            f"at **{ctl.alpha:.0%}** confidence. The percentages show how much bigger ES and EVT are than VaR: the gap is the "
            "loss VaR hides. These are today's levels; the committee's limit uses a through-the-cycle figure that includes "
            f"2008: {money(n['risk']['es99_ttc'] * nav)} on a 1-in-100 day against a limit of {money(n['limits']['es99_max'] * nav)}.")
    with st.expander("Over ten days, and once in a decade", icon=":material/calendar_month:"):
        say(f"**Ten trading days (99%):** a loss above {money(rd['var99_10d'] * nav)} once in a hundred ten-day periods; "
            f"{money(rd['es99_10d'] * nav)} on average when it happens.  \n**The worst day in ten years:** about "
            f"{money(rd['once_in_10y_champion'] * nav)} with today's volatility model, up to {money(rd['once_in_10y_evt'] * nav)} "
            "from the long-run tail. The gap is the honest uncertainty about rare events.")
    with st.expander("Compare every model", icon=":material/compare:"):
        t = snap.xs(ctl.alpha, level="alpha").reset_index()
        t["chosen"] = t["model"].eq(ctl.model)
        dots = alt.Chart(t.melt(["model", "chosen"], ["var", "es"], "measure", "loss")).mark_line(point=True).encode(
            x=alt.X("loss:Q", title="One-day loss (share of the endowment)", axis=alt.Axis(format=".1%")),
            y=alt.Y("model:N", sort=alt.EncodingSortField("loss", op="max"), title=None),
            detail="model:N", color=alt.condition("datum.chosen", alt.value(ACCENT), alt.value(GREY)),
            tooltip=["model:N", "measure:N", alt.Tooltip("loss:Q", format=".2%")])
        st.altair_chart(dots.properties(height=320), alt="VaR (left dot) and ES (right dot) for every model")
        st.caption("Left dot VaR, right dot ES; the selected model is blue. Which model to trust is settled under 'Is the model right?'.")

else:
    passed = mv.get("passes")
    with st.container(horizontal=True, vertical_alignment="center"):
        st.badge("Passed the one-shot test" if passed else "Failed the one-shot test",
                 icon=":material/verified:" if passed else ":material/error:", color="green" if passed else "red")
        st.caption(f"{mv.get('champion')} · {mv.get('test_start')} to {mv.get('test_end')} · {mv.get('days')} trading days it had never seen")
    with st.container(horizontal=True):
        st.metric("Bad days beyond the forecast", f"{mv.get('exceptions')}", f"{mv.get('expected', 0):.1f} expected",
                  delta_color="off", delta_arrow="off", border=True,
                  help="At 99%, about 1 day in 100 should exceed the forecast. Too many means the model understates risk.")
        st.metric("Is the count right?", "Yes" if mv.get("kupiec_p", 0) >= 0.05 else "No", f"Kupiec p = {mv.get('kupiec_p', 0):.2f}",
                  delta_color="off", delta_arrow="off", border=True,
                  help="Kupiec test: could the number of breaches come from a correct model? p above 0.05 means yes.")
        st.metric("Do bad days cluster?", "No" if mv.get("cc_p", 0) >= 0.05 else "Yes", f"Christoffersen p = {mv.get('cc_p', 0):.2f}",
                  delta_color="off", delta_arrow="off", border=True,
                  help="Christoffersen test: does one breach make the next more likely? Clustering means the model reacts too slowly.")
    explain("We chose the model on 2019–2022 with a rule fixed in advance, froze everything, and only then ran it once on "
            "2023–2026. Of eleven models only three passed there; the rest failed because their bad days came in clusters. "
            "The machine-learning challenger was not adopted: less accurate than the champion by more than the 2% margin set in advance.")

    alpha = ctl.alpha if ctl.alpha in (0.95, 0.99) else 0.95
    parts = [artifact(f"backtest_{FILES[ctl.model]}_500.parquet"), artifact(f"final_test_{FILES[ctl.model]}.parquet")]
    bt = pd.concat([p for p in parts if p is not None]).sort_index()
    bt = bt[~bt.index.duplicated(keep="last")].loc[f"{ctl.start}-01-01":f"{ctl.end}-12-31"]
    hits = bt[f"hit_{alpha}"].astype(int)
    k, ch = cv.kupiec(hits.to_numpy(), alpha), cv.christoffersen(hits.to_numpy(), alpha)
    roll = cv.rolling_basel(hits, 250, alpha) if alpha == 0.99 else None
    st.subheader(f"{ctl.model}, {alpha:.0%}, {ctl.start}–{ctl.end}")
    if ctl.alpha == 0.90:
        st.caption("Backtests are stored at 95% and 99% confidence; showing 95%.")
    if roll is not None and len(roll):
        zone = roll["zone"].iloc[-1]
        st.badge({"green": "Traffic light: green", "yellow": "Traffic light: yellow", "red": "Traffic light: red"}[zone],
                 icon=":material/traffic:", color={"green": "green", "yellow": "orange", "red": "red"}[zone])
    st.caption(f"{k.x} breaches against {k.expected:.1f} expected · Kupiec p = {k.pvalue:.3f} · Christoffersen p = {ch.p_cc:.3f} "
               "over the dates you chose (before 2019 is the build period, including 2008).")
    d = bt.reset_index().rename(columns={"index": "date"})
    d = d.rename(columns={d.columns[0]: "date"})
    d["loss_usd"], d["var_usd"] = d["loss"] * nav, d[f"var_{alpha}"] * nav
    base = alt.Chart(d).encode(x=alt.X("date:T", title=None))
    chart = (base.mark_line(color=GREY, strokeWidth=0.6).encode(y=alt.Y("loss_usd:Q", title="One-day loss (USD)", axis=alt.Axis(format="$~s")))
             + base.mark_line(color=ACCENT, strokeWidth=1.4).encode(y="var_usd:Q")
             + alt.Chart(d[d[f"hit_{alpha}"] == 1]).mark_circle(color=CRIT, size=36).encode(
                 x="date:T", y="loss_usd:Q", tooltip=[alt.Tooltip("date:T"), alt.Tooltip("loss_usd:Q", format="$,.0f", title="loss")])
             + alt.Chart(pd.DataFrame({"date": [pd.Timestamp("2023-01-01")]})).mark_rule(strokeDash=[4, 4], color="#1D2733").encode(x="date:T"))
    st.altair_chart(chart.properties(height=320).interactive(bind_y=False), alt="Daily loss, VaR forecast and breaches")
    explain("Grey: the fund's daily loss (below zero is a gain). Blue: the model's forecast line. Red dots: days the loss crossed "
            "the line. The dashed line marks the start of the one-shot test. Drag or scroll on the chart to zoom into a crisis.")
    if roll is not None and len(roll):
        z = roll.reset_index()
        z = z.rename(columns={z.columns[0]: "date"})
        z["run"] = (z["zone"] != z["zone"].shift()).cumsum()           # merge consecutive days of one colour
        z = z.groupby("run").agg(date=("date", "first"), end=("date", "last"), zone=("zone", "first")).reset_index(drop=True)
        z["end"] = z["date"].shift(-1).fillna(z["end"])
        z["date"], z["end"], z["zone"] = z["date"].astype("datetime64[ns]"), z["end"].astype("datetime64[ns]"), z["zone"].astype(str)
        st.altair_chart(alt.Chart(z).mark_rect(y=0, y2=50).encode(
            x=alt.X("date:T", title=None), x2="end:T", tooltip=[alt.Tooltip("date:T", title="from"), alt.Tooltip("end:T", title="to"), "zone:N"],
            color=alt.Color("zone:N", scale=alt.Scale(domain=["green", "yellow", "red"], range=[GOOD, WARN, CRIT]),
                            legend=alt.Legend(title=None, orient="bottom"))).properties(height=60),
            alt="Traffic light over every 250-day window")
        st.caption("Traffic light over every 250-day window (Basel: 0–4 breaches green, 5–9 yellow, 10 or more red).")
    with st.expander("All eleven models on the one-shot test", icon=":material/leaderboard:"):
        sc = artifact("final_test_scores.parquet")
        st.dataframe(pd.DataFrame({"Breaches (9.6 expected)": sc["exceptions"].astype(int), "Kupiec p": sc["kupiec_p"].round(3),
                                   "Christoffersen p": sc["cc_p"].round(3), "Passes": sc["passes"].map({True: "yes", False: "no"}),
                                   "Accuracy": sc["pinball_vs_champion"].map(lambda v: f"{v:+.1%} vs champion" if v > 0 else "best")}),
                     height=35 * (len(sc) + 1) + 3, alt="All models on the one-shot test")
    with st.expander("Every breach on 2019–2022 and its cause", icon=":material/history:"):
        v = artifact(f"backtest_{FILES[mv.get('champion', 'GJR conditional EVT')]}_500.parquet").loc["2019-01-01":"2022-12-31"]
        log = v[v["hit_0.99"] == 1]
        st.dataframe(pd.DataFrame({"Loss": (log["loss"] * nav).map(money), "Forecast": (log["var_0.99"] * nav).map(money),
                                   "Cause": [EXCEPTION_CAUSES.get(str(x.date()), "—") for x in log.index]}, index=log.index.date),
                     height=35 * (len(log) + 1) + 3, alt="Breaches with their causes")
        say("All 14 have a documented market cause and none is a data error. Six were the first days of a new crisis, when "
            "a volatility model needs a few days to catch up; that is why the fund also holds a crisis budget and stress tests.")
