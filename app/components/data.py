"""Cached artifact loaders. The app reads data/artifacts only: no downloads, no model fitting."""

from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from quantedge.config import load_config
from quantedge.paths import ARTIFACTS

BACKTEST_FILES = {
    "Historical": "historical", "Normal": "normal", "Student-t": "student_t",
    "Cornish-Fisher": "cornish_fisher", "EVT": "evt", "Monte Carlo": "monte_carlo",
    "GARCH-FHS": "garch_fhs", "Conditional EVT": "conditional_evt",
}
ML_FILES = {"Linear QR": "ml_linear_qr", "LightGBM": "ml_lightgbm",
            "Linear QR (ratio ES)": "ml_linear_qr_ratio_es", "LightGBM (ratio ES)": "ml_lightgbm_ratio_es",
            "LSTM": "ml_lstm"}


@st.cache_resource
def config():
    return load_config()


@st.cache_data
def parquet(name: str) -> pd.DataFrame | None:
    path = ARTIFACTS / name
    return pd.read_parquet(path) if path.exists() else None


@st.cache_data
def jsonfile(name: str) -> dict:
    path = ARTIFACTS / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


@st.cache_data
def csv(name: str) -> pd.DataFrame | None:
    path = ARTIFACTS / name
    return pd.read_csv(path) if path.exists() else None


def backtest(model: str, window: int = 500) -> pd.DataFrame | None:
    return parquet(f"backtest_{BACKTEST_FILES[model]}_{window}.parquet")


def ml_forecast(name: str) -> pd.DataFrame | None:
    return parquet(f"{ML_FILES[name]}.parquet")


def status() -> dict:
    return jsonfile("status.json")


def require(df, what: str) -> bool:
    if df is None:
        st.warning(f"{what} is not available yet. Run `python -m quantedge.pipeline` first.")
        return False
    return True
