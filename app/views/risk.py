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
say("How much can the fund lose on a bad day, and can we trust that number? Use the Risk controls in the sidebar to "
    "change how cautious the estimate is, which model makes it, and which years you look at.")
view = st.segmented_control("View", ["A bad day", "Is the model right?"], default="A bad day", required=True,
                            label_visibility="collapsed", key="risk_view",
                            format_func=lambda v: {"A bad day": ":material/trending_down: A bad day",
                                                   "Is the model right?": ":material/fact_check: Is the model right?"}[v])
st.space("small")

if view == "A bad day":
    snap = artifact("decision_risk_snapshot.parquet").set_index(["model", "alpha"])
    var_, es_ = float(snap.loc[(ctl.model, ctl.alpha), "var"]), float(snap.loc[(ctl.model, ctl.alpha), "es"])
    evt = float(snap.loc[("EVT", ctl.alpha), "es"])
    freq = per_year(ctl.alpha)
    with st.container(horizontal=True):
        st.metric("Value at Risk (VaR)", f"−{money(var_ * nav)}", f"lost on {freq.split(' (')[0]} or worse", delta_color="off",
                  delta_arrow="off", border=True, help=f"On {freq} the fund loses at least this much. It does not say how much "
                  "more.")
        st.metric("Expected Shortfall (ES)", f"−{money(es_ * nav)}", "average loss on those days", delta_color="off",
                  delta_arrow="off", border=True, help="How much the fund loses on average on those bad days. The committee's "
                  "bad-day limit uses this measure.")
        st.metric("Extreme Value Theory (EVT)", f"−{money(evt * nav)}", "the most cautious estimate", delta_color="off",
                  delta_arrow="off", border=True, help="Built only from the worst days in history, so it gives the most "
                  "cautious view of rare, extreme losses.")
    df = pd.DataFrame({"measure": ["VaR", "ES", "EVT"], "loss": [var_ * nav, es_ * nav, evt * nav],
                       "label": [money(var_ * nav), f"{money(es_ * nav)} ({es_ / var_ - 1:+.0%})", f"{money(evt * nav)} ({evt / var_ - 1:+.0%})"]})
    bars = alt.Chart(df).mark_bar(cornerRadiusEnd=4, size=70).encode(
        x=alt.X("measure:N", sort=None, title=None, axis=alt.Axis(labelAngle=0, labelFontSize=14)),
        y=alt.Y("loss:Q", title="One-day loss (USD)", axis=alt.Axis(format="$~s"), scale=alt.Scale(domain=[0, max(df.loss) * 1.25])),
        color=alt.Color("measure:N", scale=alt.Scale(domain=["VaR", "ES", "EVT"], range=TAIL), legend=None),
        tooltip=["measure:N", alt.Tooltip("loss:Q", format="$,.0f")])
    st.altair_chart((bars + bars.mark_text(dy=-10, fontSize=13).encode(text="label:N", color=alt.value("#1D2733"))).properties(height=300),
                    alt=f"VaR, ES and EVT at {ctl.alpha:.0%}")
    explain(f"Three ways of measuring a bad day, in dollars. VaR is the line a bad day crosses; ES is the average loss once "
            f"it does; EVT looks only at the most extreme days in history. The percentages show how much worse ES and EVT are "
            f"than VaR: that gap is the risk VaR alone would hide. These figures reflect the last two years, which were fairly "
            f"calm. Including a 2008-style period, an average very bad day costs {money(n['risk']['es99_ttc'] * nav)}, "
            f"within the committee's limit of {money(n['limits']['es99_max'] * nav)}.")
    with st.expander("Over ten days, and once in a decade", icon=":material/calendar_month:"):
        say(f"**Over two weeks:** once in a hundred two-week periods the fund could lose more than "
            f"{money(rd['var99_10d'] * nav)}, and {money(rd['es99_10d'] * nav)} on average when it does.  \n"
            f"**The worst single day in ten years:** about {money(rd['once_in_10y_champion'] * nav)} judging by today's "
            f"markets, and up to {money(rd['once_in_10y_evt'] * nav)} judging by the long history. The difference shows how "
            "uncertain any estimate of rare events is.")
    with st.expander("Compare every model", icon=":material/compare:"):
        t = snap.xs(ctl.alpha, level="alpha").reset_index()
        t["chosen"] = t["model"].eq(ctl.model)
        dots = alt.Chart(t.melt(["model", "chosen"], ["var", "es"], "measure", "loss")).mark_line(point=True).encode(
            x=alt.X("loss:Q", title="One-day loss (share of the endowment)", axis=alt.Axis(format=".1%")),
            y=alt.Y("model:N", sort=alt.EncodingSortField("loss", op="max"), title=None),
            detail="model:N", color=alt.condition("datum.chosen", alt.value(ACCENT), alt.value(GREY)),
            tooltip=["model:N", "measure:N", alt.Tooltip("loss:Q", format=".2%")])
        st.altair_chart(dots.properties(height=320), alt="VaR (left dot) and ES (right dot) for every model")
        st.caption("For each model, the left dot is VaR and the right dot is ES; the model you selected is blue. The tab "
                   "'Is the model right?' shows which model passed the test.")

