import plotly.graph_objects as go
import streamlit as st

from components.charts import LAYOUT
from components.data import jsonfile, parquet, require
from components.ui import money

st.title("Tail risk (EVT) diagnostics")
st.markdown("How the tail of the loss distribution was modelled: the peaks-over-threshold method fits a Generalised Pareto distribution to losses above a high threshold. The locked choice is the **90% quantile** (notebook 03 §3); the rules below show how much the choice matters. Fitted on data to end-2022, before the freeze.")

ev = parquet("evt_threshold_evidence.parquet")
sens = parquet("evt_sensitivity.parquet")
if not (require(ev, "EVT threshold evidence") and require(sens, "The EVT sensitivity table")):
    st.stop()

st.subheader("Threshold choice: stability of ξ across candidate thresholds")
fig = go.Figure()
fig.add_scatter(x=ev["quantile"], y=ev["xi"], mode="lines+markers", name="ξ",
                error_y=dict(type="data", symmetric=False, array=ev["xi_hi"] - ev["xi"], arrayminus=ev["xi"] - ev["xi_lo"]))
fig.update_xaxes(title="Threshold quantile", tickformat=".1%")
fig.update_yaxes(title="Shape ξ (95% CI)")
st.plotly_chart(fig.update_layout(**LAYOUT), width="stretch")
st.dataframe(ev[["quantile", "u", "n_u", "xi", "se_xi", "beta_star", "ad_p", "ks_p"]].rename(columns={
    "quantile": "threshold quantile", "u": "threshold (loss)", "n_u": "losses above it", "xi": "shape ξ", "se_xi": "ξ std. error",
    "beta_star": "scale β*", "ad_p": "Anderson-Darling p", "ks_p": "Kolmogorov-Smirnov p"}).round(4),
             width="stretch", hide_index=True)
st.markdown("""
- **Rule A (diagnostic):** lowest threshold with stable ξ, at least 50 exceedances and an Anderson-Darling bootstrap p > 0.10.
- **Rule B (ForwardStop, Bader et al. 2018):** sequential goodness-of-fit testing with false-discovery control at 10%.
- **Rule C (fixed 95%):** naive benchmark, shown only to measure how much the rule matters.
""")

st.subheader("Rule sensitivity")
cols = [c for c in sens.columns if c.startswith(("var_", "es_"))]
st.dataframe(sens.drop(columns=["portfolio"]).style.format({c: "{:.3%}" for c in cols} | {"u": "{:.4f}", "xi": "{:.3f}",
                                                                                        "xi_se": "{:.3f}", "beta": "{:.4f}"}),
             width="stretch", hide_index=True)
st.caption("At 99% the rules agree; they diverge only in the far tail, where EVT's confidence intervals are wide.")

extras = jsonfile("risk_extras.json")
rl = extras.get("return_level_10y_evt")
if rl is not None:
    st.metric("Once-in-10-years daily loss (EVT, end-2022 fit)", money(rl * 10_000_000))
    st.caption(f"{rl:.2%} of the endowment")
st.caption("ξ is the tail-shape parameter: ξ = 0.2 means the loss tail decays like a power law with index 5. "
           "It is not a crash probability.")
