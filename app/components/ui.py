"""Shared look and plain-language formatting for the committee app.

Rules (doc: the app audit): summary first; dollars and "days per year" before percentages; one
colour per meaning (the recommendation in blue, everything else grey, status colour always with a
word); every headline number comes from data/artifacts/decision_numbers.json.
The look itself is the theme in .streamlit/config.toml (light and dark) plus components/palette.py; no custom CSS.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache

import pandas as pd
import streamlit as st

from quantedge.config import load_config
from quantedge.data.partition import load_returns
from quantedge.paths import ARTIFACTS

# The committee story, in reading order: each page ends with a link to the next one.
STORY = [("views/recommendation.py", "Our recommendation"), ("views/crises.py", "What can go wrong"),
         ("views/risk.py", "Risk and confidence"), ("views/portfolio.py", "Compare portfolios"),
         ("views/assumptions.py", "Assumptions & Limitations")]


@st.cache_data
def numbers() -> dict:
    path = ARTIFACTS / "decision_numbers.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


@st.cache_data
def artifact(name: str) -> pd.DataFrame | None:
    path = ARTIFACTS / name
    return pd.read_parquet(path) if path.exists() else None


@lru_cache
def jsonfile(name: str) -> dict:
    path = ARTIFACTS / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


@st.cache_data
def returns_to_decision() -> pd.DataFrame:
    """Daily returns up to the day before the decision date. The app only runs on finished results (the one-shot test
    is over, its record is in the artifacts), so it does not look for the git tag, which a hosted clone may not carry."""
    r = load_returns("all", load_config(), frozen=True)
    return r.loc[r.index < pd.Timestamp(numbers()["decision_date"])]


def need_numbers() -> dict:
    n = numbers()
    if not n:
        st.error("The decision numbers are not available yet. Run `python -m quantedge.pipeline` after the freeze tag.")
        st.stop()
    return n


# ---------- plain-language formatting ----------
def money(x: float, signed: bool = False) -> str:
    """$2.39M, $208k, $10,700; a minus sign before the dollar sign."""
    sign = "−" if x < 0 else ("+" if signed and x > 0 else "")
    a = abs(x)
    if a >= 999_500:                               # so that $999,999 reads $1.00M, not $1,000k
        body = f"${a / 1e6:.2f}M"
    elif a >= 1e5:
        body = f"${a / 1e3:,.0f}k"
    else:
        body = f"${round(a, -2):,.0f}"
    return sign + body


def pct(x: float, d: int = 1, signed: bool = False) -> str:
    s = f"{x * 100:+.{d}f}%" if signed else f"{x * 100:.{d}f}%"
    return s.replace("-", "−")


def per_year(alpha: float) -> str:
    """Natural frequency of a 1-day loss beyond the alpha quantile, on 252 trading days."""
    days = (1 - alpha) * 252
    if days < 4:
        return f"1 day in {round(1 / (1 - alpha))} (about {int(days)}–{int(days) + 1} trading days a year)"
    return f"1 day in {round(1 / (1 - alpha))} (about {round(days)} trading days a year)"


def esc(text: str) -> str:
    """Escape dollar signs so Streamlit Markdown never reads them as LaTeX."""
    return text.replace("$", "\\$")


# ---------- page chrome ----------
def header(title: str, lead: str | None = None, *, page: str | None = None) -> None:
    """Where you are (step k of the committee story), the page's question, and one line on what it answers."""
    paths = [p for p, _ in STORY]
    if page in paths:
        st.caption(f":material/flag: Step {paths.index(page) + 1} of {len(STORY)} · for the investment committee")
    st.title(title)
    if lead:
        say(lead)


def step_footer(page: str) -> None:
    """Previous and next page of the committee story, so the pages read as one walk-through."""
    paths = [p for p, _ in STORY]
    i = paths.index(page)
    st.space("medium")
    with st.container(border=True, horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"):
        if i > 0:
            st.page_link(STORY[i - 1][0], label=f"Back: {STORY[i - 1][1]}", icon=":material/arrow_back:")
        else:
            st.caption("Start of the committee story")
        if i < len(STORY) - 1:
            st.page_link(STORY[i + 1][0], label=f"Next: {STORY[i + 1][1]}", icon=":material/arrow_forward:",
                         icon_position="right")
        else:
            st.page_link("side/custom.py", label="Try your own portfolio", icon=":material/tune:", icon_position="right")
    n = numbers()
    st.caption(f"Team Gmora · QuantEdge 1.0 · decision date {n.get('decision_date', '?')} · market data to "
               f"{n.get('data_end', '?')} · history is not a forecast")


# ---------- low-cognitive-load helpers (one idea per line, explanations on demand) ----------
TEXT_WIDTH = "stretch"    # full width; paragraphs are kept to one or two sentences


def points(text: str) -> str:
    """Three or more sentences read better as bullets; shorter text and ready-made lists stay as they are."""
    if "\n" in text:
        return text
    parts = re.split(r"(?<=[.?!])\s+(?=[A-Z*])", text.strip())
    return "\n".join(f"- {p}" for p in parts) if len(parts) >= 3 else text


def say(text: str) -> None:
    """Short text at a readable width (dollar signs escaped), as bullets when it runs to three sentences or more."""
    st.markdown(esc(points(text)), width=TEXT_WIDTH)


def explain(text: str, label: str = "How to read this") -> None:
    """The 'why' behind a chart or number, one click away."""
    with st.popover(label, icon=":material/help:", type="tertiary"):
        st.markdown(esc(points(text)))
