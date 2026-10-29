"""Shared look and plain-language formatting for the committee app.

Rules (doc: the app audit): summary first; dollars and "days per year" before percentages; one
colour per meaning (the recommendation in blue, everything else grey, status colour always with a
word); every headline number comes from data/artifacts/decision_numbers.json.
"""

from __future__ import annotations

import json
from functools import lru_cache

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from quantedge.paths import ARTIFACTS

ACCENT, GREY, INK, MUTED = "#1f5fae", "#a3abb5", "#1d2733", "#5b6573"
GOOD, WARN, CRIT = "#0d7a2f", "#a15c00", "#b42318"
TAIL = {"VaR": "#9ec1ea", "ES": "#4f86c6", "EVT": "#1f3f73"}           # one hue, light to dark: worse is darker
STATUS = {"ACCEPT": GOOD, "ADJUST": WARN, "REJECT": CRIT}

CSS = """
<style>
/* Full-width layout (requested): slimmer side margins and top gap than Streamlit's defaults */
[data-testid="stMainBlockContainer"], .block-container {padding: 2.2rem 2.2rem 3rem 2.2rem; max-width: 100%;}
/* More breathing room between sections and inside bordered panels */
[data-testid="stMain"] [data-testid="stVerticalBlock"] {gap: 1.25rem;}
[data-testid="stSlider"] {padding: 0 0.6rem;}
.qe-verdict {border-radius: 10px; padding: 18px 22px; color: #fff; margin: 4px 0 6px 0;}
.qe-verdict .v {font-size: 1.55rem; font-weight: 700; letter-spacing: .01em;}
.qe-verdict .s {font-size: 1.05rem; margin-top: 6px; max-width: 75ch; line-height: 1.45;}
.qe-card {border: 1px solid #dde1e7; border-radius: 10px; padding: 14px 16px; background: #fff; height: 100%;}
.qe-card .q {font-size: .8rem; text-transform: uppercase; letter-spacing: .06em; color: #5b6573;}
.qe-card .a {font-size: 1.45rem; font-weight: 650; color: #1d2733; margin: 4px 0 2px 0; font-variant-numeric: tabular-nums;}
.qe-card .d {font-size: .92rem; color: #3d4652; line-height: 1.4;}
.qe-pill {display: inline-block; padding: 1px 9px; border-radius: 999px; font-size: .8rem; font-weight: 600;}
.qe-note {border-left: 4px solid #1f5fae; background: #eef3fa; padding: 10px 14px; border-radius: 4px; color: #1d2733;}
.qe-warn {border-left: 4px solid #a15c00; background: #fbf3e6; padding: 10px 14px; border-radius: 4px; color: #1d2733;}
</style>
"""


def style() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


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


def html_safe(text: str) -> str:
    """Dollar signs as an HTML entity inside HTML blocks (Markdown would read a pair of them as LaTeX)."""
    return text.replace("$", "&#36;")


def esc(text: str) -> str:
    """Escape dollar signs so Streamlit Markdown never reads them as LaTeX."""
    return text.replace("$", "\\$")


# ---------- building blocks ----------
def verdict_banner(verdict: str, sentence: str) -> None:
    key = verdict.split()[0]
    label = {"ACCEPT": "ACCEPT the mandate as proposed", "ADJUST": "ADJUST THE RISK LIMIT",
             "REJECT": "REJECT the mandate as proposed"}[key]
    st.markdown(f"<div class='qe-verdict' style='background:{STATUS[key]}'><div class='v'>{label}</div>"
                f"<div class='s'>{html_safe(sentence)}</div></div>", unsafe_allow_html=True)


def card(question: str, answer: str, detail: str) -> None:
    st.markdown(f"<div class='qe-card'><div class='q'>{question}</div><div class='a'>{html_safe(answer)}</div>"
                f"<div class='d'>{html_safe(detail)}</div></div>", unsafe_allow_html=True)


def pill(text: str, status: str) -> str:
    colour = {"good": GOOD, "warn": WARN, "crit": CRIT}[status]
    return f"<span class='qe-pill' style='color:{colour};background:{colour}1a'>{text}</span>"


def note(text: str, kind: str = "note") -> None:
    st.markdown(f"<div class='qe-{kind}'>{html_safe(text)}</div>", unsafe_allow_html=True)


def layout(fig: go.Figure, height: int = 360, title: str | None = None) -> go.Figure:
    fig.update_layout(template="plotly_white", height=height, margin=dict(l=8, r=8, t=48 if title else 16, b=8),
                      font=dict(size=13, color=INK, family="Google Sans, Helvetica, Arial, sans-serif"), title=dict(text=title, x=0, font=dict(size=15)) if title else None,
                      legend=dict(orientation="h", y=-0.18, x=0), hoverlabel=dict(font_size=13))
    return fig


def show(fig: go.Figure) -> None:
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def full(df) -> None:
    """A data table tall enough to show every row (no inner scrolling)."""
    rows = len(df.data) if hasattr(df, "data") else len(df)
    st.dataframe(df, width="stretch", height=35 * (rows + 1) + 3)


# ---------- low-cognitive-load helpers (one idea per line, explanations on demand) ----------
TEXT_WIDTH = "stretch"    # full width; paragraphs are kept to one or two sentences


def say(text: str) -> None:
    """A short paragraph at a readable width (dollar signs escaped)."""
    st.markdown(esc(text), width=TEXT_WIDTH)


def explain(text: str, label: str = "How to read this") -> None:
    """The 'why' behind a chart or number, one click away."""
    with st.popover(label, icon=":material/help:", type="tertiary"):
        st.markdown(esc(text))
