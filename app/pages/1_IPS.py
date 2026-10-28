import pandas as pd
import streamlit as st

from components import charts
from components.data import config, jsonfile, parquet
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
st.info("Calibration (team decision 2026-10-28): AGG may be held up to 65%, because with AGG under the 40% single-asset "
        "cap and GLD ≤ 20% at least 40% had to sit in equities. All other limits are unchanged; the original "
        "AGG ≤ 40% case is kept as a sensitivity (`doc/decisions/ips_calibration.md`).")
st.caption("Policy benchmark: 60/40 SPY/AGG. Note that the benchmark itself breaches the IPS (SPY 60% > 40%; equity 60% > 50%).")

feas, tab = jsonfile("ips_feasibility.json"), parquet("ips_feasibility.parquet")
st.subheader("Feasibility across the frontier")
st.caption("Every IPS-compliant frontier portfolio and the minimum-ES portfolio, held fixed over 2004–2022 "
           "(development + validation). Weights are chosen on the same data, so this is an optimistic screen: "
           "a limit no portfolio meets here cannot be met out of sample either.")
if feas and tab is not None:
    labels = {"adopted": "Adopted IPS (AGG ≤ 65%)", "original_agg40": "Original IPS (AGG ≤ 40%)"}
    cols = st.columns(len(feas))
    for col, (case, s) in zip(cols, feas.items(), strict=True):
        col.plotly_chart(charts.feasibility_frontier(tab[tab["case"] == case], s["required_return"],
                                                     cfg.ips["limits"]["es99_1d_max"], labels.get(case, case)),
                         width="stretch")
        col.markdown(f"**{s['finding'].split(':')[0].capitalize()}:** {s['finding'].split(': ', 1)[1]}.")
        col.caption(f"{s['points_meeting_risk_limits']} of {s['points']} portfolios meet every risk limit; "
                    f"lowest achievable ES {pct(s['min_es99_1d'])}, volatility {pct(s['min_volatility'])}, "
                    f"stress drawdown {pct(s['min_stress_drawdown'], 1)}.")
    with st.expander("Table"):
        show = ["case", "expected_return", "cagr", "volatility", "es99_1d", "stress_drawdown", "risk_ok", "return_ok",
                *cfg.universe]
        st.dataframe(tab[show], width="stretch")
    st.caption("Expected return = CAPM prior (rf at the end of 2022 + β × 5% market premium), the optimiser's own "
               "estimate; realised CAGR is in the table.")
else:
    st.warning("Run the pipeline to compute the feasibility study.")
