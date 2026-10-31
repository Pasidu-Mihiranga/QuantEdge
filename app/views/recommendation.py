"""Decision page 1: the verdict in one glance, then four views to explore it (one at a time)."""

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from components.pack import crises_table, summary_html, weights_table
from components.ui import artifact, esc, money, need_numbers, pct, returns_to_decision, say
from quantedge.config import load_config
from quantedge.decision.decision_date import es_shares
from quantedge.stress.factor import scenario_contributions

n = need_numbers()
obj, lim, risk, alt_ = n["objective"], n["limits"], n["risk"], n["alternatives"]
nav, eq = n["nav_usd"], n["advised_equity"]
key = n["verdict"].split()[0]
fr = artifact("decision_frontier.parquet")
ACCENT, GREY, CRIT = "#1F5FAE", "#A3ABB5", "#B42318"
NAMES = {"SPY": "US stocks", "EFA": "Developed-market stocks", "EEM": "Emerging-market stocks",
         "AGG": "US investment-grade bonds", "GLD": "Gold", "XLE": "Energy stocks", "XLK": "Technology stocks"}

st.title("Our recommendation")
st.caption(f"Serendib University Endowment · USD {nav / 1e6:.0f}M · decision date {n['decision_date']} · "
           f"market data to {n['data_end']}")

# ---------- the answer, in one glance ----------
with st.container(border=True):
    badge = {"ACCEPT": ("ACCEPT the mandate as proposed", "green", ":material/check_circle:"),
             "ADJUST": ("ADJUST the risk limit", "orange", ":material/tune:"),
             "REJECT": ("REJECT the mandate as proposed", "red", ":material/cancel:")}[key]
    st.badge(badge[0], icon=badge[2], color=badge[1])
    if key == "ACCEPT":
        st.subheader(f"Invest {eq:.0%} in equities and {1 - eq:.0%} in bonds and real assets. Expected return "
                     f"{pct(n['expected_return'], 2)} a year against the {pct(obj['required_return'], 2)} the objective "
                     "needs, with every risk limit met.")
    else:
        st.subheader(f"No portfolio inside the risk limits is expected to earn the {pct(obj['required_return'], 2)} the "
                     "objective needs.")
    if key == "ACCEPT" and n["robustness"].get("ACCEPT", 0) < sum(n["robustness"].values()) / 2 + 1:
        st.markdown(esc(f":orange-badge[:material/warning: Narrow margin] {money(n['return_margin_usd'])} a year above the "
                        "target. Try **What would change it** below."))
    with st.container(horizontal=True, gap="small"):
        st.download_button("Committee summary", summary_html(n), "committee_summary.html", "text/html",
                           icon=":material/download:", help="One printable page with the verdict, the allocation, every "
                           "limit, the crises and how sure we are. Built from the same numbers as this app.")
        st.download_button("Weights (CSV)", weights_table(n).to_csv(index=False), "weights.csv", "text/csv",
                           icon=":material/table:", type="tertiary")
        st.download_button("Crises (CSV)", crises_table(n).to_csv(index=False), "crises.csv", "text/csv",
                           icon=":material/table:", type="tertiary")

mv = n["model_validity"]
with st.container(horizontal=True):
    margin_ok = n["return_margin"] >= 0
    narrow = margin_ok and n["robustness"].get("ACCEPT", 0) < sum(n["robustness"].values()) / 2 + 1
    st.metric("Expected return a year", pct(n["expected_return"], 2),
              f"needs {pct(obj['required_return'], 2)}" + (" · narrow" if narrow else ""),
              delta_color="orange" if narrow else ("green" if margin_ok else "red"), delta_arrow="off", border=True)
    st.metric("Worst crisis on record", f"−{money(risk['worst_crisis_loss'] * nav)}",
              f"{risk['worst_crisis']} · limit {money(lim['crisis_budget'] * nav)}",
              delta_color="green" if risk["worst_crisis_loss"] <= lim["crisis_budget"] else "red", delta_arrow="off", border=True)
    st.metric("A very bad day", f"−{money(risk['es99_ttc'] * nav)}", f"worst 1 day in 100 · limit {money(lim['es99_max'] * nav)}",
              delta_color="green" if risk["es99_ttc"] <= lim["es99_max"] else "red", delta_arrow="off", border=True,
              help="Measured over 2004–2018, which includes the 2008 crisis, so a calm year does not make it look smaller.")
    st.metric("Risk model tested on new data", "Passed" if mv.get("passes") else "Failed",
              f"{mv.get('exceptions')} misses vs {mv.get('expected', 0):.1f} expected, 2023–26",
              delta_color="green" if mv.get("passes") else "red", delta_arrow="off", border=True, help="We tested the risk model once on 2023–2026 data it had never seen. "
              "It should miss about 1 day in 100; it missed 9 days against about 10 expected.")

