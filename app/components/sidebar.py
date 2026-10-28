"""Shared sidebar (mandatory component M1): every page reads the same Controls."""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from components.data import BACKTEST_FILES, candidate_weights, candidates, config, jsonfile, status
from quantedge.paths import ARTIFACTS

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
    portfolio: str = ""                      # candidate name, or CUSTOM
    weights: dict | None = None              # weights of the selected portfolio (normalised later)

    @property
    def is_recommended(self) -> bool:
        return self.portfolio == status().get("focus_portfolio")


CUSTOM = "Custom weights"


def sidebar() -> Controls:
    cfg = config()
    st.markdown(PAGE_STYLE, unsafe_allow_html=True)
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
        focus = s.get("focus_portfolio", "")
        names = [focus, *[c for c in candidates() if c != focus], CUSTOM] if focus else [CUSTOM]
        portfolio = st.selectbox("Portfolio", names, format_func=lambda n: f"{n} (recommended)" if n == focus else n,
                                 help="Precomputed results are for the recommended portfolio; other choices are "
                                      "checked live on the Risk dashboard.")
        if portfolio != focus:
            st.caption("Checked live on the **Risk dashboard**; the other pages show the recommended portfolio.")
        base = candidate_weights(focus) if focus else None
        if portfolio == CUSTOM:
            with st.expander("Custom weights (%)", expanded=True):
                weights = {t: st.number_input(t, 0.0, 100.0, round(float(base.get(t, 0.0)) * 100 if base is not None
                                                                    else 100 / len(cfg.universe), 1), 0.5, key=f"w_{t}")
                           for t in cfg.universe}
                st.caption(f"Total {sum(weights.values()):.1f}% (rescaled to 100%).")
        else:
            w = candidate_weights(portfolio)
            weights = None if w is None else {k: float(v) for k, v in w.items()}
        st.caption(f"Data to {s.get('data_end', '?')} · analysis to {s.get('analysis_end', '?')}")
        st.caption("Final-test period (2023+) locked until the methodology freeze.")
    return Controls(alpha, model, window, float(nav), horizon, f"{dates[0]}-01-01", f"{dates[1]}-12-31",
                    portfolio, weights)


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
