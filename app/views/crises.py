"""What can go wrong: every crisis with the recommended weights, against one budget, and a scenario to try."""

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from components.ui import artifact, explain, money, need_numbers, pct, returns_to_decision, say
from quantedge.config import load_config
from quantedge.stress.factor import (
    episode_plausibility,
    scenario_contributions,
    scenario_loss,
    weekly_factors,
)
from quantedge.stress.reverse import most_likely_breach, stressed_sigma

n = need_numbers()
cfg = load_config()
nav, budget = n["nav_usd"], n["limits"]["crisis_budget"]
w = pd.Series(n["weights"])
hyp = cfg.stress["hypothetical"]
ACCENT, GREY, CRIT = "#1F5FAE", "#A3ABB5", "#B42318"

KIND = {"GFC 2008": ("Deflationary crash", "Stocks fell about 55%; Treasuries rallied, so bonds cushioned the fall."),
        "COVID crash 2020": ("Liquidity panic", "Everything was sold for cash for a few days, bonds included; oil collapsed."),
        "Rate shock 2022": ("Inflation shock", "Stocks and bonds fell together, so the bond hedge failed."),
        "2025 tariff shock (pre-registered)": ("'Sell America'", "US stocks, Treasuries and the dollar fell together."),
        "2026 Hormuz shock (pre-registered)": ("Oil shock", "Oil and yields rose; the energy holding gained."),
        f"{hyp['name']} (scenario)": ("Our stagflation scenario", "Yields +250 bp, oil +40%, VIX +25, dollar +8%, credit +150 bp, "
                                     "plus one panic day on AGG.")}
cm = pd.Series(n["crisis_map"]).sort_values(ascending=False)

st.title("What can go wrong?")
say(f"The portfolio is built to lose **less than {pct(budget, 0)} ({money(budget * nav)})** in every kind of crisis we can "
    "measure, while still paying the scholarships.")

with st.container(horizontal=True):
    st.metric("Worst crisis on record", f"−{money(cm.max() * nav)}", cm.idxmax().replace(" (scenario)", ""), delta_color="off",
              delta_arrow="off", border=True, help="The largest peak-to-trough loss of today's portfolio in any crisis replay.")
    st.metric("Crises inside the budget", f"{int((cm <= budget).sum())} of {len(cm)}", f"budget {money(budget * nav)}",
              delta_color="off", delta_arrow="off", border=True,
              help="Four past crises, two recent market shocks and one crisis we designed.")
    st.metric("Our stagflation scenario", f"−{money(n['scenario']['loss'] * nav)}", "the crisis bonds can't hedge",
              delta_color="off", delta_arrow="off", border=True,
              help="A crisis we designed ourselves, in which stocks and bonds fall together.")

df = pd.DataFrame({"crisis": [k.replace(" (pre-registered)", "").replace(" (scenario)", "") for k in cm.index],
                   "kind": [KIND[k][0] for k in cm.index], "loss": cm.values * nav,
                   "label": [f"−{money(v * nav)} ({pct(v)})" for v in cm.values],
                   "type": ["our scenario" if "scenario" in k else "happened" for k in cm.index]})
bars = alt.Chart(df).mark_bar(cornerRadiusEnd=4, height=24).encode(
    y=alt.Y("crisis:N", sort=None, title=None, axis=alt.Axis(labelLimit=260, labelFontSize=13)),
    x=alt.X("loss:Q", title="Worst loss during the episode (USD)", scale=alt.Scale(domain=[0, budget * nav * 1.22]),
            axis=alt.Axis(format="$~s", tickCount=6)),
    color=alt.Color("type:N", scale=alt.Scale(domain=["happened", "our scenario"], range=[GREY, ACCENT]),
                    legend=alt.Legend(title=None, orient="bottom")),
    tooltip=["crisis:N", "kind:N", alt.Tooltip("loss:Q", format="$,.0f")])
