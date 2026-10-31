"""Plotly figures with one colour per concept across the app (Step 15 §3.5)."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

COLORS = {"var": "#2f6db5", "es": "#e07b22", "evt": "#c0392b", "loss": "#8c8c8c",
          "portfolio": "#178a85", "benchmark": "#5b6773"}
ZONE = {"green": "#2e9d57", "yellow": "#e3b505", "red": "#c0392b"}
LAYOUT = dict(margin=dict(l=10, r=10, t=40, b=10), legend=dict(orientation="h", y=-0.15),
              font=dict(size=13))  # no template: Streamlit's light or dark theme applies


def donut(weights: pd.Series, title: str) -> go.Figure:
    w = weights[weights > 1e-4]
    fig = go.Figure(go.Pie(labels=w.index, values=w.values, hole=0.55, sort=False,
                           texttemplate="%{label}<br>%{percent:.0%}"))
    return fig.update_layout(title=title, showlegend=False, **LAYOUT)


def var_es_evt_bars(table: pd.DataFrame, title: str) -> go.Figure:
    fig = go.Figure()
    fig.add_bar(x=table.index, y=table["var"], name="VaR", marker_color=COLORS["var"])
    fig.add_bar(x=table.index, y=table["es"], name="ES", marker_color=COLORS["es"])
    fig.update_yaxes(tickformat=".2%", title="1-day loss")
    return fig.update_layout(barmode="group", title=title, **LAYOUT)


def exceptions_chart(df: pd.DataFrame, alpha: float, title: str) -> go.Figure:
    v = df[f"var_{alpha}"]
    hit = df[f"hit_{alpha}"].astype(bool)
    fig = go.Figure()
    fig.add_scatter(x=df.index, y=df["loss"], mode="lines", name="Realised loss",
                    line=dict(color=COLORS["loss"], width=1))
    fig.add_scatter(x=df.index, y=v, mode="lines", name=f"VaR {alpha:.0%}", line=dict(color=COLORS["var"], width=1.5))
    fig.add_scatter(x=df.index[hit], y=df["loss"][hit], mode="markers", name="Exception",
                    marker=dict(color=COLORS["evt"], size=6))
    fig.update_yaxes(tickformat=".1%", title="Daily loss (positive = loss)")
    return fig.update_layout(title=title, **LAYOUT)


def zone_band(rolling: pd.DataFrame, title: str) -> go.Figure:
    fig = go.Figure()
    for zone, color in ZONE.items():
        mask = rolling["zone"] == zone
        fig.add_bar(x=rolling.index[mask], y=[1] * int(mask.sum()), name=zone.title(),
                    marker_color=color, marker_line_width=0)
    fig.update_yaxes(visible=False)
    return fig.update_layout(title=title, barmode="stack", bargap=0, height=180, **LAYOUT)


def cumulative(perf: pd.DataFrame, title: str) -> go.Figure:
    wealth = (1 + perf.fillna(0)).cumprod()
    fig = px.line(wealth, title=title)
    fig.update_yaxes(title="Growth of $1")
    return fig.update_layout(**LAYOUT)


def underwater(perf: pd.DataFrame, title: str) -> go.Figure:
    wealth = (1 + perf.fillna(0)).cumprod()
    dd = wealth / wealth.cummax() - 1
    fig = px.line(dd, title=title)        # one line per series: stacked areas would add the drawdowns up
    fig.update_yaxes(tickformat=".0%", title="Drawdown")
    return fig.update_layout(**LAYOUT)


def heatmap(matrix: pd.DataFrame, title: str) -> go.Figure:
    fig = px.imshow(matrix, text_auto=".1%", color_continuous_scale="RdYlGn", aspect="auto",
                    zmin=-0.35, zmax=0.0, title=title)
    return fig.update_layout(coloraxis_showscale=False, **LAYOUT)


def capital_vs_risk(contrib: pd.DataFrame, title: str) -> go.Figure:
    fig = go.Figure()
    fig.add_bar(x=contrib.index, y=contrib["weight"], name="Share of capital", marker_color=COLORS["portfolio"])
    fig.add_bar(x=contrib.index, y=contrib["pct_contribution"], name="Share of 99% ES", marker_color=COLORS["es"])
    fig.update_yaxes(tickformat=".0%")
    return fig.update_layout(barmode="group", title=title, **LAYOUT)
