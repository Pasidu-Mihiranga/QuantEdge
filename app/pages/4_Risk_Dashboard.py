import pandas as pd
import streamlit as st

from components import charts
from components.data import analysis_returns, config, jsonfile, parquet, require
from components.sidebar import pct, provisional_banner, sidebar, usd
from quantedge.decision.ips import IPSLimits
from quantedge.portfolio.custom import custom_check

st.set_page_config(page_title="Risk Dashboard", layout="wide")
ctl = sidebar()
st.title("Risk dashboard: VaR, ES and EVT")
provisional_banner()



@st.cache_data(show_spinner=False)
def live_check(weights: dict, window: int, heavy: bool, evt_q: float) -> dict:
    cfg = config()
    return custom_check(weights, analysis_returns(), IPSLimits.from_config(cfg.ips), cfg.stress["historical"],
                        window=window, alphas=(0.90, 0.95, 0.99), heavy=heavy, evt_threshold_q=evt_q)


snap = parquet("risk_snapshot.parquet")
if not require(snap, "The risk snapshot"):
    st.stop()

if not ctl.is_recommended and ctl.weights and analysis_returns() is not None:
    st.subheader(f"Selected portfolio: {ctl.portfolio} (live check)")
    evt_tab = parquet("evt_sensitivity.parquet")
    evt_q = float(evt_tab["quantile"].iloc[0]) if evt_tab is not None else 0.90
    key = f"heavy_{sorted(ctl.weights.items())}_{ctl.window}"
    heavy = st.session_state.get(key, False)
    try:
        with st.spinner("Fitting GARCH-FHS and EVT…" if heavy else "Computing…"):
            chk = live_check(ctl.weights, ctl.window, heavy, evt_q)
    except ValueError as e:
        st.error(f"These weights cannot be checked: {e}.")
        st.stop()
    w = chk["weights"]
    c1, c2 = st.columns([1, 2])
    c1.dataframe(w[w > 1e-6].rename("weight").to_frame().style.format("{:.1%}"), width="stretch")
    breaches = chk["weight_checks"][~chk["weight_checks"]["passed"]]
    if chk["weights_ok"]:
        c2.success("Weights meet every IPS weight limit.")
    else:
        c2.error("IPS weight limits breached: " + "; ".join(
            f"{r['name']} {r['value']:.1%} vs {r['limit']:.0%}" for _, r in breaches.iterrows()))
    rc = chk["risk_checks"].set_index("name")
    labels = {"vol_ann": "Volatility (annualised)", "es99_1d": "99% 1-day ES (historical)",
              "stress_drawdown": "Worst stress-window drawdown"}
    c2.dataframe(pd.DataFrame({"value": rc["value"], "limit": rc["limit"], "passes": rc["passed"]})
                 .rename(index=labels).style.format({"value": "{:.2%}", "limit": "{:.1%}"}), width="stretch")
    c2.caption(f"Fixed weights over {chk['sample'][0]} to {chk['sample'][1]} (development + validation).")
    live = chk["risk"][chk["risk"]["alpha"] == ctl.alpha].set_index("model")
    rec = snap[snap.alpha == ctl.alpha].set_index("model")
    table = pd.DataFrame({"VaR": live["var"], "ES": live["es"], "ES (USD)": live["es"] * ctl.nav,
                          "ES, recommended": rec["es"].reindex(live.index)})
    st.dataframe(table.style.format({"VaR": "{:.3%}", "ES": "{:.3%}", "ES (USD)": "${:,.0f}",
                                     "ES, recommended": "{:.3%}"}, na_rep="—"), width="stretch")
    st.caption(f"1-day · {ctl.alpha:.0%} · fitted on the last {ctl.window} days ({chk['window'][0]} to {chk['window'][1]}). "
               "The recommended column uses the precomputed 500-day snapshot.")
    if not heavy and st.button("Also fit GARCH-FHS and EVT (a few seconds)"):
        st.session_state[key] = True
        st.rerun()
    worst = table["ES"].max()
    st.markdown(f"**What this means:** on a bad day (the worst {1 - ctl.alpha:.0%} of days), this portfolio would lose "
                f"about {usd(worst * ctl.nav)} on average under the most cautious model shown"
                f"{'' if chk['risk_ok'] else ', and it breaches at least one IPS risk limit over 2004–2022'}.")
    st.divider()
    st.caption("Everything below is precomputed for the recommended portfolio.")
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

if ctl.horizon == 10:
    h10 = parquet("risk_horizon_10d.parquet")
    if h10 is not None:
        st.subheader("10-day horizon")
        show = h10[h10.alpha == (a if a in (0.95, 0.99) else 0.99)].set_index("method")[["var", "es"]]
        st.dataframe(show.assign(var_usd=show["var"] * ctl.nav, es_usd=show["es"] * ctl.nav).style.format(
            {"var": "{:.2%}", "es": "{:.2%}", "var_usd": "${:,.0f}", "es_usd": "${:,.0f}"}), width="stretch")
        st.caption("√10 scaling assumes i.i.d. returns, which the tests reject: shown only as a comparison. "
                   f"IPS reported limit for 10-day 99% ES: {extras.get('es99_10d_limit', 0.05):.0%} of NAV.")

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
