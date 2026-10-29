"""Evidence: Assumptions & Limitations (booklet item 6, graded): what the model does not capture, in plain language."""

import pandas as pd
import streamlit as st

from components.content import DECISIONS, NOT_CAPTURED
from components.ui import esc, need_numbers, note

n = need_numbers()
st.title("Assumptions & Limitations")
st.markdown("What this analysis does **not** capture, and the assumptions behind every number. The same list is in "
            "the report.")

st.markdown("##### What the model does not capture")
for title, text in NOT_CAPTURED:
    st.markdown(esc(f"**{title}.** {text}"))

st.markdown("##### The assumptions we chose, and how much they matter")
rows = [(d, name, value, rng) for d, name, value, rng, _ in DECISIONS if d in ("D1", "D2", "D3", "D4", "D5", "D8", "D10")]
st.table(pd.DataFrame(rows, columns=["#", "Assumption", "Value used", "Plausible range"]).set_index("#"))
rob = n["robustness"]
note(esc(f"<b>Sensitivity of the verdict.</b> Over the {sum(rob.values())} combinations of the return assumptions (equity "
         f"premium 3.5–5.5%, AGG spread 0.3–0.9%, AGG taxed or not) the verdict is ACCEPT in {rob.get('ACCEPT', 0)}, "
         f"ADJUST in {rob.get('ADJUST', 0)} and REJECT in {rob.get('REJECT', 0)}. The risk limits pass in every case: "
         "only the return objective is sensitive.").replace("\\$", "$"), "warn")

st.markdown("##### How the numbers were made")
st.markdown(esc(
    "- **Data:** daily prices of the seven funds (Yahoo Finance) and US macro series (FRED), November 2004 to "
    f"{n['data_end']}, frozen and hashed. Suspect days are flagged, never deleted; every flag was checked against market news.\n"
    "- **No look-ahead:** every forecast for a day uses only earlier data; portfolio weights are those actually held.\n"
    "- **Three periods:** 2004–2018 to build, 2019–2022 to choose, 2023–2026 to test once. The rules and the inputs were "
    "locked and the methodology frozen before the test.\n"
    "- **Two independent codes:** each analysis notebook was written separately from the app's code, and both give the "
    "same verdict, the same backtest results and the same portfolio."))
