"""Serendib University Endowment: the committee app (entry point and navigation).

Run with `streamlit run app/Home.py`. The app reads data/artifacts only: no downloads, no model fitting.
Three sections, read top to bottom: the decision, the evidence for it, and a technical appendix.
"""

import streamlit as st

st.set_page_config(page_title="Serendib Endowment", layout="wide")

from components.ui import numbers, style  # noqa: E402  (after set_page_config)

style()
pages = {
    "Decision": [
        st.Page("views/recommendation.py", title="What do we recommend?", default=True),
        st.Page("views/crises.py", title="What can go wrong?", url_path="crises"),
    ],
    "Evidence": [
        st.Page("views/mandate.py", title="What did we promise?", url_path="mandate"),
        st.Page("views/portfolio.py", title="How is the money invested?", url_path="portfolio"),
        st.Page("views/bad_day.py", title="How bad can a bad day get?", url_path="risk"),
        st.Page("views/trust.py", title="Can we trust the risk model?", url_path="backtesting"),
        st.Page("views/assumptions.py", title="Assumptions & Limitations", url_path="assumptions"),
    ],
    "Technical appendix": [
        st.Page("views/data_quality.py", title="Data and quality checks", url_path="data"),
        st.Page("views/models.py", title="All risk models", url_path="models"),
        st.Page("views/tail_evt.py", title="Tail risk (EVT) diagnostics", url_path="evt"),
        st.Page("views/innovation.py", title="Regimes, overlay, copula, FX", url_path="innovation"),
        st.Page("views/methodology.py", title="Methodology and AI disclosure", url_path="methodology"),
    ],
}
page = st.navigation(pages)
n = numbers()
with st.sidebar:
    st.caption(f"USD 10M endowment · decision date {n.get('decision_date', '?')} · data to {n.get('data_end', '?')}")
    st.caption("Methodology frozen before the 2023–2026 test (tag `methodology-freeze-v1`).")
page.run()
