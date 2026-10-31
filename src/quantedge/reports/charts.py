"""Static figures for the report: inline SVG, so the HTML needs no network and prints the same everywhere."""

from __future__ import annotations

import io
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

ACCENT, GREY, CRIT, INK, MUTED = "#1F5FAE", "#A3ABB5", "#B42318", "#1D2733", "#5B6573"
RECOMMENDED, BENCHMARK = "Recommended (35% equity)", "60/40 stocks/bonds"

plt.rcParams.update({
    "svg.fonttype": "none", "font.family": ["DejaVu Sans"], "font.size": 8.5, "text.color": INK,
    "axes.edgecolor": "#C7CDD5", "axes.labelcolor": MUTED, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": "#E8EBEF", "grid.linewidth": 0.6, "axes.axisbelow": True,
    "xtick.color": MUTED, "ytick.color": MUTED, "xtick.major.size": 0, "ytick.major.size": 0,
})


def _svg(fig, name: str) -> str:
    plt.rcParams["svg.hashsalt"] = name                 # stable, unique clip-path ids per figure
    buf = io.StringIO()
    fig.savefig(buf, format="svg", bbox_inches="tight", metadata={"Date": None})
    plt.close(fig)
    text = buf.getvalue()
    # Labels are live text, so they take the document's typeface rather than the one matplotlib measured with.
    text = re.sub(r"font-family: *[^;\"]+", "font-family: 'Source Sans 3', Helvetica, Arial, sans-serif", text)
    text = re.sub(r"font: ((?:bold )?[\d.]+px) [^;\"]+", r"font: \1 'Source Sans 3', Helvetica, Arial, sans-serif", text)
    return text[text.index("<svg"):]


def growth_and_drawdown(perf: pd.DataFrame, nav: float) -> str:
    """Growth of the fund and falls from the peak, the recommended strategy against the 60/40 reference."""
    wealth = (1 + perf.fillna(0)).cumprod()
    wealth.columns = [RECOMMENDED, BENCHMARK]
    fig, (top, low) = plt.subplots(2, 1, figsize=(7.1, 3.5), sharex=True, height_ratios=[1.7, 1])
    for name, colour, width in ((BENCHMARK, GREY, 1.2), (RECOMMENDED, ACCENT, 1.5)):
        v = wealth[name] * nav / 1e6
        top.plot(v.index, v, color=colour, lw=width, label=name)
        fall = (wealth[name] / wealth[name].cummax() - 1) * 100
        low.plot(fall.index, fall, color=colour, lw=width)
    top.set_ylabel("Value of USD 10M (USD M)")
    low.set_ylabel("Fall from peak (%)")
    top.legend(frameon=False, loc="upper left", ncols=2)
    return _svg(fig, "growth")


def frontier(fr: pd.DataFrame, budget: float, required: float, chosen: float) -> str:
    """Return against crisis loss across the equity shares: the rule's two constraints leave one point."""
    x, y = fr["d2_loss"] * 100, fr["forward_return"] * 100
    fig, ax = plt.subplots(figsize=(7.1, 2.7))
    ax.axvline(budget * 100, color=CRIT, lw=1.1, ls="--")
    ax.axhline(required * 100, color=CRIT, lw=1.1, ls="--")
    ax.plot(x, y, color=GREY, lw=1.4, marker="o", ms=4.5, zorder=2)
    ax.scatter([x.loc[chosen]], [y.loc[chosen]], color=ACCENT, s=62, zorder=3)
    for eq in fr.index:
        ax.annotate(f"{eq:.0%}", (x.loc[eq], y.loc[eq]), textcoords="offset points", xytext=(0, 7), ha="center",
                    color=ACCENT if eq == chosen else MUTED, fontweight="bold" if eq == chosen else "normal")
    ax.text(budget * 100 + 0.1, y.min() + 0.02, f"crisis budget {budget:.0%}", color=CRIT)
    ax.text(x.max(), required * 100 - 0.015, f"required {required:.2%}", color=CRIT, ha="right", va="top")
    ax.set_xlabel("Worst crisis loss, % of the fund")
    ax.set_ylabel("Expected return, % a year")
    ax.margins(y=0.16)
    return _svg(fig, "frontier")


def models(snap: pd.DataFrame, nav: float, alpha: float = 0.99) -> str:
    """VaR to ES for each model on one row: the distance between the dots is the loss VaR alone hides."""
    t = snap[snap["alpha"] == alpha].sort_values("es")
    fig, ax = plt.subplots(figsize=(7.1, 2.6))
    pos = range(len(t))
    ax.hlines(pos, t["var"] * nav / 1e3, t["es"] * nav / 1e3, color=GREY, lw=1.3)
    ax.scatter(t["var"] * nav / 1e3, pos, color=GREY, s=20, label="VaR", zorder=3)
    ax.scatter(t["es"] * nav / 1e3, pos, color=ACCENT, s=24, label="Expected Shortfall", zorder=3)
    ax.set_yticks(list(pos), t["model"])
    ax.set_xlabel(f"One-day loss at {alpha:.0%} confidence, USD thousand")
    ax.grid(axis="y", visible=False)
    ax.legend(frameon=False, loc="lower right")
    return _svg(fig, "models")


def backtest(bt: pd.DataFrame, nav: float, alpha: float = 0.99) -> str:
    """Daily loss against the VaR forecast on the one-shot test, with every breach marked."""
    fig, ax = plt.subplots(figsize=(7.1, 2.3))
    loss, var = bt["loss"] * nav / 1e3, bt[f"var_{alpha}"] * nav / 1e3
    hits = bt[f"hit_{alpha}"] == 1
    ax.plot(loss.index, loss, color=GREY, lw=0.5, label="Daily loss")
    ax.plot(var.index, var, color=ACCENT, lw=1.3, label="99% VaR forecast")
    ax.scatter(loss.index[hits], loss[hits], color=CRIT, s=16, zorder=3, label=f"Breach ({int(hits.sum())})")
    ax.set_ylabel("USD thousand")
    ax.legend(frameon=False, ncols=3, loc="lower left", bbox_to_anchor=(0, 1), borderaxespad=0)
    return _svg(fig, "backtest")


def crises(losses: pd.Series, budget: float, nav: float) -> str:
    """Every crisis against the one budget; the team's own scenario stands out by colour and by label."""
    s = losses.sort_values()
    fig, ax = plt.subplots(figsize=(7.1, 2.2))
    colours = [ACCENT if "scenario" in k else GREY for k in s.index]
    names = [k.replace(" (pre-registered)", "").replace(" (scenario)", " (our scenario)") for k in s.index]
    ax.barh(names, s * 100, color=colours, height=0.62)
    for i, v in enumerate(s):                       # a label column right of the budget line, so nothing crosses it
        ax.text(budget * 100 + 1, i, f"{v:.1%}  USD {v * nav / 1e6:.2f}M", va="center")
    ax.axvline(budget * 100, color=CRIT, lw=1.2, ls="--")
    ax.text(budget * 100, len(s) - 0.4, f"budget {budget:.0%}", color=CRIT, ha="center")
    ax.set_xlim(0, 34)
    ax.set_xticks(range(0, 30, 5))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Worst loss during the episode")
    return _svg(fig, "crises")
