"""The portfolio: compare equity shares (interactive), and how the strategy did since 2008 (booklet item 2)."""

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from components.palette import palette
from components.ui import (
    artifact,
    explain,
    header,
    money,
    need_numbers,
    pct,
    returns_to_decision,
    say,
    step_footer,
)
from quantedge.config import load_config
from quantedge.decision.objective import crisis_loss
from quantedge.portfolio.capm import capm_regression
from quantedge.portfolio.metrics import kpi_table

n = need_numbers()
nav, eq, req = n["nav_usd"], n["advised_equity"], n["objective"]["required_return"]
fr, wts, perf = artifact("decision_frontier.parquet"), artifact("decision_weights.parquet"), artifact("decision_performance.parquet")
P = palette()
ACCENT, GREY = P.accent, P.grey
NAMES = {"SPY": "US stocks", "EFA": "Developed-market stocks", "EEM": "Emerging-market stocks", "AGG": "US bonds",
         "GLD": "Gold", "XLE": "Energy stocks", "XLK": "Technology stocks"}

header("Compare portfolios", page="views/portfolio.py")
say("Choose how much of the fund goes into stocks and see the portfolio we would build, what it is expected to earn and "
    f"what a crisis would cost. We recommend **{eq:.0%}**.")


@st.fragment
def compare() -> None:
    """One equity share at a time; a fragment, so the slider reruns only this panel."""
    with st.container(border=True):
        x = st.select_slider("Share in stocks", options=list(fr.index), value=eq, format_func=lambda v: f"{v:.0%}", key="pf_x")
    r = fr.loc[x]
    ok_lim, ok_obj = bool(r.within_limits), bool(r.meets_objective)
    with st.container(horizontal=True):
        st.metric("Expected return a year", pct(r.forward_return, 2), f"{money((r.forward_return - req) * nav, signed=True)} vs objective",
                  delta_color="off", delta_arrow="off", border=True, help="Forward-looking: today's yields plus a 4.5% equity premium, after fees and taxes.")
        st.metric("Worst crisis", f"−{money(r.d2_loss * nav)}", f"{pct(r.d2_loss)} · budget {pct(n['limits']['crisis_budget'], 0)}", delta_color="off", delta_arrow="off",
                  border=True, help="The worse of the historical crisis replays and our stagflation scenario, with these weights.")
        st.metric("Income a year", money(r.income_yield * nav), f"{pct(r.income_yield, 2)} of the fund", delta_color="off",
                  delta_arrow="off", border=True, help="Dividends and interest after withholding tax; the fund spends 3% a year.")
    with st.container(horizontal=True):
        st.badge("Inside every risk limit" if ok_lim else "Breaks the crisis budget", color="green" if ok_lim else "red",
                 icon=":material/shield:" if ok_lim else ":material/error:")
        st.badge("Meets the objective" if ok_obj else "Misses the objective", color="green" if ok_obj else "orange",
                 icon=":material/flag:" if ok_obj else ":material/remove:")
        if abs(x - eq) < 1e-9:
            st.badge("Recommended", color="blue", icon=":material/verified:")

    w = wts.loc[x].loc[lambda s: s > 1e-4].sort_values(ascending=False)
    df = pd.DataFrame({"fund": [f"{NAMES[t]} ({t})" for t in w.index], "weight": w.values,
                       "label": [f"{v:.1%} · {money(v * nav)}" for v in w.values]})
    base = alt.Chart(df).encode(y=alt.Y("fund:N", sort=None, title=None, axis=alt.Axis(labelLimit=300, labelFontSize=13)),
                                x=alt.X("weight:Q", axis=None, scale=alt.Scale(domain=[0, 1])))
    st.altair_chart((base.mark_bar(color=ACCENT if abs(x - eq) < 1e-9 else GREY, cornerRadiusEnd=4, height=24)
                     + base.mark_text(color=P.ink, align="left", dx=6).encode(text="label:N")).properties(height=46 * len(df) + 10),
                    alt=f"Weights at {x:.0%} equity")
    explain("For each share in stocks we build the mix with the least risk, using the last three years of prices and the "
            "fund's limits (bonds at most 65%; energy, technology and emerging markets at most 10% each). Below 35% the expected "
            "return falls short of what the fund needs; above 35% a crisis like 2008 would cost more than the 25% limit.")


compare()

st.subheader("How the recommended strategy did since 2008")
show = st.segmented_control("Show", ["Growth of the fund", "Falls from the peak"], default="Growth of the fund", required=True,
                            label_visibility="collapsed", key="pf_hist")
