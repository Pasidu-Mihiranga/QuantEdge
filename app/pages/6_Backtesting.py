import streamlit as st

from components import charts
from components.data import ML_FILES, backtest, jsonfile, ml_forecast, parquet, require
from components.sidebar import provisional_banner, sidebar
from quantedge.backtest.coverage import clopper_pearson, power_kupiec, rolling_basel
from quantedge.backtest.report import selection_table

st.set_page_config(page_title="Backtesting", layout="wide")
ctl = sidebar()
st.title("Backtesting and model validation")
provisional_banner()
st.markdown("<div class='qe-banner qe-locked'>Dev 2004–2018 · Validation 2019–2022 (model selection) · "
            "Final test 2023+ locked until the methodology freeze</div>", unsafe_allow_html=True)

tab_bt, tab_arena = st.tabs(["Backtest", "Model Arena (champion vs challengers)"])

with tab_bt:
    df = backtest(ctl.model, ctl.window)
    if ctl.window != 500:
        st.info(f"Sensitivity view: estimation window {ctl.window} days (the official window is 500).")
    if not require(df, f"The {ctl.model} backtest"):
        st.stop()
    a = ctl.alpha if ctl.alpha in (0.95, 0.99) else 0.95
    d = df.loc[ctl.start:ctl.end]
    st.plotly_chart(charts.exceptions_chart(d, a, f"{ctl.model}: VaR {a:.0%} vs realised loss (out-of-sample)"),
                    width="stretch")
    t = selection_table({ctl.model: d}, a).iloc[0]
    lo, hi = clopper_pearson(int(t.exceptions), int(t["T"]))
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Exceptions / expected", f"{int(t.exceptions)} / {t.expected:.1f}", f"rate CI {lo:.2%}–{hi:.2%}", delta_color="off")
    c2.metric("Kupiec p", f"{t.kupiec_p:.3f}")
    c3.metric("Christoffersen independence p", f"{t.ind_p:.3f}")
    c4.metric("Conditional coverage p", f"{t.cc_p:.3f}")
    if a == 0.99:
        roll = rolling_basel(d["hit_0.99"])
        latest = roll["zone"].iloc[-1] if len(roll) else "n/a"
        st.markdown(f"### Basel traffic light (latest 250 days): **{latest.upper()}**")
        st.plotly_chart(charts.zone_band(roll, "Rolling 250-day traffic light"), width="stretch")
        st.caption("Canonical zones (0–4 / 5–9 / ≥10 exceptions) are valid only for 250 days at 99%; longer periods "
                   "use binomial cut-offs (labelled 'Basel-style generalisation').")
    st.caption(f"Power check: with {int(t["T"])} days, Kupiec detects a doubled exception rate with probability "
               f"{power_kupiec(int(t["T"]), 1 - a, 2 * (1 - a)):.0%}. 'Not rejected' is not proof of a correct model.")

    st.subheader("Model selection table")
    split = st.radio("Period", ["val", "dev"], format_func={"val": "Validation 2019–2022 (selection)",
                                                            "dev": "Development 2008–2018"}.get, horizontal=True)
    sel = parquet(f"backtest_selection_{split}_{ctl.window}.parquet")
    if sel is not None:
        cols = ["T", "exceptions", "expected", "kupiec_p", "ind_p", "cc_p", "rolling_red", "worst_250d_exceptions",
                "z2_975", "z2_zone", "pinball", "fz0", "passes"]
        st.dataframe(sel[cols].round(5), width="stretch")
    champ = jsonfile("champion.json")
    st.success(f"Champion: **{champ.get('champion')}**: {champ.get('reason')}")
    crises = parquet("backtest_crises_500.parquet")
    if crises is not None:
        st.subheader("Crisis breakdown (99%)")
        st.dataframe(crises.round(4), width="stretch", hide_index=True)

with tab_arena:
    arena = parquet("ml_arena_val.parquet")
    if require(arena, "The ML arena"):
        st.markdown("Primary metric: **99% pinball loss** on validation. Secondary: FZ0 no more than 2% worse than the "
                    "champion, Kupiec and CC not rejected, no red rolling window. DM (Holm-corrected) and the 90% "
                    "Model Confidence Set are reported as uncertainty, not gates. Adoption also needs confirmation "
                    "on the locked final test.")
        cols = ["T", "exceptions", "kupiec_p", "cc_p", "pinball", "fz0", "fz0_vs_champion", "dm_vs_champion",
                "dm_p_holm", "mcs_pvalue", "in_mcs", "passes"]
        st.dataframe(arena[cols].sort_values("pinball").style.format(
            {"pinball": "{:.7f}", "fz0": "{:.4f}", "fz0_vs_champion": "{:+.2%}", "kupiec_p": "{:.3f}", "cc_p": "{:.3f}",
             "dm_vs_champion": "{:.2f}", "dm_p_holm": "{:.3f}", "mcs_pvalue": "{:.3f}"}), width="stretch")
        best = arena.sort_values("pinball").index[0]
        ok = bool(arena.loc[best, "passes"]) and arena.loc[best, "fz0_vs_champion"] <= 0.02
        st.info(f"Validation leader: **{best}**. Conditions 1–2 {'met' if ok else 'not met'}; condition 3 (final test) "
                "pending the methodology freeze.")
        name = st.selectbox("Challenger forecasts", list(ML_FILES))
        f = ml_forecast(name)
        if f is not None:
            st.plotly_chart(charts.exceptions_chart(f.loc[ctl.start:ctl.end], 0.99, f"{name}: 99% VaR vs loss"),
                            width="stretch")
        st.caption("Challengers: linear quantile regression (baseline) and LightGBM quantile models; the LSTM (Step 23) "
                   "joins when trained. Point-in-time weights and lagged features only; see Step 22.")
        explain, imp = jsonfile("ml_explain.json"), parquet("ml_shap_importance.parquet")
        with st.expander("Explainability (LightGBM, 99% VaR)", expanded=False):
            if explain and imp is not None:
                st.caption(f"One fit with the selected configuration, trained on {explain['trained_on'][0]} to "
                           f"{explain['trained_on'][1]} (development only) and explaining validation forecasts. The arena "
                           "retrains every 21 days, so this is a representative fit (`scripts/run_ml_explain.py`).")
                st.plotly_chart(charts.importance_bars(imp["mean_abs_shap"], "What drives the forecast"), width="stretch")
                crisis = parquet("ml_shap_crisis_day.parquet")
                if crisis is not None:
                    st.markdown(f"**Highest forecast in validation:** origin {explain['crisis_day_origin']}, 99% VaR "
                                f"{explain['crisis_day_var99']:.2%} (model average {explain['crisis_day_expected_value']:.2%}). "
                                "Largest contributions:")
                    st.dataframe(crisis.head(8).style.format({"value": "{:.4f}", "shap": "{:+.4%}"}), width="stretch")
                mono = parquet("ml_monotonicity.parquet")
                if mono is not None:
                    st.markdown("**Monotonicity in volatility.** LightGBM 4.x cannot impose monotone constraints with the "
                                "quantile objective, so it is measured: the share of days whose forecast falls anywhere "
                                "as one volatility feature rises (5–95% range), and how large the largest dip is.")
                    st.dataframe(mono.style.format({"violation_share": "{:.0%}", "median_largest_dip_bp": "{:.1f}",
                                                    "median_total_rise_bp": "{:.1f}", "share_rising_overall": "{:.0%}"}),
                                 width="stretch")
            else:
                st.info("Run `scripts/run_ml_explain.py` to compute SHAP and the monotonicity diagnostic.")
