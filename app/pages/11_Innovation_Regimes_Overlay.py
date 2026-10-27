import json

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from components import charts
from components.charts import LAYOUT
from components.data import parquet, require
from components.sidebar import provisional_banner, sidebar
from quantedge.paths import ARTIFACTS

st.set_page_config(page_title="Regimes, Overlay, Copula, Macro", layout="wide")
ctl = sidebar()
st.title("Innovation: regimes, risk overlay, joint crashes, macro and FX")
provisional_banner()

summary_file = ARTIFACTS / "innovation_summary.json"
if not require(parquet("overlay_compare.parquet"), "The Step 14 results"):
    st.stop()
inn = json.loads(summary_file.read_text(encoding="utf-8"))
rg, cp, mc = inn["regime"], inn["copula"], inn["macro"]

tab_r, tab_o, tab_c, tab_m = st.tabs(["Regimes", "Volatility-target overlay", "t-copula", "Macro and FX"])

with tab_r:
    p = parquet("regime_p_high.parquet")
    fig = go.Figure(go.Scatter(x=p.index, y=p["p_high"], mode="lines", line=dict(color="#c0392b", width=1)))
    fig.add_hline(y=0.7, line_dash="dot", annotation_text="governance trigger 0.7")
    st.plotly_chart(fig.update_layout(title="Filtered probability of the high-volatility regime", **LAYOUT), width="stretch")
    c1, c2, c3 = st.columns(3)
    c1.metric("99% ES, high-vol vs calm", f"{rg['es99_high_over_calm']:.1f}×")
    c2.metric("Expected regime length", f"{rg['duration_calm_days']:.0f} / {rg['duration_high_days']:.0f} days", "calm / high-vol",
              delta_color="off")
    c3.metric("P(high-vol), end of 2022", f"{rg['p_high_latest']:.0%}")
    st.dataframe(parquet("regime_vix.parquet").style.format("{:.0%}"), width="stretch")
    st.caption(f"Parameters estimated on data to {rg['fit_window_end']}, then the filter runs forward with them "
               "fixed: the probability on any day uses only earlier data. Used as a governance trigger, not a trading signal.")

with tab_o:
    perf = parquet("overlay_performance.parquet").loc[ctl.start:ctl.end]
    c1, c2 = st.columns(2)
    c1.plotly_chart(charts.cumulative(perf, "Growth of $1 after costs"), width="stretch")
    c2.plotly_chart(charts.underwater(perf, "Drawdown"), width="stretch")
    ov = parquet("overlay_compare.parquet")
    st.dataframe(ov.style.format({c: "{:.2%}" for c in ov.columns if c not in ("calmar", "turnover_ann")}
                                 | {"calmar": "{:.2f}", "turnover_ann": "{:.2f}"}), width="stretch")
    st.caption("Weekly rule: when the GARCH volatility forecast exceeds the 8% target, scale the risky assets down "
               "and hold the difference in AGG or T-bills (turnover capped at 20% a month, 5 bps per side). Moving "
               "into AGG barely helps and did not help in 2022, when bonds fell with equities.")

with tab_c:
    c1, c2, c3 = st.columns(3)
    c1.metric("99% ES, t-copula vs Gaussian", f"{cp['es99_t']:.2%}", f"{cp['es_uplift_t_vs_gauss']:+.1%}", delta_color="inverse")
    c2.metric("Joint SPY/EFA/EEM crash (t / Gaussian)", f"{cp['joint_crash_t']:.2%}", f"Gaussian {cp['joint_crash_gauss']:.2%}",
              delta_color="off")
    c3.metric("Tail dependence SPY–EFA (λ_L)", f"{cp['lambda_L_spy_efa']:.2f}", f"ν = {cp['nu']:.1f}", delta_color="off")
    st.caption(f"Historical joint-crash frequency: {cp['joint_crash_history']:.2%}. A Gaussian copula has no tail "
               "dependence; the t-copula lets large losses arrive together. Marginals: empirical body with GPD tails.")

with tab_m:
    sb = parquet("macro_stock_bond.parquet")
    fig = go.Figure()
    fig.add_scatter(x=sb.index, y=sb["stock_bond_corr"], name="SPY–AGG correlation (1 year)")
    fig.add_scatter(x=sb.index, y=sb["cpi_yoy"], name="CPI inflation (year on year)", yaxis="y2")
    fig.update_layout(title="Stocks and bonds move together when inflation is high", yaxis2=dict(overlaying="y", side="right",
                      tickformat=".0%"), **LAYOUT)
    st.plotly_chart(fig, width="stretch")
    c1, c2 = st.columns(2)
    c1.metric("+100 bp in the 10-year yield", f"{mc['rates_plus_100bp']:.1%}")
    c2.metric("Inflation-surprise beta (t-stat)", f"{mc['inflation']['beta']:.2f}", f"t = {mc['inflation']['t']:.2f}",
              delta_color="off")
    lkr = mc.get("lkr")
    if lkr:
        st.subheader("USD/LKR: the endowment spends in rupees")
        st.markdown(f"From {lkr['start']} to {lkr['end']} the rupee moved from {lkr['lkr_per_usd_start']:.0f} to "
                    f"{lkr['lkr_per_usd_end']:.0f} per dollar ({lkr['annual_depreciation']:.1%} a year; "
                    f"{lkr['change_2022']:+.0%} in 2022). The portfolio grew {lkr['growth_usd']:.0%} in USD but "
                    f"{lkr['growth_lkr']:.0%} in LKR terms: USD assets are a natural hedge for rupee spending. "
                    "This is outside the mandate's USD risk measures.")
        fx = pd.read_parquet(ARTIFACTS.parent / "raw" / "fx_LKR_X.parquet").iloc[:, 0].loc[:"2022-12-31"]
        st.plotly_chart(px.line(fx, title="LKR per USD").update_layout(**LAYOUT, showlegend=False), width="stretch")
