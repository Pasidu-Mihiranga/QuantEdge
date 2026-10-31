"""Risk, and how sure we are: the booklet's risk dashboard (VaR, ES, EVT side by side) and backtesting panel."""

import altair as alt
import pandas as pd
import streamlit as st

from components.content import EXCEPTION_CAUSES
from components.controls import FILES, risk_controls
from components.palette import palette
from components.ui import (
    artifact,
    explain,
    header,
    money,
    need_numbers,
    pct,
    per_year,
    returns_to_decision,
    say,
    step_footer,
)
from quantedge.backtest import coverage as cv
from quantedge.config import load_config
from quantedge.data.partition import load_returns
from quantedge.decision.objective import crisis_loss
from quantedge.risk.es import sample_es

n = need_numbers()
nav, rd, mv = n["nav_usd"], n["risk_day"], n["model_validity"]
P = palette()
ACCENT, GREY, CRIT, GOOD, WARN = P.accent, P.grey, P.crit, P.good, P.warn
TAIL = list(P.tail)

header("Risk, and how sure we are", page="views/risk.py")
say("How much can the fund lose on a bad day, and can we trust that number? Use the Risk controls in the sidebar to "
    "change how cautious the estimate is, which model makes it, and which years you look at.")
VIEWS = {"A bad day": ":material/trending_down:", "Diversification": ":material/hub:", "Is the model right?": ":material/fact_check:"}
view = st.segmented_control("View", list(VIEWS), default="A bad day", required=True, label_visibility="collapsed",
                            key="risk_view", format_func=lambda v: f"{VIEWS[v]} {v}")
