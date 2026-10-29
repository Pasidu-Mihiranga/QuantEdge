"""Serendib University Endowment: the committee app (entry point and navigation).

Run with `streamlit run app/Home.py`. The app reads data/artifacts only: no downloads, no model fitting.
Three sections, read top to bottom: the decision, the evidence for it, and a technical appendix.
"""

import streamlit as st

st.set_page_config(page_title="Serendib Endowment", page_icon=":material/account_balance:", layout="wide")

from components.ui import numbers, style  # noqa: E402  (after set_page_config)

style()
pages = {
    "Decision": [
        st.Page("views/recommendation.py", icon=":material/verified:", title="What do we recommend?", default=True),
        st.Page("views/crises.py", icon=":material/thunderstorm:", title="What can go wrong?", url_path="crises"),
    ],
    "Evidence": [
        st.Page("views/mandate.py", icon=":material/handshake:", title="What did we promise?", url_path="mandate"),
        st.Page("views/portfolio.py", icon=":material/pie_chart:", title="How is the money invested?", url_path="portfolio"),
        st.Page("views/bad_day.py", icon=":material/trending_down:", title="How bad can a bad day get?", url_path="risk"),
        st.Page("views/trust.py", icon=":material/fact_check:", title="Can we trust the risk model?", url_path="backtesting"),
        st.Page("views/assumptions.py", icon=":material/info:", title="Assumptions & Limitations", url_path="assumptions"),
    ],
    "Technical appendix": [
        st.Page("views/data_quality.py", icon=":material/database:", title="Data and quality checks", url_path="data"),
        st.Page("views/models.py", icon=":material/stacked_line_chart:", title="All risk models", url_path="models"),
        st.Page("views/tail_evt.py", icon=":material/ssid_chart:", title="Tail risk (EVT) diagnostics", url_path="evt"),
        st.Page("views/innovation.py", icon=":material/science:", title="Regimes, overlay, copula, FX", url_path="innovation"),
        st.Page("views/methodology.py", icon=":material/menu_book:", title="Methodology and AI disclosure", url_path="methodology"),
    ],
}
page = st.navigation(pages)
n = numbers()
with st.sidebar:
    st.caption(f"USD 10M endowment · decision date {n.get('decision_date', '?')} · data to {n.get('data_end', '?')}")
    st.caption("Methodology frozen before the 2023–2026 test (tag `methodology-freeze-v1`).")
page.run()