else:
    passed = mv.get("passes")
    with st.container(horizontal=True, vertical_alignment="center"):
        st.badge("Passed the one-shot test" if passed else "Failed the one-shot test",
                 icon=":material/verified:" if passed else ":material/error:", color="green" if passed else "red")
        st.caption(f"Our model ({mv.get('champion')}) on {mv.get('days')} trading days from {mv.get('test_start')} to "
                   f"{mv.get('test_end')}, data it had never seen")
    with st.container(horizontal=True):
        st.metric("Days worse than forecast", f"{mv.get('exceptions')}", f"about {mv.get('expected', 0):.0f} expected",
                  delta_color="off", delta_arrow="off", border=True,
                  help="A good model is beaten on about 1 day in 100. Many more would mean it understates risk.")
        st.metric("Is the count right?", "Yes" if mv.get("kupiec_p", 0) >= 0.05 else "No", f"Kupiec p = {mv.get('kupiec_p', 0):.2f}",
                  delta_color="off", delta_arrow="off", border=True,
                  help="A standard test (Kupiec) of whether the number of misses is what a correct model would give.")
        st.metric("Do bad days cluster?", "No" if mv.get("cc_p", 0) >= 0.05 else "Yes", f"Christoffersen p = {mv.get('cc_p', 0):.2f}",
                  delta_color="off", delta_arrow="off", border=True,
                  help="A standard test (Christoffersen) of whether misses come in bunches, which would mean the model reacts "
                       "too slowly to a crisis.")
    explain("We chose this model using 2019–2022 data, then tested it once on 2023–2026, which it had never seen, without "
            "changing anything. Of the eleven models we compared, only three passed; the others missed several bad days in a "
            "row. A machine-learning model was also tested and passed, but it was less accurate than ours.")

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
    st.caption(f"Over the years you chose: {k.x} days worse than forecast against about {k.expected:.0f} expected "
               f"(Kupiec p = {k.pvalue:.2f}, Christoffersen p = {ch.p_cc:.2f}). Years before 2019 include 2008, when every "
               "model struggled.")
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
    explain("Grey: what the fund lost each day (below zero means it gained). Blue: the model's forecast of a bad day. Red "
            "dots: days that were worse than the forecast. Right of the dashed line is the 2023–2026 test. Scroll on the chart "
            "to zoom into a crisis.")
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
        st.caption("The regulators' traffic light for every year-long window: green means 0–4 days worse than forecast in "
                   "a year, yellow 5–9, red 10 or more.")
    with st.expander("All eleven models on the 2023–2026 test", icon=":material/leaderboard:"):
        sc = artifact("final_test_scores.parquet")
        st.dataframe(pd.DataFrame({"Days worse than forecast (≈10 expected)": sc["exceptions"].astype(int),
                                   "Kupiec p": sc["kupiec_p"].round(2), "Christoffersen p": sc["cc_p"].round(2),
                                   "Passed": sc["passes"].map({True: "yes", False: "no"}),
                                   "Accuracy": sc["pinball_vs_champion"].map(lambda v: f"{v:.1%} less accurate" if v > 0 else "most accurate")}),
                     height=35 * (len(sc) + 1) + 3, alt="All models on the one-shot test")
    with st.expander("Every miss in 2019–2022 and what caused it", icon=":material/history:"):
        v = artifact(f"backtest_{FILES[mv.get('champion', 'GJR conditional EVT')]}_500.parquet").loc["2019-01-01":"2022-12-31"]
        log = v[v["hit_0.99"] == 1]
        st.dataframe(pd.DataFrame({"Loss": (log["loss"] * nav).map(money), "Forecast": (log["var_0.99"] * nav).map(money),
                                   "Cause": [EXCEPTION_CAUSES.get(str(x.date()), "—") for x in log.index]}, index=log.index.date),
                     height=35 * (len(log) + 1) + 3, alt="Breaches with their causes")
        say("Each one matches a real market event. Six were the first days of a new crisis, before any model could react; "
            "that is why the fund also has a crisis limit and stress tests, not just a daily risk number.")
