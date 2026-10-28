import pandas as pd
import streamlit as st

from components.data import config, jsonfile
from components.sidebar import pct, sidebar

st.set_page_config(page_title="IPS", layout="wide")
sidebar()
cfg = config()
st.title("Investment Policy Statement")

st.subheader("Client profile")
st.markdown("""
- **Perpetual endowment** funding scholarships, research, faculty and capital projects.
- **Committee belief:** avoiding large losses matters more than maximising gains; downside must be measured, tested and defensible.
- **Risk tolerance:** ability moderate (perpetual horizon, 3% a year is spent), willingness low → overall **below average**.
- **Constraints:** long-only, no leverage or derivatives, 7 ETFs only, USD mandate with spending in LKR (FX risk outside the model).
""")

req = jsonfile("required_return.json")
st.subheader("Return objective: CPI + 3.5% (D1)")
if req:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Spending rate (D1)", pct(req["spending_rate"], 1))
    c2.metric("Real growth (D1)", pct(req["real_growth"], 1))
    c3.metric("Expected inflation (breakeven)", pct(req["inflation"]))
    c4.metric("Required nominal return", pct(req["required_return"]))
    st.caption(f"Required = (1 + spending)(1 + growth)(1 + inflation) − 1; inflation is the {req['inflation_source']} "
               f"(10-year average CPI for context: {pct(req['cpi_avg_10y'])}). The expected return it is compared with "
               "is forward-looking and already net of costs (D4: ERP 4.5%, AGG spread 0.5%).")

lim = cfg.ips["limits"]
why = {
    "vol_ann_max": "D2-derived: through-the-cycle volatility of the frontier point whose worst crisis loss is 25%",
    "stress_drawdown_max": "D2 crisis budget: the worst crisis loss the committee accepts (historical replays and the hypothetical)",
    "es99_1d_max": "D2-derived: 99% 1-day ES through the cycle (development data incl. the GFC) at the same point ($223k)",
    "es99_10d_max": "Committee-meeting horizon (reported)",
    "single_asset_max": "Concentration",
    "equity_max": "Conservative profile",
    "cash_max": "Liquidity buffer only (sensitivity)",
}
rows = [{"limit": k, "value": v, "why": why.get(k, "")} for k, v in lim.items() if not isinstance(v, (dict, list))]
rows += [{"limit": f"cap {t}", "value": v, "why": "Sector / EM / no-income concentration"} for t, v in lim["asset_caps"].items()]
rows += [{"limit": f"floor {t}", "value": v, "why": "Income and capital preservation"} for t, v in lim["asset_floors"].items()]
st.subheader("Risk limits")
st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
cal = jsonfile("limit_calibration.json")
if cal:
    st.info(f"Calibration (notebook 03 §4, recomputed by the pipeline to {cal['as_of']}): a {cal['crisis_budget']:.0%} crisis "
            f"budget allows about {cal['equity_share']:.0%} equity, which sets volatility ≤ {cal['vol_ann_max']:.2%} and "
            f"99% ES ≤ {cal['es99_1d_max']:.2%}. IPS v1 (8% / 20% / 1.5%) is kept as a sensitivity case: its volatility "
            "and ES limits contradicted each other (ES is about 4× daily volatility, so 8% volatility implies about 2.1% ES).")
st.caption("Policy benchmark: 60/40 SPY/AGG. Note that the benchmark itself breaches the IPS (SPY 60% > 40%; equity 60% > 50%).")
