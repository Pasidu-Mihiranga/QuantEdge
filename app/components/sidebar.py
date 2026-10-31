"""Shared sidebar (mandatory component M1): every page reads the same Controls."""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from components.data import BACKTEST_FILES, config, jsonfile, status
from quantedge.paths import ARTIFACTS


@dataclass(frozen=True)
class Controls:
    alpha: float
    model: str
    window: int
    nav: float
    horizon: int
    start: str
    end: str


def sidebar() -> Controls:
    cfg = config()
    with st.sidebar:
        st.header("Controls")
        alpha = st.select_slider("Confidence level", options=[0.90, 0.95, 0.99], value=0.99,
                                 format_func=lambda a: f"{a:.0%}")
        champion = jsonfile("champion.json").get("champion", "Conditional EVT")
        models = list(BACKTEST_FILES)
        model = st.selectbox("VaR methodology", models, index=models.index(champion) if champion in models else 0,
                             help=f"Default: the validated champion ({champion}).")
        windows = [w for w in (250, 500, 1000) if (ARTIFACTS / f"backtest_selection_val_{w}.parquet").exists()] or [500]
        window = st.selectbox("Estimation window (days)", windows, index=windows.index(500) if 500 in windows else 0,
                              help="Backtests are precomputed for each window; 500 days is the official choice.")
        dates = st.slider("Backtest date range (year)", 2008, 2022, (2008, 2022))
        nav = st.number_input("NAV (USD)", min_value=1_000_000, value=int(cfg.nav_usd), step=1_000_000)
        horizon = st.radio("Horizon", [1, 10], format_func=lambda h: f"{h} day{'s' if h > 1 else ''}",
                           horizontal=True, help="10-day figures: simulated GARCH paths and overlapping history.")
        s = status()
        st.caption(f"Data to {s.get('data_end', '?')} · analysis to {s.get('analysis_end', '?')}")
        st.caption("This page shows the pre-freeze periods (2008–2022).")
    return Controls(alpha, model, window, float(nav), horizon, f"{dates[0]}-01-01", f"{dates[1]}-12-31")


def usd(x: float) -> str:
    return f"${x:,.0f}"


def pct(x: float, d: int = 2) -> str:
    return f"{x:.{d}%}"
