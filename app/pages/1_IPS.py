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
- **Risk tolerance:** ability moderate (perpetual horizon, but about 4% a year is spent), willingness low → overall **below average**.
- **Constraints:** long-only, no leverage or derivatives, 7 ETFs only, USD mandate with spending in LKR (FX risk outside the model).
""")

req = jsonfile("required_return.json")
st.subheader("Return objective (derived, not assumed)")
if req:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Spending rate", pct(req["spending_rate"], 1))
    c2.metric("Expected inflation (10y avg CPI)", pct(req["inflation"]))
    c3.metric("Costs", pct(req["cost_drag"], 1))
    c4.metric("Required nominal return", pct(req["required_return"]))
    st.caption(f"CPI window {req['cpi_window_start']} to {req['cpi_window_end']} (data up to the end of validation).")

lim = cfg.ips["limits"]
why = {
    "vol_ann_max": "About the volatility of a 35/65 equity/bond policy; consistent with low willingness",
    "stress_drawdown_max": "With 3-year smoothed spending, a 20% drawdown cuts spending by about 7% at most",
    "es99_1d_max": "Daily tail budget ($150k on $10M)",
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
st.info("Calibration status: on 2008–2022 walk-forward data no candidate meets all limits. The 40% single-asset "
        "cap also applies to AGG, which with GLD ≤ 20% forces at least 40% into equities. The team decides whether "
        "to keep the limits (ADJUST verdict) or recalibrate them from the client's tolerance.")
st.caption("Policy benchmark: 60/40 SPY/AGG. Note that the benchmark itself breaches the IPS (SPY 60% > 40%; equity 60% > 50%).")