# ---------- explore, one view at a time ----------
VIEWS = {"The mix": ":material/pie_chart:", "What would change it": ":material/tune:",
         "Alternatives": ":material/compare_arrows:", "Why this mix": ":material/rule:"}
st.space("small")
view = st.segmented_control("Explore", list(VIEWS), default="The mix", format_func=lambda v: f"{VIEWS[v]} {v}",
                            label_visibility="collapsed", required=True, key="rec_view")
st.space("small")

if view == "The mix":
    w = pd.Series(n["weights"]).loc[lambda s: s > 1e-4].sort_values(ascending=False)
    df = pd.DataFrame({"fund": [f"{NAMES[t]} ({t})" for t in w.index], "weight": w.values,
                       "label": [f"{v:.1%} · {money(v * nav)}" for v in w.values]})
    left, right = st.columns([3, 2], gap="large")
    with left:
        base = alt.Chart(df).encode(y=alt.Y("fund:N", sort=None, title=None, axis=alt.Axis(labelLimit=320, labelFontSize=13)),
                                    x=alt.X("weight:Q", axis=None, scale=alt.Scale(domain=[0, w.max() * 1.45])))
        chart = base.mark_bar(color=ACCENT, cornerRadiusEnd=4, height=26) + base.mark_text(align="left", dx=6).encode(text="label:N")
        st.altair_chart(chart.properties(height=60 * len(df)), alt="Recommended weights")
    with right:
        inc = risk["income_yield"]
        st.markdown(esc(
            f"- **{1 - eq:.0%} in bonds** (AGG) for income and crash protection.\n"
            f"- **{eq:.0%} in equities**, spread across the US, developed markets and energy (a hedge against oil "
            "and inflation shocks).\n"
            f"- **Income pays the scholarships:** dividends and interest of about {money(inc * nav)} a year "
            f"({pct(inc, 2)}) cover the 3% spending rate.\n"
            f"- **No fund dominates the tail risk:** the largest share is {n['largest_es_share_etf']} at "
            f"{n['largest_es_share']:.0%}, below the 40% cap."))
        st.page_link("views/portfolio.py", label="Compare other equity shares and the history since 2008", icon=":material/compare_arrows:")

    # Risk budget (booklet p. 8): the same Euler ES shares as the D8 rule, plus each fund's share of the scenario loss.
    st.subheader("Where the risk comes from", divider=False)
    cfg = load_config()
    past = returns_to_decision()
    wf = pd.Series(n["weights"]).reindex(past.columns, fill_value=0.0)
    es_sh = es_shares(wf, past)
    hyp = cfg.stress["hypothetical"]
    parts = scenario_contributions(artifact("decision_scenario_betas.parquet"), hyp["shock"], wf, hyp.get("liquidity_day"))
    parts.index = [i.split(" ")[0] for i in parts.index]                 # the AGG panic day counts as AGG
    scen = parts.groupby(level=0).sum() / parts.sum()
    rb = pd.DataFrame({"Share of the money": wf, "Share of a very bad day (99% ES)": es_sh,
                       "Share of the stagflation loss": scen}).loc[w.index].fillna(0.0)
    long = rb.rename(index=lambda t: f"{NAMES[t]} ({t})").reset_index(names="fund").melt(
        "fund", var_name="measure", value_name="share")
    order = list(rb.columns)
    bars = alt.Chart(long).mark_bar(cornerRadiusEnd=3, height=12).encode(
        y=alt.Y("fund:N", sort=None, title=None, axis=alt.Axis(labelLimit=320, labelFontSize=13)),
        yOffset=alt.YOffset("measure:N", sort=order),
        x=alt.X("share:Q", title=None, axis=alt.Axis(format=".0%"), scale=alt.Scale(domain=[min(0.0, long.share.min()), min(1.0, long.share.max() * 1.1)])),
        color=alt.Color("measure:N", sort=order, scale=alt.Scale(domain=order, range=[GREY, ACCENT, "#1F3F73"]),
                        legend=alt.Legend(title=None, orient="bottom", labelLimit=400)),
        tooltip=["fund:N", "measure:N", alt.Tooltip("share:Q", format=".1%")])
    st.altair_chart(bars.properties(height=alt.Step(14)), alt="Share of money, of bad-day risk and of the scenario loss")
    top = scen.idxmax()
    say(f"No fund carries more than {pct(es_sh.max(), 0)} of the bad-day risk (the cap is "
        f"{pct(cfg.decision['es_share_cap'], 0)}). The two risk measures disagree about {NAMES[top]} ({top}): the bad-day "
        f"measure, built from history, gives it only {pct(es_sh[top], 0)} of the risk, but in our stagflation scenario it "
        f"carries **{pct(scen.max(), 0)}** of the loss, because there bonds fall with stocks. That is why the crisis budget is "
        "checked separately from the daily risk.")

