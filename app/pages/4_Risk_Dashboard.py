import streamlit as st

from components import charts
from components.data import jsonfile, parquet, require
from components.sidebar import pct, provisional_banner, sidebar, usd

st.set_page_config(page_title="Risk Dashboard", layout="wide")
ctl = sidebar()
st.title("Risk dashboard: VaR, ES and EVT")
provisional_banner()

snap = parquet("risk_snapshot.parquet")
if not require(snap, "The risk snapshot"):
    st.stop()
extras = jsonfile("risk_extras.json")
a = ctl.alpha
at = snap[snap.alpha == a].set_index("model")

st.caption(f"Fitted on {extras.get('window_start')} to {extras.get('window_end')} at the latest target weights · 1-day · {a:.0%}")
c1, c2, c3 = st.columns(3)
c1.metric(f"VaR {a:.0%} ({ctl.model})", usd(at.loc[ctl.model, "var"] * ctl.nav), pct(at.loc[ctl.model, "var"]), delta_color="off")
c2.metric(f"ES {a:.0%} ({ctl.model})", usd(at.loc[ctl.model, "es"] * ctl.nav), pct(at.loc[ctl.model, "es"]), delta_color="off")
c3.metric(f"EVT ES {a:.0%}", usd(at.loc["EVT", "es"] * ctl.nav), pct(at.loc["EVT", "es"]), delta_color="off")
st.caption("VaR is a threshold exceeded on about (1 − α) of days, not a maximum loss. ES is the average loss on those days.")

st.plotly_chart(charts.var_es_evt_bars(at, f"All models at {a:.0%}"), width="stretch")
st.dataframe(at[["var", "es"]].assign(var_usd=at["var"] * ctl.nav, es_usd=at["es"] * ctl.nav)
             .style.format({"var": "{:.3%}", "es": "{:.3%}", "var_usd": "${:,.0f}", "es_usd": "${:,.0f}"}),
             width="stretch")

st.subheader("Why the models disagree")
dis = parquet("risk_disagreement.parquet")
if dis is not None:
    st.dataframe(dis.style.format("{:.3%}").format({"HS / Normal": "{:.2f}"}), width="stretch")
st.markdown(f"""
- Excess kurtosis of portfolio losses: **{extras.get('excess_kurtosis', float('nan')):.2f}** (Jarque-Bera p = {extras.get('jarque_bera_p', float('nan')):.2g}): fat tails.
- Ljung-Box on squared losses p = {extras.get('ljungbox_sq_p', float('nan')):.2g}, ARCH-LM p = {extras.get('arch_lm_p', float('nan')):.2g}: volatility clustering.
- GARCH persistence α + β = {extras.get('garch_persistence', float('nan')):.3f}{' (integrated-GARCH boundary: volatility shocks do not decay)' if extras.get('garch_persistence', 0) >= 0.999 else ''}.
- Cornish-Fisher expansion monotone: {extras.get('cornish_fisher_monotone')}.
""")

ratios = parquet("risk_es_var_ratios.parquet")
if ratios is not None:
    st.subheader("ES / VaR against the Normal reference")
    st.dataframe(ratios.pivot(index="model", columns="alpha", values="es_var_ratio").style.format("{:.3f}"),
                 width="stretch")
    st.caption("Normal reference: 1.254 at 95%, 1.146 at 99%. Higher ratios mean a heavier tail beyond VaR.")

contrib = parquet("risk_contributions.parquet")
if contrib is not None:
    st.subheader("Euler risk budget: share of capital vs share of 99% ES")
    hist = contrib[contrib.method == "historical ES 99%"]
    st.plotly_chart(charts.capital_vs_risk(hist, "Capital vs tail-risk contribution"), width="stretch")
    st.dataframe(hist[["weight", "pct_contribution", "risk_to_capital"]].style.format(
        {"weight": "{:.1%}", "pct_contribution": "{:.1%}", "risk_to_capital": "{:.2f}"}), width="stretch")
    st.caption("Risk-to-capital above 1.5 means an asset takes more than 1.5× its capital share of tail risk.")
