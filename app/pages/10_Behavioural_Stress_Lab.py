import streamlit as st

from components.sidebar import sidebar
from quantedge.paths import DATA

st.set_page_config(page_title="Behavioural Stress Lab", layout="wide")
sidebar()
st.title("Behavioural Stress Lab (MiroFish), exploratory")
st.markdown("<div class='qe-banner qe-locked'>Exploratory layer: it never replaces VaR, ES, EVT or backtesting. "
            "This page reads cached runs only and makes no LLM calls.</div>", unsafe_allow_html=True)

cache = DATA / "behavioral"
if not cache.exists() or not any(cache.glob("*.parquet")):
    st.info("No MiroFish runs cached yet. Steps 19–20 are optional and start with the Week-2 feasibility gate "
            "(local free LLM, run time, schema validity). If the gate fails, MiroFish is dropped and documented.")
