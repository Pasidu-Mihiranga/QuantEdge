import numpy as np
import pandas as pd
import streamlit as st

from components import charts
from components.data import config, parquet, require, status
from components.sidebar import pct, provisional_banner, sidebar, usd
from quantedge.data.partition import load_returns
from quantedge.stress.factor import FACTORS
from quantedge.stress.reverse import most_likely_breach, parametric_var_es, stressed_sigma

st.set_page_config(page_title="Stress Testing", layout="wide")
ctl = sidebar()
cfg = config()
st.title("Stress testing")
provisional_banner()

matrix = parquet("stress_matrix.parquet")
if not require(matrix, "The stress matrix"):
    st.stop()
w = pd.Series(status().get("weights", {}))

tab_h, tab_hyp, tab_rev, tab_corr = st.tabs(["Historical", "Hypothetical (scenario builder)", "Reverse stress",
                                             "Stressed correlation"])
with tab_h:
    st.plotly_chart(charts.heatmap(matrix, "Cumulative return: candidate × scenario"), width="stretch")
    st.caption("Historical windows are replayed buy-and-hold from the target weights (the portfolio drifts during a "
               "crisis). In 2022 stocks and bonds fell together: AGG lost 15% while SPY lost 24%.")

with tab_hyp:
    betas = parquet("stress_betas_full.parquet")
    hyp = cfg.stress["hypothetical"]
    st.markdown(f"**{hyp['name']}**: inflation re-accelerates, yields and oil jump, equities sell off, the USD "
                "strengthens, credit spreads widen and stocks and bonds fall together.")
    base = hyp["shock"]
    c = st.columns(5)
    shock = {
        "d_yield10_bp": c[0].slider("10y yield (bp)", -100, 400, int(base["d_yield10_bp"]), 10),
        "dln_oil": np.log1p(c[1].slider("Oil (%)", -50, 100, round((np.exp(base["dln_oil"]) - 1) * 100), 5) / 100),
        "d_vix": c[2].slider("VIX (points)", -10, 60, int(base["d_vix"]), 1),
        "dln_usd": np.log1p(c[3].slider("USD index (%)", -15, 20, round((np.exp(base["dln_usd"]) - 1) * 100), 1) / 100),
        "d_credit_bp": c[4].slider("Baa credit spread (bp)", -50, 500, int(base["d_credit_bp"]), 10),
    }
    if betas is not None:
        r_star = betas[FACTORS] @ pd.Series(shock)
        port = float(w.reindex(r_star.index).fillna(0) @ r_star)
        st.metric("Portfolio impact", usd(port * ctl.nav), pct(port, 1), delta_color="off")
        st.bar_chart(r_star.rename("ETF shock"))
        st.caption("ETF shocks = factor betas (weekly regressions with HAC errors, data to 2022) × the factor shocks. "
                   "The magnitudes are anchored on history (2022: +240 bp in the 10-year yield).")

with tab_rev:
    returns = load_returns("dev+val", cfg)
    L = st.slider("Loss to explain", 0.05, 0.40, float(cfg.stress["reverse"]["loss"]), 0.01)
    h = int(cfg.stress["reverse"]["horizon_days"])
    calm = most_likely_breach(returns.cov(), w, L, h)
    crisis = most_likely_breach(stressed_sigma(returns, cfg.stress["historical"]), w, L, h)
    st.dataframe(pd.DataFrame({"calm correlations": calm.x_star, "crisis correlations": crisis.x_star})
                 .style.format("{:.1%}"), width="stretch")
    st.markdown(f"To lose **{L:.0%}** in {h} trading days, the most plausible path is shown above. Under the Normal "
                f"model this is roughly a 1-in-{calm.years_between:,.0f}-year event with calm correlations, but "
                f"1-in-{crisis.years_between:,.0f} years with crisis correlations.")
    st.caption("Normal tails understate extremes, so treat these frequencies as optimistic; the comparison is the point.")

with tab_corr:
    returns = load_returns("dev+val", cfg)
    v_c, e_c = parametric_var_es(returns.cov(), w)
    v_s, e_s = parametric_var_es(stressed_sigma(returns, cfg.stress["historical"]), w)
    st.dataframe(pd.DataFrame({"99% VaR": [v_c, v_s], "99% ES": [e_c, e_s]}, index=["calm Σ", "crisis Σ"])
                 .style.format("{:.2%}"), width="stretch")
    st.caption("Diversification shrinks in crises: the same weights carry far more tail risk under crisis correlations.")
