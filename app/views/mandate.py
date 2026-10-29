"""Evidence: what the fund promised (the Investment Policy Statement) and why the limits are what they are."""

import pandas as pd
import streamlit as st

from components.content import DECISIONS
from components.ui import artifact, esc, money, need_numbers, note, pct

n = need_numbers()
obj, lim, nav = n["objective"], n["limits"], n["nav_usd"]

st.title("What did we promise?")
st.markdown("The Investment Policy Statement: what the endowment needs to earn, how much it may lose, and the ten "
            "decisions the team locked before the 2023–2026 test.")

st.markdown("##### The return objective: US inflation + 3.5% a year")
c = st.columns(4)
c[0].metric("Spending (scholarships, research)", pct(obj["spending"]))
c[1].metric("Real growth", pct(obj["real_growth"]))
c[2].metric("Expected inflation (10-year breakeven)", pct(obj["inflation_breakeven"], 2))
c[3].metric("Required return", pct(obj["required_return"], 2))
st.caption("Required = (1 + spending) × (1 + growth) × (1 + inflation) − 1. Inflation is the market's own 10-year "
           f"forecast on {n['data_end']}. The expected return it is compared with is already after fees and taxes.")

st.markdown("##### The risk limits")
rows = [("Crisis budget (worst loss in any crisis)", pct(lim["crisis_budget"], 0), money(lim["crisis_budget"] * nav),
         "The committee's preference (D2): the largest crisis loss that still lets the fund grow"),
        ("Volatility through the cycle", pct(lim["vol_max"], 2), "—", "Read from the frontier where the crisis loss equals the budget"),
        ("Average loss on a 1-in-100 day, through the cycle", pct(lim["es99_max"], 2), money(lim["es99_max"] * nav),
         "Same point; 2004–2018 data including 2008, so a calm year does not loosen it"),
        ("Equity share", "≤ 50%", "—", "Conservative profile"),
        ("Largest share of tail risk per fund", "≤ 40%", "—", "D8 position sizing")]
st.table(pd.DataFrame(rows, columns=["Limit", "Value", "In dollars", "Where it comes from"]).set_index("Limit"))
st.caption(f"The volatility and tail-loss limits are recalibrated from the 25% budget at the decision date: a 25% budget "
           f"allows about {lim['equity_at_budget']:.0%} equity. At end-2022 the same calculation gave 8.40% and 2.23%.")

with st.expander("Why the limits changed from the first draft (IPS v1 → v2)"):
    cal = artifact("limit_calibration.parquet")
    st.markdown(esc("The first draft set volatility ≤ 8%, crisis loss ≤ 20% and 1-in-100-day average loss ≤ 1.5%, before "
                    "any evidence. On the same set of portfolios those three limits allowed about 34%, 24% and 21% equity: "
                    "three limits, three answers, because a 1-in-100-day loss is about four times daily volatility. The "
                    "agreed limits are all read from one preference (the 25% budget), so they agree by construction. Under "
                    "the first draft no portfolio fitted the limits at all. The change was made on data up to 2022, before "
                    "the test."))
    if cal is not None:
        t = cal[["vol_ann", "es99_1d", "worst_crisis_loss"]].rename(columns={
            "vol_ann": "volatility", "es99_1d": "1-in-100-day average loss", "worst_crisis_loss": "worst crisis loss"})
        t.index = [f"{x:.0%} equity" for x in t.index]
        st.dataframe(t.style.format("{:.2%}"), width="stretch")
        st.caption("End-2022 frontier, through-the-cycle measures (notebook 03 §4, reproduced by the pipeline).")

st.markdown("##### The ten decisions the team locked before the test")
st.table(pd.DataFrame(DECISIONS, columns=["#", "Decision", "Agreed value", "Plausible range", "Why"]).set_index("#"))
note("Every decision records one value (so the verdict is mechanical) and a range (so the committee can see how much "
     "it matters). Signed and locked on 29 October 2026; any later change would be logged as a deviation.")
