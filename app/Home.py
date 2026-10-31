"""Serendib University Endowment: the committee app (entry point and navigation).

Run with `make run` (or `.venv/bin/python -m streamlit run app/Home.py`). The app reads data/artifacts only: no
downloads, no model fitting. Five committee pages, then five technical pages in their own sidebar section.
"""

import streamlit as st

st.set_page_config(page_title="Serendib Endowment", page_icon=":material/account_balance:", layout="wide")

from components.ui import style  # noqa: E402  (after set_page_config)
from quantedge.paths import ARTIFACTS  # noqa: E402

style()
pages = {
    "For the committee": [
        st.Page("views/recommendation.py", title="Our recommendation", icon=":material/verified:", default=True),
        st.Page("views/crises.py", title="What can go wrong", icon=":material/thunderstorm:", url_path="crises"),
        st.Page("views/risk.py", title="Risk and confidence", icon=":material/monitoring:", url_path="risk"),
        st.Page("views/portfolio.py", title="Compare portfolios", icon=":material/compare_arrows:", url_path="portfolio"),
        st.Page("views/assumptions.py", title="Assumptions & Limitations", icon=":material/info:", url_path="assumptions"),
    ],
    "Technical detail": [
        st.Page("technical/data_quality.py", title="Data and quality checks", icon=":material/dataset:", url_path="data"),
        st.Page("technical/models.py", title="All risk models, 2008–2022", icon=":material/leaderboard:", url_path="models"),
        st.Page("technical/tail_evt.py", title="Tail risk (EVT)", icon=":material/show_chart:", url_path="evt"),
        st.Page("technical/innovation.py", title="Regimes, overlay, copula, FX", icon=":material/lightbulb:",
                url_path="innovation"),
        st.Page("technical/methodology.py", title="Methodology", icon=":material/menu_book:",
                url_path="methodology"),
    ],
}
pages["Explore"] = [st.Page("side/custom.py", title="Try your own portfolio", icon=":material/tune:", url_path="custom")]
if (ARTIFACTS / "swarm_comparison.json").exists():         # appears once real simulation runs exist
    pages["Explore"].append(st.Page("side/swarm.py", title="Crowd simulation", icon=":material/groups:", url_path="crowd"))
page = st.navigation(pages, position="sidebar")
st.sidebar.caption("Team Gmora · QuantEdge 1.0")
page.run()