text = alt.Chart(df).mark_text(align="left", dx=6).encode(y=alt.Y("crisis:N", sort=None), x="loss:Q", text="label:N")
rule = alt.Chart(pd.DataFrame({"x": [budget * nav]})).mark_rule(color=CRIT, strokeWidth=2).encode(x="x:Q")
st.altair_chart((bars + text + rule).properties(height=330), alt="Every crisis against the 25% budget")
explain("Each grey bar shows what today's portfolio would have lost if it had lived through that crisis. The blue bar "
        "is a crisis we designed: inflation and interest rates jump, oil spikes and stocks and bonds fall together. The red "
        f"line is the most the committee is willing to lose in a crisis ({pct(budget, 0)}, {money(budget * nav)}). "
        + ("Every bar stays left of it. " if (cm <= budget).all() else "Bars crossing it break the budget. ") + "Bonds "
        "protect the fund in a crash like 2008, but not when inflation pushes rates up (2022), which is why the limit is "
        "set as a maximum loss rather than relying on bonds alone.")

st.subheader("Try a crisis yourself", divider=False)
say("Move the sliders to create your own crisis and see what the fund would lose. They start at the crisis we designed.")
betas = artifact("decision_scenario_betas.parquet")
base = hyp["shock"]
panel = st.container(border=True)
c = panel.columns(5, gap="medium")
shock = {"d_yield10_bp": c[0].slider("10-year yield (bp)", -150, 400, int(base["d_yield10_bp"]), 10, key="s_y"),
         "dln_oil": float(np.log1p(c[1].slider("Oil (%)", -60, 100, round((np.exp(base["dln_oil"]) - 1) * 100), 5, key="s_o") / 100)),
         "d_vix": c[2].slider("VIX (points)", -10, 60, int(base["d_vix"]), 1, key="s_v"),
         "dln_usd": float(np.log1p(c[3].slider("Dollar (%)", -15, 20, round((np.exp(base["dln_usd"]) - 1) * 100), 1, key="s_d") / 100)),
         "d_credit_bp": c[4].slider("Credit spread (bp)", -50, 500, int(base["d_credit_bp"]), 10, key="s_c")}
liq = panel.toggle("Add a panic day on bonds (AGG −5%)", value=True, key="s_l")
liq_day = hyp.get("liquidity_day") if liq else None
loss = scenario_loss(betas, shock, w, liq_day)
inside = loss <= budget
with st.container(horizontal=True, vertical_alignment="center", gap="medium"):
    st.metric("Portfolio loss" if loss >= 0 else "Portfolio gain", money(-loss * nav, signed=True),
              f"{pct(abs(loss))} of the endowment", delta_color="off", delta_arrow="off", border=True, width="content")
    st.badge("Inside the budget" if inside else "Breaks the budget", icon=":material/check_circle:" if inside else ":material/error:",
             color="green" if inside else "red")
    # Plausibility (booklet p. 8): how often history produced a three-quarter episode at least this extreme.
    macro = artifact("clean_macro.parquet").loc[lambda m: m.index < pd.Timestamp(n["decision_date"])]
    pl = episode_plausibility(weekly_factors(macro), shock)
    share = pl.share_more_extreme
    label, colour = (("Seen often in history", "green") if share >= 0.05 else ("Severe but seen before", "orange")
                     if share >= 0.01 else ("Extreme: rarer than 1 in 100", "red") if share > 0 else
                     ("Beyond anything since " + str(pl.start.year), "red"))
    st.badge(label, icon=":material/history:", color=colour,
             help=f"Of the {pl.n_episodes:,} three-quarter periods since {pl.start.year}, {share:.1%} were more extreme "
                  "once all five moves are taken together (Mahalanobis distance). Overlapping periods, so read it as a "
                  "frequency, not a probability.")
NAMES_F = {"d_yield10_bp": "yield", "dln_oil": "oil", "d_vix": "VIX", "dln_usd": "dollar", "d_credit_bp": "credit spread"}
st.caption("How often history went at least this far in three quarters since " + str(pl.start.year) + ": "
           + ", ".join(f"{NAMES_F[f]} {'never' if v == 0 else f'{v:.1%} of periods' if v < 0.01 else f'{v:.0%} of periods'}" for f, v in pl.per_factor.items())
           + f"; all five together, {share:.1%}.")
