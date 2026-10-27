import pandas as pd
import streamlit as st

from components.sidebar import sidebar
from quantedge.reports.limitations import LIMITATIONS

st.set_page_config(page_title="Assumptions & Limitations", layout="wide")
sidebar()
st.title("Assumptions & Limitations")
st.caption("Each item gives the assumption, why it matters and how we mitigate it. The same list appears in the report.")

for group, items in LIMITATIONS.items():
    st.subheader(group)
    st.dataframe(pd.DataFrame(items, columns=["Assumption", "Why it matters", "Mitigation"]),
                 width="stretch", hide_index=True)
