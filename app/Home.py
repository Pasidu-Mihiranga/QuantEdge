"""Serendib University Endowment: the committee app (entry point and navigation).

Run with `make run` (or `.venv/bin/python -m streamlit run app/Home.py`). The app reads data/artifacts only: no
downloads, no model fitting. Five pages in the sidebar; technical detail sits behind one dropdown on the last.
"""

import streamlit as st

st.set_page_config(page_title="Serendib Endowment", page_icon=":material/account_balance:", layout="wide")

from components.ui import style  # noqa: E402  (after set_page_config)

style()
page = st.navigation([
    st.Page("views/recommendation.py", title="Our recommendation", icon=":material/verified:", default=True),
    st.Page("views/crises.py", title="What can go wrong", icon=":material/thunderstorm:", url_path="crises"),
    st.Page("views/risk.py", title="Risk and confidence", icon=":material/monitoring:", url_path="risk"),
    st.Page("views/portfolio.py", title="Compare portfolios", icon=":material/compare_arrows:", url_path="portfolio"),
    st.Page("views/assumptions.py", title="Assumptions & Limitations", icon=":material/info:", url_path="assumptions"),
], position="sidebar")
page.run()
