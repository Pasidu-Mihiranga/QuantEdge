import pandas as pd
import streamlit as st

from components import charts
from components.data import parquet, require, status
from components.sidebar import provisional_banner, sidebar
from quantedge.paths import ARTIFACTS

st.set_page_config(page_title="Portfolio", layout="wide")
ctl = sidebar()
st.title("Portfolio construction and selection")
provisional_banner()

card = parquet("portfolio_scorecard_val.parquet")
perf = parquet("wf_performance_val.parquet")
if not (require(card, "The scorecard") and require(perf, "Walk-forward performance")):
    st.stop()

perf = perf.loc[ctl.start:ctl.end]
st.subheader("Walk-forward results (out-of-sample, quarterly rebalance, 5 bps per side)")
c1, c2 = st.columns(2)
c1.plotly_chart(charts.cumulative(perf, "Cumulative return"), width="stretch")
c2.plotly_chart(charts.underwater(perf, "Drawdown (underwater)"), width="stretch")

st.subheader("Pre-declared scorecard (selection uses data to 2022 only)")
show = ["rank", "ips_pass", "weights_within_ips", "es99_oos", "max_drawdown", "worst_crisis_drawdown", "worst_crisis",
        "calmar", "cagr", "vs_required", "volatility", "sharpe", "turnover_ann"]
st.dataframe(card[show].style.format({c: "{:.2%}" for c in ("es99_oos", "max_drawdown", "worst_crisis_drawdown", "cagr",
                                                            "vs_required", "volatility")} | {"calmar": "{:.2f}",
                                                                                            "sharpe": "{:.2f}",
                                                                                            "turnover_ann": "{:.2f}"}),
             width="stretch")
st.caption("Order: IPS pass/fail, then capital preservation (OOS 99% ES and max drawdown), then Calmar.")

st.subheader("Target weights at the latest rebalance")
weights = {}
for f in sorted(ARTIFACTS.glob("wf_weights_*.parquet")):
    w = pd.read_parquet(f)
    weights[f.stem.replace("wf_weights_", "").replace("_", " ")] = w.iloc[-1]
st.dataframe(pd.DataFrame(weights).T.style.format("{:.1%}"), width="stretch")
st.caption(f"Weights as of {status().get('weights_as_of', '?')}.")
