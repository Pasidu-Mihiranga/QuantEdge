"""Try your own portfolio: any weights, measured exactly as the recommendation is. Calculated in the app from saved data."""

import pandas as pd
import streamlit as st

from components.ui import artifact, explain, money, need_numbers, pct, returns_to_decision, say
from quantedge.config import load_config
from quantedge.data.partition import load_returns
from quantedge.decision.ips import IPSLimits
from quantedge.decision.objective import (
    crisis_loss,
    forward_asset_returns,
    forward_inputs,
    forward_portfolio_return,
    through_the_cycle,
)
from quantedge.portfolio.custom import custom_check, normalise
from quantedge.stress.factor import scenario_loss

n = need_numbers()
cfg = load_config()
nav, lim, req = n["nav_usd"], n["limits"], n["objective"]["required_return"]
hyp = cfg.stress["hypothetical"]
NAMES = {"SPY": "US stocks", "EFA": "Developed stocks", "EEM": "Emerging stocks", "AGG": "US bonds", "GLD": "Gold",
         "XLE": "Energy stocks", "XLK": "Technology stocks"}


@st.cache_data
def inputs() -> dict:
    return forward_inputs(returns_to_decision(), artifact("clean_prices.parquet"), artifact("clean_dividends.parquet"),
                          artifact("clean_macro.parquet"), pd.Timestamp(n["decision_date"]), cfg.ips["forward"]["beta_window"])


st.title("Try your own portfolio")
st.badge("Your portfolio, not our recommendation. Nothing here changes the decision.", icon=":material/science:", color="blue")
say("Set any mix of the seven funds and see it measured exactly as our recommendation was. Weights are scaled to add up to 100%.")

start = pd.Series(n["weights"]).round(3) * 100
panel = st.container(border=True)
cols = panel.columns(7, gap="small")
raw = {t: c.slider(NAMES[t], 0.0, 100.0, float(start[t]), 0.1, format="%.1f%%", key=f"cw_{t}", help=t) for t, c in zip(NAMES, cols, strict=True)}
if sum(raw.values()) <= 0:
    st.warning("Give at least one fund a weight.", icon=":material/warning:")
    st.stop()

returns = returns_to_decision()
w = normalise(raw, list(returns.columns))
if (w - pd.Series(n["weights"]).reindex(w.index)).abs().max() < 1e-3:   # untouched sliders are the recommendation itself
    w = pd.Series(n["weights"]).reindex(w.index)
f = inputs()
net = forward_asset_returns(f["y10"], f["inflation"], f["beta"], f["div_yield"], cfg.ips["forward"])
expected = forward_portfolio_return(w, net, f["cov_long"])
windows = {**cfg.stress["historical"], **cfg.stress.get("preregistered", {})}
crises = crisis_loss(w, returns, windows)
stress = max(float(crises.max()), scenario_loss(artifact("decision_scenario_betas.parquet"), hyp["shock"], w, hyp.get("liquidity_day")))
ttc = through_the_cycle(w, load_returns("dev", cfg))
check = custom_check(w, returns, IPSLimits.from_config(cfg.ips), cfg.stress["historical"])

tests = {"objective": expected >= req, "crisis": stress <= lim["crisis_budget"] + 1e-9, "bad day": ttc["es99_1d"] <= lim["es99_max"] + 1e-9,
         "volatility": ttc["vol_ann"] <= lim["vol_max"] + 1e-9, "caps": check["weights_ok"]}
with st.container(horizontal=True):
    st.metric("Expected return a year", pct(expected, 2), f"needs {pct(req, 2)}", delta_color="off", delta_arrow="off", border=True)
    st.metric("Worst crisis", pct(stress), f"budget {pct(lim['crisis_budget'], 0)} · {money(stress * nav)}", delta_color="off", delta_arrow="off", border=True)
    st.metric("A very bad day", pct(ttc["es99_1d"], 2), f"limit {pct(lim['es99_max'], 2)} · {money(ttc['es99_1d'] * nav)}", delta_color="off", delta_arrow="off", border=True)
    st.metric("Volatility", pct(ttc["vol_ann"], 2), f"limit {pct(lim['vol_max'], 2)}", delta_color="off", delta_arrow="off", border=True)
with st.container(horizontal=True):
    for name, ok in tests.items():
        st.badge(f"{name.capitalize()}: {'met' if ok else 'broken'}", color="green" if ok else "red",
                 icon=":material/check_circle:" if ok else ":material/error:")

st.subheader("By model", divider=False)
risk = check["risk"]
t = risk.pivot(index="model", columns="alpha", values=["var", "es"]) * nav
st.table(pd.DataFrame({f"{'VaR' if m == 'var' else 'ES'} {a:.0%}": t[(m, a)].map(money) for m in ("var", "es") for a in (0.95, 0.99)}))
failed = check["weight_checks"].loc[lambda d: ~d["passed"]]
if len(failed):
    st.caption("Position limits broken: " + ", ".join(str(x) for x in failed.iloc[:, 0]) + ".")
explain("Expected return uses the same forward estimate as our recommendation, after fees and tax. The crisis figure is the worst replay or "
        "our stagflation scenario. A very bad day and volatility use 2004–2018 data, which includes 2008. The table uses the last 500 trading "
        "days, in dollars, so it shows calm-market figures. A model-tested forecast exists only for the recommended portfolio.")