elif view == "What would change it":
    wi = artifact("decision_whatif.parquet")
    say("Our answer depends on two forecasts nobody can know for sure: how much more stocks will earn than bonds, and "
        "where interest rates go. Try other values and see whether the answer changes.")
    panel = st.container(border=True)
    c1, c2, c3 = panel.columns([2, 2, 1.3], vertical_alignment="center", gap="large")
    erp = c1.slider("Extra return from stocks (equity premium)", 3.0, 6.0, 4.5, 0.25, format="%.2f%%", key="wi_erp",
                    help="How much more a year stocks earn than bonds over the long run. We assume 4.5%; published "
                         "estimates range from about 4% to 5.5%.") / 100
    dy = c2.slider("Change in interest rates after inflation", -1.0, 1.0, 0.0, 0.1, format="%+.1f pts", key="wi_dy",
                   help="0 means today's level. Higher rates mean bonds pay more, which helps this bond-heavy portfolio.") / 100
    taxed = c3.toggle("Bond income taxed", value=False, key="wi_tax",
                      help="If US tax were withheld on the bond fund's interest, as it is on stock dividends.")
    s_ = wi[np.isclose(wi.erp, erp) & np.isclose(wi.dy, dy) & np.isclose(wi.agg_withholding, 0.15 if taxed else 0.0)]
    f = s_.set_index("equity_share")["forward_return"]
    inside = fr["within_limits"]
    need = obj["required_return"]
    ok = [x for x in f.index if f[x] >= need and inside[x]]
    near = [x for x in f.index if f[x] >= need and fr.loc[x, "d2_loss"] <= lim["crisis_budget"] + 0.05 + 1e-9]
    v = "ACCEPT" if ok else ("ADJUST" if near else "REJECT")
    best = min(ok) if ok else max(x for x in f.index if inside[x])
    gap = f[best] - need
    st.space("small")
    label = {"ACCEPT": ("Our answer stays: ACCEPT", "green", ":material/check_circle:"),
             "ADJUST": ("Only with a looser crisis limit: ADJUST", "orange", ":material/tune:"),
             "REJECT": ("The answer would change to REJECT", "red", ":material/cancel:")}[v]
    st.badge(label[0], icon=label[2], color=label[1])
    bars = pd.DataFrame({"what": [f"Expected return ({best:.0%} in stocks)", "What the fund needs"],
                         "value": [f[best] * 100, need * 100], "colour": ["#0D7A2F" if gap >= 0 else CRIT, GREY],
                         "label": [pct(f[best], 2), pct(need, 2)]})
    b = alt.Chart(bars).encode(y=alt.Y("what:N", sort=None, title=None, axis=alt.Axis(labelLimit=320, labelFontSize=14)),
                               x=alt.X("value:Q", title="% a year", scale=alt.Scale(domain=[0, max(bars.value) * 1.15])))
    st.altair_chart((b.mark_bar(cornerRadiusEnd=4, height=34).encode(color=alt.Color("colour:N", scale=None))
                     + b.mark_text(align="left", dx=8, fontSize=15).encode(text="label:N")).properties(height=150),
                    alt="Expected return against what the fund needs")
    say(f"With these values the safest portfolio that stays within the risk limits is expected to earn "
        f"**{pct(f[best], 2)}** a year against the **{pct(need, 2)}** the fund needs: **{money(abs(gap) * nav)} a year "
        f"{'more' if gap >= 0 else 'less'}** than needed.")
    st.caption(f"With today's values the answer is ACCEPT, but only just: it would change if the equity premium were "
               f"below {pct(n['erp_breakeven'], 2)} or if interest rates fell by {n['yield_margin']['pp'] * 100:.2f} points.")

