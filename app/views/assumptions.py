"""Assumptions & Limitations (booklet item 6, graded): what we promised, what the model does not capture, and a pointer
to the technical pages in the sidebar."""


import numpy as np
import pandas as pd
import streamlit as st

from components.content import DECISIONS, NOT_CAPTURED
from components.ui import artifact, money, need_numbers, pct, say
from quantedge.config import load_config
from quantedge.reports.limitations import LIMITATIONS

n = need_numbers()
obj, lim, nav = n["objective"], n["limits"], n["nav_usd"]

st.title("Assumptions & Limitations")
say("What the fund promised, what our analysis cannot see, and the choices behind every number, in plain language.")

st.subheader("What we promised")
with st.container(horizontal=True):
    st.metric("Return objective", "Inflation + 3.5%", f"{pct(obj['required_return'], 2)} a year today", delta_color="off",
              delta_arrow="off", border=True, help="3% for scholarships and research, plus 0.5% real growth, after US inflation "
              f"(the market's 10-year forecast: {pct(obj['inflation_breakeven'], 2)}).")
    st.metric("Crisis budget", f"−{pct(lim['crisis_budget'], 0)}", f"at most {money(lim['crisis_budget'] * nav)} in any crisis",
              delta_color="off", delta_arrow="off", border=True, help="The most the committee accepts losing in a crisis; the other limits follow from it.")
    st.metric("Bad-day limit", f"−{money(lim['es99_max'] * nav)}", "average 1-in-100-day loss", delta_color="off",
              delta_arrow="off", border=True, help="The average loss on the worst 1 day in 100, measured over years that include 2008.")
    st.metric("Equity", "≤ 50%", "no fund > 40%; bonds ≤ 65%", delta_color="off", delta_arrow="off", border=True,
              help="Limits on concentration: energy, technology and emerging markets at most 10% each, gold at most 15%.")

st.markdown("##### Every limit, and how much room is left")
cfg = load_config()
ips, risk, w = cfg.ips["limits"], n["risk"], pd.Series(n["weights"])
caps = {t: ips["asset_caps"].get(t, ips["single_asset_max"]) for t in w.index}
over = [t for t in w.index if w[t] > caps[t] + 1e-9]
equity = float(w.reindex(ips["equity_group"]).sum())
room = lambda a, b, usd=True: f"{pct(a - b, 2)}" + (f" ({money((a - b) * nav)})" if usd else "")  # noqa: E731
rows = [("Return a year (at least)", pct(obj["required_return"], 2), pct(n["expected_return"], 2),
         room(n["expected_return"], obj["required_return"]), "D1: 3% spending + 0.5% real growth + expected inflation"),
        ("Worst crisis loss (at most)", pct(lim["crisis_budget"], 0), f"{pct(risk['d2_loss'])} ({risk['worst_crisis']})",
         room(lim["crisis_budget"], risk["d2_loss"]), "D2: the committee's preference, the anchor for the next two"),
        ("Volatility, through the cycle (at most)", pct(lim["vol_max"], 2), pct(risk["vol_ttc"], 2),
         room(lim["vol_max"], risk["vol_ttc"], usd=False), "Read from the frontier where the crisis loss equals the budget"),
        ("Average loss on a 1-in-100 day, through the cycle (at most)", money(lim["es99_max"] * nav),
         money(risk["es99_ttc"] * nav), money((lim["es99_max"] - risk["es99_ttc"]) * nav),
         "Same point, on 2004–2018 data including 2008, so a calm year cannot loosen it"),
        ("Equity share (at most)", pct(ips["equity_max"], 0), pct(equity, 0), pct(ips["equity_max"] - equity, 0),
         "Conservative profile"),
        ("Per fund (at most)", "AGG 65%, GLD 15%, XLE, XLK, EEM 10%, others 40%",
         "inside every cap" if not over else f"over the cap: {', '.join(over)}", "", "D3: concentration and liquidity"),
        ("Share of tail risk per fund (at most)", pct(cfg.decision["es_share_cap"], 0),
         f"{pct(n['largest_es_share'], 0)} ({n['largest_es_share_etf']})",
         pct(cfg.decision["es_share_cap"] - n["largest_es_share"], 0), "D8: no fund dominates a very bad day")]
st.table(pd.DataFrame(rows, columns=["Limit", "Limit value", "Our portfolio", "Room left", "Where it comes from"])
         .set_index("Limit"))
st.caption(f"The volatility and bad-day limits are recalibrated from the {pct(lim['crisis_budget'], 0)} budget at the decision "
           f"date (a {pct(lim['crisis_budget'], 0)} budget allows about {lim['equity_at_budget']:.0%} equity); on end-2022 data "
           f"the same calculation gave {pct(ips['vol_ann_max'], 2)} and {pct(ips['es99_1d_max'], 2)}.")