# Losses are positive (the page's convention); the bars add up exactly to the card, panic day included.
parts = scenario_contributions(betas, shock, w, liq_day)
cd = pd.DataFrame({"fund": parts.index, "loss": -parts.values * nav})
cd["label"] = [money(v) if v >= 0 else f"helps {money(-v)}" for v in cd["loss"]]
cd["effect"] = np.where(cd["loss"] >= 0, "loses money", "helps")
lo, hi = min(0.0, cd["loss"].min()), max(0.0, cd["loss"].max())
pad = (hi - lo) * 0.18
order = cd.sort_values("loss", ascending=False)["fund"].tolist()
base = alt.Chart(cd).encode(y=alt.Y("fund:N", sort=order, title=None, axis=alt.Axis(labelFontSize=13)))
bars = base.mark_bar(cornerRadiusEnd=3, height=22).encode(
    x=alt.X("loss:Q", title="Share of the loss (USD)", scale=alt.Scale(domain=[lo - (pad if lo < 0 else 0), hi + pad]),
            axis=alt.Axis(format="$~s", tickCount=6)),
    color=alt.Color("effect:N", scale=alt.Scale(domain=["loses money", "helps"], range=[CRIT, "#0D7A2F"]),
                    legend=alt.Legend(title=None, orient="bottom")),
    tooltip=["fund:N", alt.Tooltip("loss:Q", title="loss (USD)", format="$,.0f")])
# Labels sit past the end of each bar: right of a loss, left of a gain (blank text on the other side).
gain_right = base.mark_text(dx=6, align="left").encode(x="loss:Q", text=alt.condition("datum.loss >= 0", "label:N", alt.value("")))
gain_left = base.mark_text(dx=-6, align="right").encode(x="loss:Q", text=alt.condition("datum.loss < 0", "label:N", alt.value("")))
st.altair_chart((bars + gain_right + gain_left).properties(height=alt.Step(38)), alt="Where the scenario loss comes from")
explain("Each fund's move is based on how it reacted to these kinds of market moves in past stressful periods. The bars "
        "add up to the loss on the card: red bars lose money in your crisis, green bars help. The panic day has its own "
        "row: a one-day 5% drop in the bond fund, like the one on 10 October 2008 when bond-fund prices fell below the "
        "value of their bonds.")

with st.expander("Every crisis in detail", icon=":material/table:"):
    years = {k: (pd.Timestamp(b) - pd.Timestamp(a)).days / 365.25
             for k, (a, b) in {**cfg.stress["historical"], **{f"{k} (pre-registered)": v for k, v in cfg.stress.get("preregistered", {}).items()}}.items()}
    rows = [{"Episode": k.replace(" (pre-registered)", "").replace(" (scenario)", " (our design)"), "Kind": KIND[k][0], "Loss": f"−{money(v * nav)}",
             "Endowment at the bottom, after scholarships": money(nav * (1 - v) - 0.03 * nav * years.get(k, 0.75)),
             "What happened": KIND[k][1]} for k, v in cm.items()]
    st.table(pd.DataFrame(rows).set_index("Episode"))

with st.expander("What would it take to lose 25%? (reverse stress)", icon=":material/undo:"):
    returns = returns_to_decision()
    h = int(cfg.stress["reverse"]["horizon_days"])
    calm = most_likely_breach(returns.cov(), w, budget, h)
    crisis = most_likely_breach(stressed_sigma(returns, cfg.stress["historical"]), w, budget, h)
    st.dataframe(pd.DataFrame({"In calm markets": calm.x_star, "In a crisis": crisis.x_star}).style.format("{:+.1%}"),
                 alt="Most plausible fund moves that would cost 25%")
    say(f"The table shows the most likely combination of fund moves that would cost {pct(budget, 0)} within a month: a broad "
        f"stock crash with bonds not helping. In calm markets that is roughly a once-in-{calm.years_between:,.0f}-years event; "
        f"when markets are already in crisis mode it becomes about once in {crisis.years_between:,.0f} years. Treat these as "
        "rough: real crises are more frequent than simple models suggest.")
