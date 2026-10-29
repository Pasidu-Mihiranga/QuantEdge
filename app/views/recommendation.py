"""Decision page 1: the verdict in one glance, then four views to explore it (one at a time)."""

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from components.ui import artifact, esc, money, need_numbers, pct, per_year

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
                        "objective. Use **What would change it** below to test our assumptions."))

mv = n["model_validity"]
with st.container(horizontal=True):
    st.metric("Expected return a year", pct(n["expected_return"], 2), f"required {pct(obj['required_return'], 2)}",
              delta_color="off", delta_arrow="off", border=True)
    st.metric("Worst crisis on record", f"−{money(risk['worst_crisis_loss'] * nav)}",
              f"{risk['worst_crisis']} · budget {money(lim['crisis_budget'] * nav)}", delta_color="off", delta_arrow="off",
              border=True)
    st.metric("A 1-in-100 bad day", f"−{money(risk['es99_ttc'] * nav)}", "average loss, through the cycle",
              delta_color="off", delta_arrow="off", border=True)
    st.metric("Risk model on unseen data", "Passed" if mv.get("passes") else "Failed",
              f"{mv.get('exceptions')} breaches vs {mv.get('expected', 0):.1f} expected, 2023–26", delta_color="off",
              delta_arrow="off", border=True)

# ---------- explore, one view at a time ----------
VIEWS = {"The mix": ":material/pie_chart:", "What would change it": ":material/tune:",
         "Alternatives": ":material/compare_arrows:", "How the rule decided": ":material/rule:"}
view = st.segmented_control("Explore", list(VIEWS), default="The mix", format_func=lambda v: f"{VIEWS[v]} {v}",
                            label_visibility="collapsed", required=True, key="rec_view")

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

