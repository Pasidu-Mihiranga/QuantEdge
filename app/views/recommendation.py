"""Decision page 1: the verdict, the recommended portfolio and why, on one screen."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.ui import (
    ACCENT,
    CRIT,
    GREY,
    INK,
    MUTED,
    artifact,
    card,
    esc,
    layout,
    money,
    need_numbers,
    note,
    pct,
    per_year,
    show,
    verdict_banner,
)

n = need_numbers()
obj, lim, risk, alt = n["objective"], n["limits"], n["risk"], n["alternatives"]
nav = n["nav_usd"]
eq = n["advised_equity"]
key = n["verdict"].split()[0]

st.title("What do we recommend?")
st.caption(f"Decision date {n['decision_date']} · market data to {n['data_end']} · USD {nav / 1e6:.0f}M endowment · "
           "every number on this page comes from one file, decision_numbers.json")

if key == "ACCEPT":
    sentence = (f"Invest {eq:.0%} in equities and {1 - eq:.0%} in bonds and real assets. The portfolio is expected to earn "
                f"{pct(n['expected_return'], 2)} a year after costs, just above the {pct(obj['required_return'], 2)} that the "
                f"objective (US inflation + 3.5%) needs, and every risk limit holds.")
elif key == "ADJUST":
    sentence = ("The objective is reachable only with the crisis budget loosened. The committee must approve the amended "
                "limit before anything is implemented.")
else:
    sentence = (f"No portfolio within the risk limits is expected to earn the {pct(obj['required_return'], 2)} the objective "
                f"needs. Lower the spending rate, or wait for higher real yields.")
verdict_banner(n["verdict"], sentence)

# The four questions the committee asks (booklet p. 5: what can go wrong, how bad, how confident; plus the objective)
c1, c2, c3, c4 = st.columns(4)
with c1:
    card("Does it meet the objective?", "Yes" if n["return_margin"] >= 0 else "No",
         f"Expected {pct(n['expected_return'], 2)} vs required {pct(obj['required_return'], 2)}: "
         f"{money(abs(n['return_margin_usd']))} a year {'above' if n['return_margin'] >= 0 else 'short'}.")
with c2:
    card("Worst crisis on record?", money(risk["worst_crisis_loss"] * nav),
         f"A repeat of the {risk['worst_crisis']} crash: −{pct(risk['worst_crisis_loss'])}, "
         f"inside the {pct(lim['crisis_budget'], 0)} ({money(lim['crisis_budget'] * nav)}) crisis budget.")
with c3:
    card("How bad is a bad day?", money(risk["es99_ttc"] * nav),
         f"Average loss on the worst {per_year(0.99)} through a full cycle. In today's calmer market: "
         f"{money(n['risk_day']['es99'] * nav)}.")
with c4:
    mv = n["model_validity"]
    card("How sure are we?", "Model passed" if mv.get("passes") else "Model failed",
         f"One-shot test on {mv.get('test_start', '?')[:4]}–{mv.get('test_end', '?')[:4]}, never seen before: "
         f"{mv.get('exceptions')} bad-day breaches vs {mv.get('expected', 0):.1f} expected.")

st.write("")
left, right = st.columns([1.05, 1])
with left:
    w = pd.Series(n["weights"]).loc[lambda s: s > 1e-4].sort_values()
    names = {"SPY": "US stocks (SPY)", "EFA": "Developed-market stocks (EFA)", "EEM": "Emerging-market stocks (EEM)",
             "AGG": "US investment-grade bonds (AGG)", "GLD": "Gold (GLD)", "XLE": "Energy stocks (XLE)", "XLK": "Technology stocks (XLK)"}
    fig = go.Figure(go.Bar(x=w.values, y=[names[t] for t in w.index], orientation="h", marker_color=ACCENT,
                           text=[f"{v:.1%} · {money(v * nav)}" for v in w.values], textposition="outside",
                           hovertemplate="%{y}: %{x:.1%}<extra></extra>"))
    fig.update_xaxes(tickformat=".0%", range=[0, max(w.values) * 1.45], showgrid=False, visible=False)
    show(layout(fig, 300, "The recommended portfolio"))
    if n.get("d8_moved_to_spy", 0) > 0:
        st.caption(f"Resized so no fund carries more than 40% of the tail risk (D8): {n['d8_moved_to_spy']:.1%} moved to SPY.")
    else:
        st.caption(f"No fund carries more than 40% of the tail risk (largest: {n['largest_es_share_etf']} "
                   f"{n['largest_es_share']:.0%}), so no resizing was needed (D8).")
with right:
    ym, rob = n["yield_margin"], n["robustness"]
    total = sum(rob.values())
    st.markdown("##### What would change the verdict")
    lines = [f"- {ym['direction']} **{ym['pp'] * 100:.2f} percentage points** (10-year TIPS yield "
             f"{pct(obj['tips'], 2)} today; threshold {pct(ym['tips_threshold'], 2)}).",
             f"- The equity risk premium we assumed (4.5%) is below **{pct(n['erp_breakeven'], 2)}**.",
             f"- Across {total} combinations of our return assumptions the verdict is ACCEPT in {rob.get('ACCEPT', 0)}, "
             f"ADJUST in {rob.get('ADJUST', 0)} and REJECT in {rob.get('REJECT', 0)}."]
    st.markdown(esc("\n".join(lines)))
    if key == "ACCEPT" and rob.get("ACCEPT", 0) < total / 2 + 1:
        note("<b>A narrow ACCEPT.</b> The verdict follows the locked rule, but it depends on the assumed equity premium "
             "and on whether AGG's distributions are taxed. The committee should treat the return objective as a target "
             "that is likely, not certain, to be met.", "warn")
    t = n["ten_year"]
    st.markdown(esc(f"**Ten years ahead (context):** about a {t['p_objective']:.0%} chance that the real return reaches 3.5% a "
                    f"year, and a {t['p_real_value_below_80']:.0%} chance that the endowment's real value, after spending, "
                    f"ends below 80% of today's."))

# The verdict on one chart
fr = artifact("decision_frontier.parquet")
if fr is not None:
    st.markdown("##### How the rule decided")
    fig = go.Figure()
    colours = [ACCENT if abs(x - eq) < 1e-9 else GREY for x in fr.index]
    fig.add_scatter(x=fr["d2_loss"] * 100, y=fr["forward_return"] * 100, mode="lines+markers+text",
                    line=dict(color=GREY, width=1.5), marker=dict(size=[16 if abs(x - eq) < 1e-9 else 9 for x in fr.index],
                                                                   color=colours, line=dict(color="#fff", width=2)),
                    text=[f"{x:.0%}" for x in fr.index], textposition="bottom right", textfont=dict(color=MUTED),
                    hovertemplate="%{text} equity<br>worst crisis loss %{x:.1f}%<br>expected return %{y:.2f}%<extra></extra>",
                    showlegend=False)
    fig.add_hline(y=obj["required_return"] * 100, line=dict(color=INK, dash="dash", width=1.2),
                  annotation_text=f"required {pct(obj['required_return'], 2)}", annotation_position="top left")
    fig.add_vline(x=lim["crisis_budget"] * 100, line=dict(color=CRIT, width=1.2),
                  annotation_text=f"crisis budget {pct(lim['crisis_budget'], 0)}", annotation_position="bottom right")
    fig.update_xaxes(title="Worst crisis loss with today's weights (%)", ticksuffix="%")
    fig.update_yaxes(title="Expected return after costs (% a year)", ticksuffix="%")
    show(layout(fig, 380))
    st.caption("Each dot is a portfolio with a different share in equities (minimum risk for that share). ACCEPT needs a dot "
               "above the dashed line and left of the red one; the rule picks the one with the least risk. Left of the "
               "line means inside the budget for both the historical crises and our 'Hormuz stagflation 2027' scenario.")

st.markdown("##### The recommendation and two alternatives, in dollars a year and in a crisis")
rows = {}
for label, a in (("Lower risk", alt["lower_risk"]), ("Recommended", alt["recommended"]), ("Higher return", alt["higher_return"])):
    rows[f"{label} · {a['equity_share']:.0%} equity"] = {
        "Expected return a year": money(a["expected_return_usd"]),
        "Against the objective": (money(-a["shortfall_usd"], signed=True) + " a year"),
        "Worst historical crisis": "−" + money(a["worst_crisis_usd"]),
        "Hormuz stagflation 2027 scenario": "−" + money(a["hypothetical_usd"]),
        "Average loss on a 1-in-100 day": "−" + money(a["es99_ttc_usd"]),
        "Income a year (dividends, interest)": money(a["income_usd"]),
        "Inside every risk limit": "yes" if a["within_limits"] else "no"}
st.dataframe(pd.DataFrame(rows), width="stretch")
st.caption("Losses use today's weights held through each crisis. 'Through the cycle' figures use 2004–2018 data, which "
           "include the 2008 crisis, so a calm year does not make the limits look easier.")

st.markdown("##### Read next")
a, b, c = st.columns(3)
a.page_link("views/crises.py", label="What can go wrong? Every crisis in dollars")
b.page_link("views/trust.py", label="Can we trust the risk model? The one-shot test")
c.page_link("views/assumptions.py", label="Assumptions & Limitations")