st.space("small")
ctl = risk_controls(dates=view == "Is the model right?", models=view != "Diversification")  # only controls that change the view

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
        st.metric("Extreme Value Theory (EVT)", f"−{money(evt * nav)}", "built from the worst days only", delta_color="off",
                  delta_arrow="off", border=True, help="Built only from the worst days in history, so it describes rare, "
                  "extreme losses better than a model fitted to every day.")
    if ctl.model == "Cornish-Fisher":
        st.warning("Cornish-Fisher is unreliable for this fund: its correction for skew and fat tails only works when they "
                   "are mild, and these returns are too fat-tailed. It understates VaR at 90% and overstates both VaR and ES "
                   "at 99%. It is shown for comparison only; the limits use the tested model.", icon=":material/warning:")
    df = pd.DataFrame({"measure": ["VaR", "ES", "EVT"], "loss": [var_ * nav, es_ * nav, evt * nav],
                       "label": [money(var_ * nav), f"{money(es_ * nav)} ({es_ / var_ - 1:+.0%})", f"{money(evt * nav)} ({evt / var_ - 1:+.0%})"]})
    bars = alt.Chart(df).mark_bar(cornerRadiusEnd=4, size=70).encode(
        x=alt.X("measure:N", sort=None, title=None, axis=alt.Axis(labelAngle=0, labelFontSize=14)),
        y=alt.Y("loss:Q", title="One-day loss (USD)", axis=alt.Axis(format="$~s"), scale=alt.Scale(domain=[0, max(df.loss) * 1.25])),
        color=alt.Color("measure:N", scale=alt.Scale(domain=["VaR", "ES", "EVT"], range=TAIL), legend=None),
        tooltip=["measure:N", alt.Tooltip("loss:Q", format="$,.0f")])
    st.altair_chart((bars + bars.mark_text(color=P.ink, dy=-10, fontSize=13).encode(text="label:N", color=alt.value(P.ink))).properties(height=300),
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

    with st.expander("Why the models disagree", icon=":material/psychology_alt:"):
        # Facts about the portfolio's own returns that drive the gaps (booklet: "discuss where and why they disagree").
        past = returns_to_decision()
        port = past @ pd.Series(n["weights"]).reindex(past.columns, fill_value=0.0)
        recent = port.loc[rd["window_start"]:rd["window_end"]]
        vol_now, vol_all = float(port.iloc[-21:].std() * 252 ** 0.5), float(port.std() * 252 ** 0.5)
        hs = snap.xs(ctl.alpha, level="alpha")
        WHY = {"Historical": "Replays the last two years as they happened; assumes nothing about their shape.",
               "Normal": "Assumes a bell curve, so it misses fat tails: too low far out in the tail.",
               "Student-t": "A bell curve with fat tails: higher far out in the tail, lower near the middle.",
               "Cornish-Fisher": "Bends the bell curve for skew and fat tails; breaks down when the tails are this fat.",
               "EVT": "Fits only the worst days, so it describes the far tail best.",
               "Monte Carlo": "Simulates 100,000 days from a fitted fat-tailed distribution.",
               "GARCH-FHS": "Rescales history to today's volatility: higher when markets are nervous.",
               "GJR-FHS": "As GARCH-FHS, but falls raise volatility more than rises do.",
               "Conditional EVT": "Today's volatility plus an EVT tail.",
               "GJR conditional EVT": "Today's volatility (falls weigh more) plus an EVT tail: the tested model."}
        tbl = pd.DataFrame({"VaR": (hs["var"] * nav).map(money), "ES": (hs["es"] * nav).map(money),
                            "VaR vs historical": (hs["var"] / hs.loc["Historical", "var"] - 1).map(lambda v: f"{v:+.0%}"),
                            "Why it differs": [WHY.get(m, "") for m in hs.index]})
        st.table(tbl)
        say(f"Three facts about this portfolio explain the gaps:\n- **Fat tails:** its daily returns have an excess kurtosis of "
            f"{port.kurt():.1f} since 2004 ({recent.kurt():.1f} in the last two years; a bell curve has 0), so models that "
            f"assume a bell curve understate rare losses.\n- **Skew:** {port.skew():+.2f}, "
            + ("big falls are more common than big rises." if port.skew() < -0.2 else "close to symmetric, so skew matters "
               "little here; the fat tails do the damage.")
            + f"\n- **Volatility now vs on average:** {pct(vol_now)} over the last month against {pct(vol_all)} since "
            "2004, so models that react to today's volatility give "
            + ("lower" if vol_now < vol_all else "higher") + " numbers than models built on all of history.\n- At "
            f"{ctl.alpha:.0%} these effects " + ("are small: most models agree." if ctl.alpha < 0.99 else
                                                 "are largest: this is where the models disagree most."))

elif view == "Diversification":
    # Booklet p. 4: what holding several funds saves, on a bad day and in each crisis, and why less in 2022.
    cfg = load_config()
    w = pd.Series(n["weights"]).loc[lambda s: s > 1e-4]
    dev = load_returns("dev", cfg)[w.index]                     # 2004-2018, as the bad-day limit (through the cycle)
    port_es = sample_es(-(dev @ w).to_numpy(), ctl.alpha)
    alone_es = sum(w[t] * sample_es(-dev[t].to_numpy(), ctl.alpha) for t in w.index)
    past = returns_to_decision()[w.index]
    crises = cfg.stress["historical"]
    together = crisis_loss(w, past, crises)
    alone = sum(w[t] * crisis_loss(pd.Series({t: 1.0}), past, crises) for t in w.index)
    with st.container(horizontal=True):
        st.metric("A very bad day, fund by fund", f"−{money(alone_es * nav)}", "if every fund fell at once",
                  delta_color="off", delta_arrow="off", border=True,
                  help=f"Each holding's own average loss on its worst {1 - ctl.alpha:.0%} of days, added up (2004–2018).")
        st.metric("The same day, for the portfolio", f"−{money(port_es * nav)}", "they rarely fall together",
                  delta_color="off", delta_arrow="off", border=True)
        st.metric("Diversification saves", money((alone_es - port_es) * nav), f"{(alone_es - port_es) / alone_es:.0%} of the bad-day loss",
                  delta_color="off", delta_arrow="off", border=True)
    cd = pd.DataFrame({"crisis": list(crises) * 2, "how": ["each fund on its own"] * len(crises) + ["the portfolio"] * len(crises),
                       "loss": [*(alone[c] * nav for c in crises), *(together[c] * nav for c in crises)]})
    cd["label"] = cd["loss"].map(money)
    order_h = ["each fund on its own", "the portfolio"]
    base_d = alt.Chart(cd).encode(y=alt.Y("crisis:N", sort=list(crises), title=None, axis=alt.Axis(labelFontSize=13, labelLimit=300)),
                                  yOffset=alt.YOffset("how:N", sort=order_h))
    st.altair_chart((base_d.mark_bar(height=14, cornerRadiusEnd=3).encode(
        x=alt.X("loss:Q", title="Loss in the crisis (USD)", axis=alt.Axis(format="$~s")),
        color=alt.Color("how:N", sort=order_h, scale=alt.Scale(domain=order_h, range=[GREY, ACCENT]),
                        legend=alt.Legend(title=None, orient="bottom")),
        tooltip=["crisis:N", "how:N", alt.Tooltip("loss:Q", format="$,.0f")])
        + base_d.mark_text(color=P.ink, align="left", dx=5, fontSize=11).encode(x="loss:Q", text="label:N")).properties(height=alt.Step(16)),
        alt="Crisis loss with and without diversification")
    saved = "; ".join(f"{money((alone[c] - together[c]) * nav)} in {c}" for c in crises)
    win = lambda c: past.loc[(past.index > pd.Timestamp(crises[c][0])) & (past.index <= pd.Timestamp(crises[c][1]))]  # noqa: E731
    moves = "; ".join(f"in {c} bonds {pct(float((1 + win(c)['AGG']).prod() - 1), signed=True)} while US stocks "
                      f"{pct(float((1 + win(c)['SPY']).prod() - 1), signed=True)}" for c in crises) if {"AGG", "SPY"} <= set(past.columns) else ""
    say(f"In every crisis the portfolio lost less than its funds would have lost one by one, because their worst days did "
        f"not all coincide. Diversification saved {saved}. What differs is the bond cushion: {moves}. When bonds fall with "
        "stocks, as in 2022, the cushion is gone, which is the case our stagflation scenario is built on.")
    st.markdown("##### How the funds move together")
    period = st.segmented_control("Period", ["All days since 2004", *crises], default="All days since 2004", required=True,
                                  label_visibility="collapsed", key="div_period")
    r = past if period == "All days since 2004" else past.loc[
        (past.index > pd.Timestamp(crises[period][0])) & (past.index <= pd.Timestamp(crises[period][1]))]
    cm = r.corr().stack().rename("corr").rename_axis(["a", "b"]).reset_index()
    funds = list(w.index)
    heat = alt.Chart(cm).encode(x=alt.X("a:N", sort=funds, title=None), y=alt.Y("b:N", sort=funds, title=None))
    st.altair_chart((heat.mark_rect().encode(color=alt.Color("corr:Q", scale=alt.Scale(domain=[-1, 0, 1], range=[ACCENT, P.neutral, CRIT]),
                                                             legend=alt.Legend(title="correlation")),
                                             tooltip=["a:N", "b:N", alt.Tooltip("corr:Q", format=".2f")])
                     + heat.mark_text(color=P.ink, fontSize=13).encode(text=alt.Text("corr:Q", format=".2f")))
                    .properties(height=260, width=360), alt=f"Correlations, {period}")
    if "AGG" in funds and "SPY" in funds:
        say(f"US stocks and bonds (SPY and AGG) had a correlation of **{r['SPY'].corr(r['AGG']):+.2f}** in this period "
            f"(against {past['SPY'].corr(past['AGG']):+.2f} over all days): below zero, bonds cushion a fall in stocks; "
            "above zero, they fall together.")

else:
    passed = mv.get("passes")
    # Independence p of the champion on the days every model forecast (the scored days), as in final_test_scores
    tests = [artifact(f"final_test_{f}.parquet") for f in [*FILES.values(), "linear_qr"]]
    common = sorted(set.intersection(*(set(t.index) for t in tests if t is not None)))
    champ_hits = artifact(f"final_test_{FILES[mv.get('champion', 'GJR conditional EVT')]}.parquet").loc[common, "hit_0.99"]
    ind_p = cv.christoffersen(champ_hits.astype(int).to_numpy(), 0.99).p_ind
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
        st.metric("Do bad days cluster?", "No" if ind_p >= 0.05 else "Yes", f"independence p = {ind_p:.2f}",
                  delta_color="off", delta_arrow="off", border=True,
                  help=f"Christoffersen's independence test: do misses come in bunches, which would mean the model reacts too "
                       f"slowly to a crisis? p = {ind_p:.3f}: "
                       + ("the misses do cluster. " if ind_p < 0.05 else "no clustering at 5%, but close: worth watching. "
                          if ind_p < 0.10 else "no sign of clustering. ")
                       + f"The combined count-and-cluster "
                       f"test gives p = {mv.get('cc_p', 0):.2f}. Scored on the {len(common)} days on which every model made a "
                       "forecast.")
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
    verdict = lambda p: "passes" if p >= 0.05 else "fails at 5%"  # noqa: E731
    st.caption(f"Over the years you chose: {k.x} days worse than forecast against about {k.expected:.0f} expected. Count "
               f"(Kupiec) p = {k.pvalue:.3f}, {verdict(k.pvalue)}; clustering (independence) p = {ch.p_ind:.3f}, "
               f"{verdict(ch.p_ind)}; both together p = {ch.p_cc:.3f}, {verdict(ch.p_cc)}."
               + (" These years include 2008, when every model struggled." if ctl.start <= 2009 else ""))
    if alpha == 0.99 and (roll is None or not len(roll)):
        st.caption("The traffic light needs at least 250 trading days: choose a range of a full year or more.")
    d = bt.reset_index().rename(columns={"index": "date"})
    d = d.rename(columns={d.columns[0]: "date"})
    d["loss_usd"], d["var_usd"] = d["loss"] * nav, d[f"var_{alpha}"] * nav
    base = alt.Chart(d).encode(x=alt.X("date:T", title=None))
    chart = (base.mark_line(color=GREY, strokeWidth=0.6).encode(y=alt.Y("loss_usd:Q", title="One-day loss (USD)", axis=alt.Axis(format="$~s")))
             + base.mark_line(color=ACCENT, strokeWidth=1.4).encode(y="var_usd:Q")
             + alt.Chart(d[d[f"hit_{alpha}"] == 1]).mark_circle(color=CRIT, size=36).encode(
                 x="date:T", y="loss_usd:Q", tooltip=[alt.Tooltip("date:T"), alt.Tooltip("loss_usd:Q", format="$,.0f", title="loss")])
             + alt.Chart(pd.DataFrame({"date": [pd.Timestamp("2023-01-01")]})).mark_rule(strokeDash=[4, 4], color=P.ink).encode(x="date:T"))
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

step_footer("views/risk.py")
