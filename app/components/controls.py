"""The booklet's sidebar controls (p. 5): confidence level, VaR methodology and backtest date range.

Shown only on the pages they change, so a control never appears where it does nothing."""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from components.ui import jsonfile

MODELS = ["Historical", "Normal", "Student-t", "Cornish-Fisher", "EVT", "Monte Carlo", "GARCH-FHS", "GJR-FHS",
          "Conditional EVT", "GJR conditional EVT"]
FILES = {m: m.lower().replace(" ", "_").replace("-", "_") for m in MODELS}


@dataclass(frozen=True)
class RiskControls:
    alpha: float
    model: str
    start: int
    end: int


def risk_controls(dates: bool = True) -> RiskControls:
    champion = jsonfile("champion.json").get("champion", "GJR conditional EVT")
    with st.sidebar:
        st.subheader("Risk controls")
        alpha = st.select_slider("Confidence level", options=[0.90, 0.95, 0.99], value=0.99, key="alpha",
                                 format_func=lambda a: f"{a:.0%}")
        model = st.selectbox("VaR methodology", MODELS, index=MODELS.index(champion), key="model",
                             help=f"Default: {champion}, chosen on 2019–2022 by the locked rule and confirmed on 2023–2026.")
        start, end = (st.slider("Backtest date range", 2008, 2026, (2008, 2026), key="dates") if dates else (2008, 2026))
    return RiskControls(alpha, model, start, end)