elif view == "Alternatives":
    rows = {}
    for label, a in (("Lower risk", alt_["lower_risk"]), ("Recommended", alt_["recommended"]), ("Higher return", alt_["higher_return"])):
        rows[f"{label} · {a['equity_share']:.0%} equity"] = {
            "Expected return a year": money(a["expected_return_usd"]),
            "Against the objective": money(-a["shortfall_usd"], signed=True) + " a year",
            "Worst historical crisis": "−" + money(a["worst_crisis_usd"]),
            "Our stagflation scenario": "−" + money(a["hypothetical_usd"]),
            "Average loss on a 1-in-100 day": "−" + money(a["es99_ttc_usd"]),
            "Income a year": money(a["income_usd"]),
            "Inside every risk limit": "yes" if a["within_limits"] else "no"}
    st.dataframe(pd.DataFrame(rows), alt="The recommendation and two alternatives in dollars")
    lo, hi, rec = alt_["lower_risk"], alt_["higher_return"], alt_["recommended"]
    say(f"Going to {lo['equity_share']:.0%} equity would save about "
                    f"{money(rec['worst_crisis_usd'] - lo['worst_crisis_usd'])} in a 2008-type crisis but miss the "
                    f"objective by {money(lo['shortfall_usd'])} a year. Going to {hi['equity_share']:.0%} would add "
                    f"{money(hi['expected_return_usd'] - rec['expected_return_usd'])} a year and cost "
                    f"{money(hi['worst_crisis_usd'] - rec['worst_crisis_usd'])} more in that crisis, breaking the limit.")

else:
    df = fr.reset_index()
    df["equity"] = df["equity_share"] * 100
    df["loss"] = df["d2_loss"] * 100
    df["ret"] = df["forward_return"] * 100
    df["pick"] = np.where(np.isclose(df["equity_share"], eq), "recommended", "other equity shares")
    pts = alt.Chart(df).mark_circle(size=150).encode(
        x=alt.X("loss:Q", title="Worst crisis loss with today's weights (%)", scale=alt.Scale(zero=False), axis=alt.Axis(tickCount=6)),
        y=alt.Y("ret:Q", title="Expected return after costs (% a year)", scale=alt.Scale(zero=False)),
        color=alt.Color("pick:N", scale=alt.Scale(domain=["recommended", "other equity shares"], range=[ACCENT, GREY]),
                        legend=alt.Legend(title=None, orient="bottom")),
        tooltip=[alt.Tooltip("equity:Q", title="equity %"), alt.Tooltip("loss:Q", format=".1f"), alt.Tooltip("ret:Q", format=".2f")])
    labels = alt.Chart(df).mark_text(dx=10, dy=-10, color="#5B6573").encode(x="loss:Q", y="ret:Q", text=alt.Text("equity:Q", format=".0f"))
    line = alt.Chart(df).mark_line(color=GREY).encode(x="loss:Q", y="ret:Q")
    req = alt.Chart(pd.DataFrame({"y": [obj["required_return"] * 100]})).mark_rule(strokeDash=[6, 4], color="#1D2733").encode(y="y:Q")
    bud = alt.Chart(pd.DataFrame({"x": [lim["crisis_budget"] * 100]})).mark_rule(color=CRIT).encode(x="x:Q")
    st.altair_chart((line + pts + labels + req + bud).properties(height=340), alt="Why this mix")
    say(f"Each dot is a portfolio with a different share in stocks (the number beside it). Higher means more expected "
        f"return; further right means a bigger loss in a crisis. We choose the safest dot that is **above the dashed line** "
        f"(what the fund needs) and **left of the red line** (the most the fund may lose in a crisis). That is "
        f"**{eq:.0%} in stocks**. We agreed this way of choosing before looking at the latest data.")
    t = n["ten_year"]
    st.caption(f"Looking ten years ahead: about a {t['p_objective']:.0%} chance that the fund beats its inflation + 3.5% "
               f"target, and a {t['p_real_value_below_80']:.0%} chance that, after paying for scholarships, it is worth "
               "less than 80% of today in real terms.")
