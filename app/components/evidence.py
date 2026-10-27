"""Decision evidence for the app: a cached wrapper around quantedge.decision.evidence."""

from __future__ import annotations

import streamlit as st

from components.data import config
from quantedge.decision.evidence import build


@st.cache_data
def verdict():
    b = build(config())
    if b is None:
        return None, None
    return b.verdict, {"evidence": b.evidence, "worst_hist_loss": b.worst_hist_loss, "champion": b.champion,
                       "var99": b.var99, "bundle": b}
