import streamlit as st

from components.sidebar import sidebar
from quantedge.paths import ROOT
from quantedge.risk.examples import subadditivity_demo

st.set_page_config(page_title="Methodology & AI Disclosure", layout="wide")
sidebar()
st.title("Methodology and AI disclosure")

st.subheader("Conventions")
st.markdown(r"""
- Simple returns aggregate across assets: $R_{p,t} = \sum_i w_{i,t-1} R_{i,t}$. Log returns only for single-series statistics.
- Loss $\ell_t = -R_{p,t}$; **VaR and ES are positive numbers meaning losses**; horizon 1 day unless stated.
- Every forecast for day $t$ uses data up to $t-1$; weights are those actually held (point-in-time).
- Partition: development 2004-11-18 to 2018-12-31, validation 2019-01-01 to 2022-12-31, final test 2023-01-01 onwards (locked).
""")
st.subheader("Key formulas")
st.latex(r"\text{ES}_\alpha = \frac{1}{1-\alpha}\int_\alpha^1 \text{VaR}_u\,du")
st.latex(r"\text{VaR}_p = u + \frac{\beta}{\xi}\left[\left(\frac{n}{N_u}(1-p)\right)^{-\xi} - 1\right],\quad "
         r"\text{ES}_p = \frac{\text{VaR}_p}{1-\xi} + \frac{\beta - \xi u}{1-\xi}")
st.latex(r"LR_{POF} = -2\ln\left[(1-p)^{T-x}p^x\right] + 2\ln\left[(1-\hat p)^{T-x}\hat p^x\right]")

st.subheader("Why ES as well as VaR: VaR is not subadditive")
d = subadditivity_demo()
st.markdown(f"""Two independent bonds each lose 100 with probability 4% (otherwise earn 5). At 95%:
each bond's VaR is **{d['var_single']:.0f}**, so the sum is {d['var_sum_of_singles']:.0f}, but the pair's VaR is
**{d['var_portfolio']:.0f}**. ES stays subadditive: {d['es_portfolio']:.1f} ≤ {d['es_sum_of_singles']:.1f}.""")

st.subheader("AI disclosure")
log = ROOT / "doc" / "ai_log.md"
if log.exists():
    st.markdown(log.read_text(encoding="utf-8"))
st.caption("Portfolio choice, IPS limits, threshold choice, scenario design, interpretation and the final "
           "recommendation are the team's own judgement.")