elif view == "What would change it":
    wi = artifact("decision_whatif.parquet")
    st.markdown("The verdict rests on two numbers nobody can observe exactly: the extra return stocks earn over bonds "
                "(the equity risk premium) and the level of real interest rates. Move them and see what the locked rule says.")
    c1, c2, c3 = st.columns([2, 2, 1.3], vertical_alignment="bottom")
    erp = c1.slider("Equity risk premium", 3.0, 6.0, 4.5, 0.25, format="%.2f%%", key="wi_erp",
                    help="Our locked assumption is 4.5% (decision D4); published estimates are roughly 4.2–5.5%.") / 100
    dy = c2.slider("Change in real interest rates", -1.0, 1.0, 0.0, 0.1, format="%+.1f pts", key="wi_dy",
                   help="Shifts the 10-year Treasury yield with inflation unchanged; today's 10-year TIPS yield is "
                        f"{pct(obj['tips'], 2)}.") / 100
    taxed = c3.toggle("AGG income taxed", value=False, key="wi_tax", help="Whether AGG's interest bears 15% US withholding tax.")
    s = wi[np.isclose(wi.erp, erp) & np.isclose(wi.dy, dy) & np.isclose(wi.agg_withholding, 0.15 if taxed else 0.0)]
    f = s.set_index("equity_share")["forward_return"]
    inside = fr["within_limits"]
    ok = [x for x in f.index if f[x] >= obj["required_return"] and inside[x]]
    near = [x for x in f.index if f[x] >= obj["required_return"] and fr.loc[x, "d2_loss"] <= lim["crisis_budget"] + 0.05 + 1e-9]
    v, point = ("ACCEPT", min(ok)) if ok else (("ADJUST", min(near)) if near else ("REJECT", None))
    best = max(x for x in f.index if inside[x])
    colour = {"ACCEPT": "green", "ADJUST": "orange", "REJECT": "red"}[v]
    with st.container(horizontal=True, vertical_alignment="center"):
        st.badge(v, color=colour, icon={"ACCEPT": ":material/check_circle:", "ADJUST": ":material/tune:",
                                        "REJECT": ":material/cancel:"}[v])
        st.markdown(esc(f"Best portfolio inside the limits ({best:.0%} equity) earns **{pct(f[best], 2)}** against "
                        f"**{pct(obj['required_return'], 2)}** required: "
                        f"{money((f[best] - obj['required_return']) * nav, signed=True)} a year."
                        + (f" The rule picks **{point:.0%} equity**." if point is not None else "")))
    df = pd.DataFrame({"equity": f.index * 100, "expected": f.values * 100,
                       "status": ["inside the limits" if inside[x] else "breaks the crisis budget" for x in f.index]})
    line = alt.Chart(df).mark_line(color=GREY).encode(x=alt.X("equity:Q", title="Equity share (%)", axis=alt.Axis(values=list(range(20, 55, 5)))),
                                                      y=alt.Y("expected:Q", title="Expected return (% a year)",
                                                              scale=alt.Scale(zero=False)))
    pts = alt.Chart(df).mark_circle(size=140).encode(
        x="equity:Q", y="expected:Q", tooltip=["equity:Q", alt.Tooltip("expected:Q", format=".2f")],
        color=alt.Color("status:N", scale=alt.Scale(domain=["inside the limits", "breaks the crisis budget"],
                                                    range=[ACCENT, GREY]), legend=alt.Legend(title=None, orient="bottom")))
    req = alt.Chart(pd.DataFrame({"y": [obj["required_return"] * 100]})).mark_rule(strokeDash=[6, 4], color="#1D2733").encode(y="y:Q")
    st.altair_chart((line + pts + req).properties(height=300), alt="Expected return by equity share against the requirement")
    st.caption("Dashed line: the required return (US inflation + 3.5%). ACCEPT needs a blue dot on or above it. The risk "
               "limits do not depend on these assumptions; only the return side moves.")
    rows = []
    sub = wi[np.isclose(wi.agg_withholding, 0.15 if taxed else 0.0)]
    for (e, d), g in sub.groupby(["erp", "dy"]):
        ff = g.set_index("equity_share")["forward_return"]
        a = any(ff[x] >= obj["required_return"] and inside[x] for x in ff.index)
        b = any(ff[x] >= obj["required_return"] and fr.loc[x, "d2_loss"] <= lim["crisis_budget"] + 0.05 + 1e-9 for x in ff.index)
        rows.append({"erp": round(e * 100, 2), "dy": round(d * 100, 1) + 0.0, "verdict": "ACCEPT" if a else ("ADJUST" if b else "REJECT")})
    vm = pd.DataFrame(rows)
    heat = alt.Chart(vm).mark_rect().encode(
        x=alt.X("dy:O", title="Change in real interest rates (points)", axis=alt.Axis(labelAngle=0)),
        y=alt.Y("erp:O", title="Equity risk premium (%)", sort="descending"),
        color=alt.Color("verdict:N", scale=alt.Scale(domain=["ACCEPT", "ADJUST", "REJECT"], range=["#BFE3C8", "#F6DDB3", "#F3C4BF"]),
                        legend=alt.Legend(title=None, orient="bottom")),
        tooltip=["erp:O", "dy:O", "verdict:N"])
    you = alt.Chart(pd.DataFrame({"erp": [round(erp * 100, 2)], "dy": [round(dy * 100, 1) + 0.0]})).mark_point(
        shape="circle", size=180, filled=False, strokeWidth=3, color="#1D2733").encode(x="dy:O", y="erp:O")
    st.altair_chart((heat + you).properties(height=330), alt="Verdict for every combination of premium and rate change")
    st.caption("Each cell is the locked rule applied to one combination; the ring is your choice. The locked inputs "
               f"(4.5%, today's rates) sit in the ACCEPT region, close to its edge: ACCEPT is lost below a premium of "
               f"{pct(n['erp_breakeven'], 2)} or if real rates fall {n['yield_margin']['pp'] * 100:.2f} points.")

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
    st.markdown(esc(f"Going to {lo['equity_share']:.0%} equity would save about "
                    f"{money(rec['worst_crisis_usd'] - lo['worst_crisis_usd'])} in a 2008-type crisis but miss the "
                    f"objective by {money(lo['shortfall_usd'])} a year. Going to {hi['equity_share']:.0%} would add "
                    f"{money(hi['expected_return_usd'] - rec['expected_return_usd'])} a year and cost "
                    f"{money(hi['worst_crisis_usd'] - rec['worst_crisis_usd'])} more in that crisis, breaking the budget."))

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
    st.altair_chart((line + pts + labels + req + bud).properties(height=340), alt="How the rule decided")
    st.markdown(esc("Each dot is the least-risky portfolio for one equity share (the number next to it). The rule, fixed "
                    "before the test: recommend the **lowest-risk portfolio above the dashed line (the required return) "
                    "and left of the red line (the 25% crisis budget)**. If none existed but one would fit with the budget "
                    "5 points looser, the verdict would be ADJUST; otherwise REJECT."))
    t = n["ten_year"]
    st.caption(esc(f"Ten years ahead (context, not part of the rule): about a {t['p_objective']:.0%} chance that the real "
                   f"return reaches 3.5% a year; a {t['p_real_value_below_80']:.0%} chance that real value after spending "
                   f"ends below 80% of today's. A bad day here means {per_year(0.99)}."))