with st.expander("Why the limits are what they are (first draft → agreed)", icon=":material/history_edu:"):
    v1 = cfg.ips["variants"]["v1_limits"]
    say(f"The first draft set volatility at most {pct(v1['vol_ann_max'], 0)}, crisis loss at most "
        f"{pct(v1['stress_drawdown_max'], 0)} and the 1-in-100-day average loss at most {pct(v1['es99_1d_max'], 1)}, before "
        "any evidence. On the same set of portfolios those three limits allowed different equity shares, because a "
        "1-in-100-day loss is not a fixed multiple of volatility: three limits, three answers, and no portfolio fitted all "
        "of them. The agreed limits are all read from one preference, the crisis budget, so they agree by construction. "
        "The change was made on data up to 2022, before the test.")
    cal = artifact("limit_calibration.parquet")
    if cal is not None:
        t = cal[["vol_ann", "es99_1d", "worst_crisis_loss"]].rename(columns={
            "vol_ann": "Volatility", "es99_1d": "1-in-100-day average loss", "worst_crisis_loss": "Worst crisis loss"})
        t.index = [f"{x:.0%} equity" for x in t.index]
        st.dataframe(t.style.format("{:.2%}"), width="stretch")
        st.caption("End-2022 frontier, through-the-cycle measures (notebook 03 §4, reproduced by the pipeline). The agreed "
                   f"limits are the row where the worst crisis loss reaches {pct(lim['crisis_budget'], 0)}.")

st.subheader("What the model does not capture")
# The tax card states what the assumption is worth, from the same what-if table as the first page.
wi = artifact("decision_whatif.parquet")
at_d = wi[np.isclose(wi.erp, cfg.ips["forward"]["erp"]) & np.isclose(wi.dy, 0.0)]
taxed = at_d[np.isclose(at_d.agg_withholding, 0.15)].set_index("equity_share")["forward_return"]
TAX = ("Taxes and costs", "Fund fees and US withholding tax on dividends (15%) are included. We assume the bond fund's interest "
       f"is not taxed; if it were, the expected return at {n['advised_equity']:.0%} equity would be "
       f"{pct(float(taxed.loc[n['advised_equity']]), 2)}, below the {pct(obj['required_return'], 2)} needed, and "
       + ("no portfolio inside the limits would meet the objective: the verdict would be REJECT. A tax adviser must confirm "
          "this before money is invested." if taxed.max() < obj["required_return"] else
          "the recommendation would change. A tax adviser must confirm this before money is invested."))
cols = st.columns(2, gap="medium")
for i, (title, text) in enumerate(TAX if t == "Taxes and costs" else (t, x) for t, x in NOT_CAPTURED):
    with cols[i % 2].container(border=True):
        st.markdown(f"**{title}**")
        st.caption(text.replace("$", "\\$"))
with st.expander(f"The full list ({sum(len(v) for v in LIMITATIONS.values())} items), with what we do about each",
                 icon=":material/checklist:"):
    st.table(pd.DataFrame([(grp, a, b, c) for grp, items in LIMITATIONS.items() for a, b, c in items],
                          columns=["Area", "Assumption or limitation", "What it can change", "What we do about it"])
             .set_index("Area"))

rob = n["robustness"]
st.info(f"Our return assumptions decide the verdict: over {sum(rob.values())} combinations it is ACCEPT in {rob.get('ACCEPT', 0)}, "
        f"ADJUST in {rob.get('ADJUST', 0)}, REJECT in {rob.get('REJECT', 0)}. The risk limits hold in every case. Try it "
        "yourself on 'Our recommendation', under What would change it.", icon=":material/tune:")

with st.expander("The choices we made, and why", icon=":material/gavel:"):
    st.table(pd.DataFrame([d[1:] for d in DECISIONS if d[0] not in ("D6", "D7")],
                          columns=["Choice", "What we chose", "Reasonable range", "Why"]).set_index("Choice"))
    st.caption("Agreed and signed on 29 October 2026, before the final 2023–2026 test was run.")

with st.expander("How the numbers were made", icon=":material/construction:"):
    say(f"- **Data:** daily prices of the seven funds (Yahoo Finance) and US economic data (FRED), November 2004 to "
        f"{n['data_end']}. Unusual days were checked against the news and kept, never deleted.\n"
        "- **No hindsight:** every forecast uses only information available at the time.\n"
        "- **A fair test:** 2004–2018 to build the models, 2019–2022 to choose between them, 2023–2026 to test them once, "
        "after every choice was fixed.\n"
        "- **Checked twice:** every result was computed by two separately written programs, which agree.")

st.subheader("Technical details")
say("The full technical detail has its own pages under **Technical detail** in the sidebar: data and quality checks, every "
    "risk model, tail-risk diagnostics, our innovation work (regimes, a risk overlay, a copula and the currency view) and "
    "the methodology.")
