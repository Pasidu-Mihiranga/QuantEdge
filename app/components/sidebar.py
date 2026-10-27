"""Shared sidebar (mandatory component M1): every page reads the same Controls."""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from components.data import BACKTEST_FILES, config, status

PAGE_STYLE = """
<style>
.qe-banner {padding: 0.6rem 0.9rem; border-radius: 6px; margin-bottom: 0.8rem; font-weight: 600;}
.qe-provisional {background: #fff4e5; color: #8a4b00; border: 1px solid #f5c27a;}
.qe-locked {background: #eef1f5; color: #39424e; border: 1px solid #c9d1db;}
</style>
"""


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
    st.markdown(PAGE_STYLE, unsafe_allow_html=True)
    with st.sidebar:
        st.header("Controls")
        alpha = st.select_slider("Confidence level", options=[0.90, 0.95, 0.99], value=0.99,
                                 format_func=lambda a: f"{a:.0%}")
        model = st.selectbox("VaR methodology", list(BACKTEST_FILES), index=list(BACKTEST_FILES).index("GARCH-FHS"))
        window = st.selectbox("Estimation window (days)", [500], help="Precomputed: 500 days. 250/1000 to follow.")
        dates = st.slider("Backtest date range (year)", 2008, 2022, (2008, 2022))
        nav = st.number_input("NAV (USD)", min_value=1_000_000, value=int(cfg.nav_usd), step=1_000_000)
        horizon = st.radio("Horizon", [1], format_func=lambda h: f"{h} day", horizontal=True,
                           help="10-day figures are added with the horizon module.")
        s = status()
        st.caption(f"Data to {s.get('data_end', '?')} · analysis to {s.get('analysis_end', '?')}")
        st.caption("Final-test period (2023+) locked until the methodology freeze.")
    return Controls(alpha, model, window, float(nav), horizon, f"{dates[0]}-01-01", f"{dates[1]}-12-31")


def provisional_banner() -> None:
    s = status()
    if s.get("provisional", True):
        st.markdown(
            f"<div class='qe-banner qe-provisional'>Provisional: results use the top-ranked candidate "
            f"({s.get('focus_portfolio', 'n/a')}). {s.get('provisional_reason', '')}.</div>",
            unsafe_allow_html=True)


def usd(x: float) -> str:
    return f"${x:,.0f}"


def pct(x: float, d: int = 2) -> str:
    return f"{x:.{d}%}"