LABEL = {"Frontier 35% equity": "Recommended (35% equity)", "60/40 benchmark": "60/40 stocks/bonds (outside our limits)"}
wealth = (1 + perf.fillna(0)).cumprod()
series = wealth * nav if show == "Growth of the fund" else wealth / wealth.cummax() - 1
h = series.rename(columns=LABEL).reset_index().melt(series.index.name or "index", var_name="portfolio", value_name="value")
h = h.rename(columns={h.columns[0]: "date"})
fmt = "$~s" if show == "Growth of the fund" else ".0%"
st.altair_chart(alt.Chart(h).mark_line(strokeWidth=1.6).encode(
    x=alt.X("date:T", title=None), y=alt.Y("value:Q", title="Value of USD 10M (Jan 2008)" if show == "Growth of the fund" else "Fall from the previous peak",
                                           axis=alt.Axis(format=fmt)),
    color=alt.Color("portfolio:N", scale=alt.Scale(domain=list(LABEL.values()), range=[ACCENT, GREY]),
                    legend=alt.Legend(title=None, orient="bottom", labelLimit=400)),
    tooltip=[alt.Tooltip("date:T"), "portfolio:N", alt.Tooltip("value:Q", format="$,.0f" if fmt == "$~s" else ".1%")]).properties(height=300),
    alt="History of the recommended strategy and the 60/40 benchmark")
cfg = load_config()
past = returns_to_decision()
bench_crisis = crisis_loss(pd.Series({"SPY": 0.6, "AGG": 0.4}), past, cfg.stress["historical"]).max()
explain("Every quarter the mix was rebuilt using only the prices known at the time, and trading costs were paid, so "
        "this is what the strategy could really have done. "
        "The 60/40 mix earned more because it held 60% in US stocks during an exceptional decade for them, but it breaks the "
        f"committee's limits (a {pct(bench_crisis)} crisis loss against the {pct(n['limits']['crisis_budget'], 0)} budget) "
        "and is shown only as a reference. History is not a forecast.")

st.subheader("The scorecard", divider=False)
say("The standard performance measures for both strategies. Pick a period: the whole history, or only 2023–2026, the "
    "years no choice was made on.")
period = st.segmented_control("Period", ["Since 2008", "2023 onwards (unseen test years)"], default="Since 2008",
                              required=True, label_visibility="collapsed", key="pf_kpi_period")


@st.cache_data
def scorecard(start: str) -> pd.DataFrame:
    """Booklet Layer 1 KPIs (Sharpe, Sortino, Treynor, Jensen's alpha, IR, drawdown, Calmar); CAPM against SPY with the
    T-bill rate lagged one day, as in Step 06."""
    r = perf.dropna().loc[start:]
    rf = artifact("returns_rf.parquet")["rf"]
    spy = returns_to_decision()["SPY"].reindex(r.index)
    capm = {c: capm_regression(r[c] - rf.reindex(r.index), spy - rf.reindex(r.index)) for c in r.columns}
    return kpi_table({c: r[c] for c in r.columns}, rf, r["60/40 benchmark"],
                     betas={c: v.beta for c, v in capm.items()}, alphas={c: (v.alpha_ann, v.alpha_t) for c, v in capm.items()})


k = scorecard("2008-01-01" if period == "Since 2008" else "2023-01-01")
ROWS = [  # (KPI, column, format, what it means)
    ("Return a year", "cagr", pct, "Compounded growth a year, after trading costs."),
    ("Volatility", "volatility", pct, "How much the value swings in a typical year."),
    ("Sharpe ratio", "sharpe", "{:.2f}".format, "Return above T-bills per unit of total risk. Higher is better."),
    ("Sortino ratio", "sortino", "{:.2f}".format, "Like Sharpe, but counts only the falls."),
    ("Beta to US stocks", "beta", "{:.2f}".format, "How much the strategy moves when US stocks move 1%."),
    ("Treynor ratio", "treynor", pct, "Return above T-bills per unit of stock-market risk (beta)."),
    ("Jensen's alpha", "jensen_alpha", lambda v: pct(v, 2, signed=True), "Return beyond what its stock exposure explains."),
    ("Information ratio vs 60/40", "information_ratio", "{:.2f}".format, "Extra return over 60/40 per unit of deviation."),
    ("Worst fall", "max_drawdown", lambda v: pct(-abs(v)), "The deepest drop from a previous high."),
    ("Calmar ratio", "calmar", "{:.2f}".format, "Return a year per unit of the worst fall. Higher is better."),
]
fmt_ = lambda f, v: "—" if not np.isfinite(v) else f(v)  # noqa: E731
table = pd.DataFrame({"Measure": [r[0] for r in ROWS],
                      **{LABEL[c]: [fmt_(f, float(k.loc[c, col])) for _, col, f, _ in ROWS] for c in k.index},
                      "What it means": [r[3] for r in ROWS]}).set_index("Measure")
table.loc["Information ratio vs 60/40", LABEL["60/40 benchmark"]] = "—"
st.table(table)
t_alpha = float(k.loc["Frontier 35% equity", "jensen_alpha_t"])
explain(f"Sharpe, Sortino, Treynor and Calmar use the 3-month T-bill rate known the day before. Beta and Jensen's alpha "
        f"come from a regression on US stocks (SPY) with Newey-West errors. The recommended strategy's alpha has a t-statistic "
        f"of {t_alpha:.1f}: " + ("no evidence of skill beyond its stock exposure, as expected for a diversified mix. "
                                  if abs(t_alpha) < 2 else "statistically different from zero. ")
        + "The 60/40 is the benchmark, so it has no information ratio.")

step_footer("views/portfolio.py")
