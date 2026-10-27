import json

import plotly.express as px
import streamlit as st

from components.charts import LAYOUT
from components.data import csv, parquet, require
from components.sidebar import sidebar
from quantedge.paths import MANIFEST

st.set_page_config(page_title="Data & Quality", layout="wide")
sidebar()
st.title("Data sources, cleaning and quality")

st.subheader("Sources and snapshot manifest")
if MANIFEST.exists():
    files = json.loads(MANIFEST.read_text(encoding="utf-8"))["files"]
    st.dataframe([{k: f[k] for k in ("file", "source", "rows", "first_date", "last_date", "downloaded_utc")}
                  | {"sha256": f["sha256"][:12] + "…"} for f in files], width="stretch", hide_index=True)
st.caption("Yahoo Finance (yfinance, Adj Close and Close kept) and FRED. The app reads only this frozen, hashed snapshot.")

log = csv("cleaning_log.csv")
if require(log, "The cleaning log"):
    st.subheader("Cleaning log")
    st.dataframe(log, width="stretch", hide_index=True)

prices = parquet("clean_prices.parquet")
flags = parquet("quality_flags.parquet")
if require(prices, "Clean prices") and flags is not None:
    st.subheader("Prices with quality flags (flagged, never deleted)")
    norm = prices / prices.iloc[0]
    fig = px.line(norm, log_y=True, title="Adjusted prices (start = 1, log scale)")
    for _, f in flags[flags.rule != "structural_break"].iterrows():
        fig.add_vline(x=f.date, line_width=1, line_dash="dot", line_color="#c0392b")
    st.plotly_chart(fig.update_layout(**LAYOUT), width="stretch")
    st.dataframe(flags, width="stretch", hide_index=True)
    st.caption("Every flag was checked against market events (2008, Brexit, COVID, April 2025 …); genuine moves are kept "
               "because they are the tail risk we must model.")

stat = parquet("stationarity.parquet")
facts = parquet("stylised_facts.parquet")
if stat is not None:
    st.subheader("Stationarity (ADF + KPSS), data to 2022")
    st.dataframe(stat.round(4), width="stretch")
if facts is not None:
    st.subheader("Stylised facts of log returns")
    st.dataframe(facts.round(4), width="stretch")
    st.caption("Fat tails (Jarque-Bera) and volatility clustering (Ljung-Box on r², ARCH-LM) everywhere: "
               "this is why GARCH and EVT are needed.")
