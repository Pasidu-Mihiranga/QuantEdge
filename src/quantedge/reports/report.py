"""Technical report builder (Step 17 §3.1).

    python -m quantedge.reports.report   -> reports/report.html
    python scripts/build_pdfs.py         -> the report, memo and tear sheet as PDF

Generated content (every table and figure) is rebuilt on each run from the final weights in
decision_numbers.json. The team's narrative lives in reports/narrative/NN_*.md: each file is created
once with a [TEAM] prompt and is never overwritten, so re-running the pipeline cannot lose the team's
writing. A line {{name}} in a narrative places that generated block; blocks not placed follow the text.
"""

from __future__ import annotations

import html
import json
import re

import numpy as np
import pandas as pd

from quantedge.config import Config, load_config
from quantedge.data.partition import load_returns
from quantedge.decision.decision_date import es_shares
from quantedge.decision.objective import crisis_loss
from quantedge.paths import ARTIFACTS, ROOT
from quantedge.portfolio.capm import capm_regression
from quantedge.portfolio.metrics import kpi_table
from quantedge.reports import charts
from quantedge.reports.final import FONT, FONT_LINK, TEAM
from quantedge.reports.limitations import LIMITATIONS
from quantedge.risk import evt
from quantedge.stress.reverse import most_likely_breach, rarity_text, stressed_sigma

NARRATIVE = ROOT / "reports" / "narrative"

SECTIONS = [
    ("00_executive_summary", "Executive summary", "1 page",
     "State the recommendation, the allocation and the five key numbers in plain English."),
    ("01_mandate_ips", "Client mandate and Investment Policy Statement", "1.5 pages",
     "Explain the return objective, the risk tolerance, each limit and why, and the AGG-cap recalibration."),
    ("02_data", "Data", "1 page", "Sources, the snapshot, cleaning, flags, stationarity and stylised facts."),
    ("03_portfolio", "Portfolio construction", "2 pages",
     "Candidates, inputs (Ledoit-Wolf, CAPM), the walk-forward scorecard and why the chosen portfolio wins."),
    ("04_risk", "Risk measurement", "2.5 pages",
     "VaR across models and why they disagree, the rationale for ES, EVT threshold evidence and return level."),
    ("05_validation", "Model validation", "1.5 pages",
     "Walk-forward design, coverage tests and their power, the champion and its limits."),
    ("05b_challengers", "Champion–challenger and final test", "0.5–1 page",
     "What the ML challengers showed on validation, and the final-test result once run."),
    ("06_stress", "Stress testing", "1.5 pages",
     "Historical crises, the hypothetical scenario, reverse stress and stressed correlation; the 2022 lesson."),
    ("07_recommendation", "Risk budget and recommendation", "1 page",
     "Euler contributions, the verdict, how close it is, and governance."),
    ("08_limitations", "Assumptions and limitations", "1 page", "Introduce the table; add anything specific to your judgement."),
    ("09_references", "References", "0.5 page", "List the references."),
    ("10_ai_disclosure", "AI disclosure", "1 page", "The disclosure comes from AI_DISCLOSURE.md, unchanged."),
]


def ensure_narrative() -> None:
    NARRATIVE.mkdir(parents=True, exist_ok=True)
    for key, _title, pages, prompt in SECTIONS:
        f = NARRATIVE / f"{key}.md"
        if not f.exists():
            f.write_text(f"[TEAM: {prompt} Target length: {pages}.]\n", encoding="utf-8")


REFERENCES = [
    "Acerbi, C. and Székely, B. (2014). Back-testing expected shortfall. Risk.",
    "Acerbi, C. and Tasche, D. (2002). On the coherence of expected shortfall. Journal of Banking & Finance 26.",
    "Artzner, P., Delbaen, F., Eber, J.-M. and Heath, D. (1999). Coherent measures of risk. Mathematical Finance 9.",
    "Balkema, A. and de Haan, L. (1974). Residual life time at great age. Annals of Probability 2.",
    "Barone-Adesi, G., Giannopoulos, K. and Vosper, L. (1999). VaR without correlations. Journal of Futures Markets 19.",
    "Basel Committee on Banking Supervision (1996). Supervisory framework for the use of backtesting.",
    "Christoffersen, P. (1998). Evaluating interval forecasts. International Economic Review 39.",
    "Diebold, F. and Mariano, R. (1995). Comparing predictive accuracy. Journal of Business & Economic Statistics 13.",
    "Fissler, T. and Ziegel, J. (2016). Higher order elicitability and Osband's principle. Annals of Statistics 44.",
    "Glosten, L., Jagannathan, R. and Runkle, D. (1993). On the relation between the expected value and the volatility of the nominal excess return on stocks. Journal of Finance 48.",
    "Hansen, P., Lunde, A. and Nason, J. (2011). The model confidence set. Econometrica 79.",
    "Koenker, R. and Bassett, G. (1978). Regression quantiles. Econometrica 46.",
    "Kupiec, P. (1995). Techniques for verifying the accuracy of risk measurement models. Journal of Derivatives 3.",
    "Ledoit, O. and Wolf, M. (2004). A well-conditioned estimator for large-dimensional covariance matrices. Journal of Multivariate Analysis 88.",
    "Markowitz, H. (1952). Portfolio selection. Journal of Finance 7.",
    "McNeil, A. and Frey, R. (2000). Estimation of tail-related risk measures for heteroscedastic financial time series. Journal of Empirical Finance 7.",
    "Pickands, J. (1975). Statistical inference using extreme order statistics. Annals of Statistics 3.",
    "Sharpe, W. (1964). Capital asset prices. Journal of Finance 19.",
]


def md_to_html(text: str) -> str:
    """Minimal Markdown: paragraphs, '- ' lists, '### ' headings, '> ' formula lines, **bold**; everything else escaped."""
    out = []
    conv = lambda s: re.sub(r"`(.+?)`", r"<code>\1</code>", re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html.escape(s)))  # noqa: E731
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = block.splitlines()
        if all(line.lstrip().startswith("- ") for line in lines):
            out.append("<ul>" + "".join(f"<li>{conv(line.lstrip()[2:])}</li>" for line in lines) + "</ul>")
        elif all(line.startswith("> ") for line in lines):
            out.append("".join(f"<p class='eq'>{conv(line[2:])}</p>" for line in lines))
        elif block.startswith("### "):
            out.append(f"<h3>{conv(block[4:])}</h3>")
        else:
            cls = " class='team'" if block.lstrip().startswith("[TEAM") else ""
            out.append(f"<p{cls}>{conv(' '.join(lines))}</p>")
    return "\n".join(out)


def table(df: pd.DataFrame, pct: tuple[str, ...] = (), dec: dict[str, int] | None = None, index: bool = True,
          cls: str = "tbl") -> str:
    d = df.copy()
    for c in d.columns:
        if c in pct:
            d[c] = d[c].map(lambda x: f"{x:.2%}" if pd.notna(x) else "")
        elif dec and c in dec:
            d[c] = d[c].map(lambda x, n=dec[c]: f"{x:.{n}f}" if pd.notna(x) else "")
    return d.to_html(index=index, index_names=False, border=0, classes=cls, escape=True)


def disclosure_html() -> str:
    """AI_DISCLOSURE.md word for word."""
    out = []
    for block in re.split(r"\n\s*\n", (ROOT / "AI_DISCLOSURE.md").read_text(encoding="utf-8").strip()):
        out.append(f"<h3>{html.escape(block.lstrip('# '))}</h3>" if block.startswith("#") else md_to_html(block))
    return "".join(out)


def caption(text: str) -> str:
    return f"<p class='cap'>{html.escape(text)}</p>"


def figure(svg: str, text: str) -> str:
    return f"<figure>{svg}{caption(text)}</figure>"


def yes_no(s: pd.Series) -> pd.Series:
    return s.map({True: "yes", False: "no"})


def kusd(x: float) -> str:
    return f"{x / 1e3:,.0f}"


def _p(name: str) -> pd.DataFrame | None:
    path = ARTIFACTS / name
    return pd.read_parquet(path) if path.exists() else None


def _scorecard(perf: pd.DataFrame, rf: pd.Series, spy: pd.Series, start: str) -> pd.DataFrame:
    """The Layer 1 KPIs for one period; CAPM on excess returns with the T-bill rate lagged one day, as in the app."""
    r = perf.dropna().loc[start:]
    capm = {c: capm_regression(r[c] - rf.reindex(r.index), spy.reindex(r.index) - rf.reindex(r.index)) for c in r.columns}
    return kpi_table({c: r[c] for c in r.columns}, rf, r["60/40 benchmark"], betas={c: v.beta for c, v in capm.items()},
                     alphas={c: (v.alpha_ann, v.alpha_t) for c, v in capm.items()})


def _kpi_block(perf: pd.DataFrame, rf: pd.Series, spy: pd.Series) -> str:
    rows = [("Return a year", "cagr", "{:.2%}"), ("Volatility", "volatility", "{:.2%}"), ("Sharpe ratio", "sharpe", "{:.2f}"),
            ("Sortino ratio", "sortino", "{:.2f}"), ("Beta to SPY", "beta", "{:.2f}"), ("Treynor ratio", "treynor", "{:.2%}"),
            ("Jensen's alpha", "jensen_alpha", "{:+.2%}"), ("Information ratio vs 60/40", "information_ratio", "{:.2f}"),
            ("Maximum drawdown", "max_drawdown", "{:.1%}"), ("Calmar ratio", "calmar", "{:.2f}")]
    cols = {}
    for label, start in (("2008–2026", "2008-01-01"), ("2023–2026", "2023-01-01")):
        k = _scorecard(perf, rf, spy, start)
        for who, name in (("Frontier 35% equity", "Recommended"), ("60/40 benchmark", "60/40")):
            cols[f"{name}, {label}"] = [("–" if not np.isfinite(float(k.loc[who, c])) or (c == "information_ratio" and who != "Frontier 35% equity")
                                         else f.format(abs(float(k.loc[who, c])) if c == "max_drawdown" else float(k.loc[who, c]))) for _, c, f in rows]
    return table(pd.DataFrame(cols, index=[r[0] for r in rows]))


def generated(cfg: Config) -> dict[str, dict[str, str]]:
    """Every generated block, section by section, on the final weights unless its caption says otherwise."""
    n = json.loads((ARTIFACTS / "decision_numbers.json").read_text(encoding="utf-8"))
    nav = n["nav_usd"]
    o, r, lm, mv, rd = n["objective"], n["risk"], n["limits"], n["model_validity"], n["risk_day"]
    w = pd.Series(n["weights"]).loc[lambda s: s > 1e-4]
    returns = load_returns("all", cfg, frozen=True)
    past = returns.loc[returns.index < pd.Timestamp(n["decision_date"])]
    perf, fr = _p("decision_performance.parquet"), _p("decision_frontier.parquet")
    snap = _p("decision_risk_snapshot.parquet")
    cm = pd.Series(n["crisis_map"])
    lim = cfg.ips["limits"]
    g: dict[str, dict[str, str]] = {}

    held = w.sort_values(ascending=False)
    weights = pd.DataFrame({"Weight": held.map("{:.1%}".format), "USD": (held * nav).map("{:,.0f}".format)})
    g["00_executive_summary"] = {
        "verdict": f"<p class='verdict'>Decision of {n['decision_date']}: <b>{html.escape(n['verdict'])}</b> at {n['advised_equity']:.0%} equity</p>",
        "key_numbers": "<div class='two'>" + table(weights) + table(pd.DataFrame({"Result": {
            "Expected return a year": f"{n['expected_return']:.2%}", "Required return": f"{o['required_return']:.2%}",
            "Worst crisis replay": f"{r['worst_crisis_loss']:.1%} ({r['worst_crisis']})", "Our scenario": f"{r['hypothetical_loss']:.1%}",
            "99% ES, full cycle": f"USD {r['es99_ttc'] * nav:,.0f}", "Income a year": f"USD {r['income_yield'] * nav:,.0f}",
            "One-shot test": f"{mv['exceptions']} breaches vs {mv['expected']:.1f} expected"}})) + "</div>"}

    largest = n["largest_es_share"]
    g["01_mandate_ips"] = {"limits": table(pd.DataFrame([
        ("Crisis budget", lm["crisis_budget"], r["d2_loss"], "Team's stated tolerance; sets the two below"),
        ("Volatility, full cycle", lm["vol_max"], r["vol_ttc"], "Frontier point at the crisis budget"),
        ("99% 1-day ES, full cycle", lm["es99_max"], r["es99_ttc"], "Frontier point at the crisis budget"),
        ("Equity", lim["equity_max"], n["advised_equity"], "Conservative mandate"),
        ("AGG", lim["asset_caps"]["AGG"], w["AGG"], "Leaves 35% for equity and gold"),
        ("XLE", lim["asset_caps"]["XLE"], w["XLE"], "Sector concentration"),
        ("Largest share of ES, any ETF", cfg.decision["es_share_cap"], largest, "Position sizing (booklet 8.6)"),
    ], columns=["Limit", "Maximum", "Portfolio", "Source"]).set_index("Limit"), pct=("Maximum", "Portfolio"), cls="tbl last-left") + caption(
        "Table 1. Every limit against the recommended portfolio. AGG and XLE sit at their caps.")}

    flags, stat, facts = _p("quality_flags.parquet"), _p("stationarity.parquet"), _p("stylised_facts.parquet")
    rows = flags.groupby("rule").agg(points=("date", "size"), first=("date", "min"), last=("date", "max"))
    rows["first"], rows["last"] = rows["first"].astype(str).str[:10], rows["last"].astype(str).str[:10]
    ret = stat[stat.index.str.endswith(" log return")].rename(index=lambda i: i.removesuffix(" log return"))
    pri = stat[stat.index.str.endswith(" log price")].rename(index=lambda i: i.removesuffix(" log price"))
    st_tbl = pd.DataFrame({"ADF p, log price": pri["adf_p"], "ADF p, log return": ret["adf_p"], "KPSS p, log return": ret["kpss_p"]})
    f = facts.loc[[t for t in facts.index if t != "60/40 benchmark"]]
    g["02_data"] = {
        "flags": table(rows.rename(columns={"points": "Points", "first": "First", "last": "Last"})) + caption(
            f"Table 2. {len(flags)} flagged points by rule. All are kept and each was checked against a market event."),
        "facts": table(pd.DataFrame({"Volatility": f["vol_ann"], "Skew": f["skew"], "Excess kurtosis": f["excess_kurtosis"],
                                     "Jarque-Bera p": f["jb_p"], "ARCH-LM p": f["arch_lm_p_lag10"]}).join(st_tbl).loc[list(cfg.universe)],
                       pct=("Volatility",), dec={"Skew": 2, "Excess kurtosis": 1, "Jarque-Bera p": 3, "ARCH-LM p": 3,
                                                 "ADF p, log price": 3, "ADF p, log return": 3, "KPSS p, log return": 2})
        + caption(f"Table 3. Daily log returns, {str(cfg.data.start)[:10]} to the snapshot. KPSS p-values are bounded at 0.10.")}

    t = fr.copy()
    t.index = [f"{x:.0%}" for x in t.index]
    rf = _p("returns_rf.parquet")["rf"]
    g["03_portfolio"] = {
        "frontier_fig": figure(charts.frontier(fr, lm["crisis_budget"], o["required_return"], n["advised_equity"]),
                               "Figure 1. Equity share on each point. Only 35% is above the required return and left of the crisis budget."),
        "frontier": table(pd.DataFrame({"Return": t["forward_return"], "Volatility": t["vol_ttc"], "99% ES": t["es99_ttc"],
                                        "Crisis loss": t["d2_loss"], "Income": t["income_yield"],
                                        "Limits": yes_no(t["within_limits"]), "Objective": yes_no(t["meets_objective"]),
                                        "Caps binding": t["caps_binding"]}),
                          pct=("Return", "Volatility", "99% ES", "Crisis loss", "Income")) + caption(
            "Table 4. The frontier on the decision date, by equity share. Volatility and ES are through the cycle (2004–2018)."),
        "growth": figure(charts.growth_and_drawdown(perf, nav),
                         "Figure 2. Walk-forward history after 5 bp costs: weights rebuilt each quarter from prices known at the time."),
        "kpis": _kpi_block(perf, rf, past["SPY"]) + caption(
            "Table 5. Performance KPIs. 2023–2026 is the period no choice was made on. Beta and alpha are against SPY.")}

    piv = snap[snap["alpha"].isin([0.95, 0.99])].pivot(index="model", columns="alpha", values=["var", "es"])
    order = ["Historical", "Normal", "Student-t", "Cornish-Fisher", "Monte Carlo", "EVT", "GARCH-FHS", "GJR-FHS", "Conditional EVT", "GJR conditional EVT"]
    vt = pd.DataFrame({f"{'VaR' if m == 'var' else 'ES'} {int(a * 100)}%": (piv[(m, a)] * nav).map(kusd)
                       for m in ("var", "es") for a in (0.95, 0.99)}).loc[order]
    losses = -(load_returns("dev+val", cfg)[w.index] @ w).to_numpy()
    ev = evt.threshold_evidence(losses, cfg.evt.threshold_quantiles, cfg.rng(stream=10), B=200)
    ev_rows = []
    for _, x in ev.iterrows():
        fit = evt.fit_gpd(losses[losses > x["u"]] - x["u"])
        ev_rows.append({"Threshold": f"{x['quantile']:.1%}", "Exceedances": int(x["n_u"]), "ξ": x["xi"], "s.e.": x["se_xi"], "AD p": x["ad_p"],
                        "KS p": x["ks_p"], "VaR 99%": evt.evt_var(float(x["u"]), fit, len(losses), int(x["n_u"]), 0.99),
                        "ES 99%": evt.evt_es(float(x["u"]), fit, len(losses), int(x["n_u"]), 0.99)})
    g["04_risk"] = {
        "models": table(vt) + caption(
            f"Table 6. One-day loss in USD thousand on the final weights, each model fitted on {rd['window_start']} to {rd['window_end']}."),
        "models_fig": figure(charts.models(snap, nav), "Figure 3. At 99%, how much further ES reaches beyond VaR, by model."),
        "evt": table(pd.DataFrame(ev_rows).set_index("Threshold"), pct=("VaR 99%", "ES 99%"),
                     dec={"ξ": 3, "s.e.": 3, "AD p": 3, "KS p": 3}) + caption(
            "Table 7. GPD threshold evidence on the final weights, 2004–2022 (no test data). AD and KS are bootstrap goodness-of-fit p-values.")}

    val, crises = _p("backtest_selection_val_500.parquet"), _p("backtest_crises_500.parquet")
    pv = crises.pivot(index="model", columns="crisis", values="exceptions").loc[order][list(cfg.stress["historical"])]
    exp = crises.groupby("crisis")["expected"].first().reindex(pv.columns)
    pv = pv.astype(int).astype(str)
    pv.loc["Expected"] = exp.map("{:.1f}".format)
    champion_bt = _p("final_test_gjr_conditional_evt.parquet")
    champion_bt = champion_bt.loc[champion_bt.index >= mv["test_start"]]
    g["05_validation"] = {
        "validation": table(pd.DataFrame({"Breaches": val["exceptions"], "Kupiec p": val["kupiec_p"], "Ind. p": val["ind_p"], "CC p": val["cc_p"],
                                          "Rolling red": val["rolling_red"], "Z2 zone": val["z2_zone"], "Pinball ×10⁴": val["pinball"] * 1e4,
                                          "Passes": yes_no(val["passes"].astype(bool))}).loc[[m for m in order if m in val.index]],
                            dec={"Kupiec p": 3, "Ind. p": 3, "CC p": 3, "Rolling red": 2, "Pinball ×10⁴": 2}) + caption(
            f"Table 8. Selection on 2019–2022 at 99%, {int(val['T'].iloc[0])} days, about {val['expected'].iloc[0]:.0f} breaches expected."),
        "crises": table(pv) + caption("Table 9. 99% VaR breaches inside each crisis window, 2008 to 2022, on the candidate portfolio."),
        "backtest_fig": figure(charts.backtest(champion_bt, nav), f"Figure 4. {mv['champion']} on the one-shot test, 2023 to 26 October 2026.")}

    sc = _p("final_test_scores.parquet")
    g["05b_challengers"] = {"final": "<h3>One-shot final test, 2023-01-01 to 2026-10-26</h3>" + table(pd.DataFrame({
        "Breaches": sc["exceptions"].astype(int), "Kupiec p": sc["kupiec_p"], "CC p": sc["cc_p"], "Passes": yes_no(sc["passes"].astype(bool)),
        "Pinball vs champion": sc["pinball_vs_champion"].map("{:+.1%}".format)}), dec={"Kupiec p": 3, "CC p": 4}) + caption(
        f"Table 10. All eleven models on {mv['days']} common days, about {mv['expected']:.1f} breaches expected.")}

    windows = {**cfg.stress["historical"], **{f"{k} (pre-registered)": v for k, v in cfg.stress.get("preregistered", {}).items()}}
    alone = sum(w[t] * crisis_loss(pd.Series({t: 1.0}), past, cfg.stress["historical"]) for t in w.index)
    together = crisis_loss(w, past, cfg.stress["historical"])
    dv = pd.DataFrame({"Funds one by one": alone, "Portfolio": together})
    dv["Saved, USD"] = ((alone - together) * nav).map("{:,.0f}".format)
    calm = most_likely_breach(past.cov(), w, lm["crisis_budget"], int(cfg.stress["reverse"]["horizon_days"]))
    crisis = most_likely_breach(stressed_sigma(past, cfg.stress["historical"]), w, lm["crisis_budget"], int(cfg.stress["reverse"]["horizon_days"]))
    moves = pd.DataFrame({"In calm markets": calm.x_star, "In a crisis": crisis.x_star}).loc[w.index].T
    ov = _p("overlay_compare.parquet")
    inn = json.loads((ARTIFACTS / "innovation_summary.json").read_text(encoding="utf-8"))
    rg, cp, mc = inn["regime"], inn["copula"], inn["macro"]
    g["06_stress"] = {
        "crises_fig": figure(charts.crises(cm, lm["crisis_budget"], nav),
                             "Figure 5. Peak-to-trough loss with today's target weights rebalanced daily, the cautious convention."),
        "windows": table(pd.DataFrame({"Start": {k: v[0] for k, v in windows.items()}, "End": {k: v[1] for k, v in windows.items()}})) + caption(
            "Table 11. Replay windows, fixed in config.yaml. The two 2025–26 windows were written down before their results were seen."),
        "diversification": table(dv, pct=("Funds one by one", "Portfolio")) + caption(
            "Table 12. Crisis loss if each fund's loss is added up, against the portfolio's loss: the difference is what diversification saved."),
        "reverse": table(moves.map("{:+.1%}".format)) + caption(
            f"Table 13. Most plausible fund moves that lose {lm['crisis_budget']:.0%} in {cfg.stress['reverse']['horizon_days']} trading days. "
            f"A normal model calls this {rarity_text(calm.years_between, crisis.years_between)}. "
            "Real crises are more frequent, so read the direction, not the odds."),
        "innovation": table(ov[["cagr", "volatility", "max_drawdown", "es99", "calmar", "turnover_ann"]].rename(columns={
            "cagr": "Return", "volatility": "Volatility", "max_drawdown": "Max drawdown", "es99": "99% ES", "calmar": "Calmar", "turnover_ann": "Turnover"}),
            pct=("Return", "Volatility", "Max drawdown", "99% ES"), dec={"Calmar": 2, "Turnover": 2}) + caption(
            "Table 14. Volatility-target overlay on the 35% frontier candidate, data to 2022. Studied, not adopted."),
        "innovation_facts": f"<ul><li><b>Regimes:</b> a two-state model fitted to 2018 finds 99% ES {rg['es99_high_over_calm']:.1f} times higher in the "
                            f"high-volatility state, which lasts about {rg['duration_high_days']:.0f} days against {rg['duration_calm_days']:.0f} for the calm state.</li>"
                            f"<li><b>Dependence:</b> a t-copula (ν = {cp['nu']:.1f}) raises 99% ES by {cp['es_uplift_t_vs_gauss']:.1%} against a Gaussian copula; "
                            f"a joint SPY, EFA and EEM crash has probability {cp['joint_crash_t']:.2%} (Gaussian {cp['joint_crash_gauss']:.2%}, history {cp['joint_crash_history']:.2%}).</li>"
                            f"<li><b>Macro:</b> the stock–bond correlation rose from {mc['stock_bond_corr_2021_end']:.2f} at end-2021 to {mc['stock_bond_corr_2022_end']:.2f} at end-2022; "
                            f"+100 bp on the 10-year yield costs about {abs(mc['rates_plus_100bp']):.1%}.</li></ul>"}

    sh = es_shares(w, past[w.index]).sort_values(ascending=False)
    rob = _p("decision_robustness.parquet")
    rob["cell"] = [f"{v.split()[0]} {m * 1e4:+.0f}" for v, m in zip(rob["verdict"], rob["best_margin"], strict=True)]
    grid = rob.pivot_table(index="erp", columns=["agg_withholding", "agg_spread"], values="cell", aggfunc="first")
    grid.index = [f"ERP {x:.1%}" for x in grid.index]
    grid.columns = [f"{'taxed' if h else 'exempt'}, +{s * 1e4:.0f} bp" for h, s in grid.columns]
    g["07_recommendation"] = {
        "contributions": table(pd.DataFrame({"Weight": w[sh.index], "Share of 99% ES": sh, "ES share ÷ weight": sh / w[sh.index]}),
                               pct=("Weight", "Share of 99% ES"), dec={"ES share ÷ weight": 2}) + caption(
            "Table 15. Euler contributions of each position to 99% ES, 2004 to the decision date. They add up to 100%."),
        "grid": table(grid) + caption(
            "Table 16. Verdict and margin (bp a year) over the assumption grid. Columns: AGG interest tax-exempt or taxed at 15%, and AGG's spread over Treasuries.")}

    g["08_limitations"] = {"table": "".join(
        f"<h3>{html.escape(grp)}</h3>" + table(pd.DataFrame(items, columns=["Assumption", "Why it matters", "Mitigation"]), index=False, cls="tbl text")
        for grp, items in LIMITATIONS.items())}
    g["10_ai_disclosure"] = {"disclosure": disclosure_html()}
    g["09_references"] = {"references": "<ul class='refs'>" + "".join(f"<li>{html.escape(r_)}</li>" for r_ in REFERENCES) + "</ul>"}
    return g


CSS = """
@page { size: A4; margin: 13mm 15mm 15mm;
        @bottom-left { content: "TEAM"; font: 8.5pt 'Source Sans 3', Helvetica, Arial, sans-serif; color: #7a8794; }
        @bottom-right { content: "Page " counter(page) " of " counter(pages); font: 8.5pt 'Source Sans 3', Helvetica, Arial, sans-serif; color: #7a8794; } }
@page :first { @bottom-left { content: ""; } @bottom-right { content: ""; } }
body { font-family: FONT; font-size: 10pt; line-height: 1.34; color: #1d2733; max-width: 780px; margin: 0 auto; }
h1 { font-size: 23pt; line-height: 1.15; margin: 0 0 8px; color: #16304f; }
h2 { font-size: 13.5pt; color: #1f5fae; border-bottom: 1px solid #d6dde5; padding-bottom: 3px; margin: 15px 0 6px; break-after: avoid; }
h3 { font-size: 10.2pt; margin: 11px 0 3px; break-after: avoid; }
p { margin: 0 0 6px; } ul { margin: 2px 0 7px 16px; padding: 0; } li { margin-bottom: 2px; }
p, li, figure { break-inside: avoid; } h2, h3 { break-after: avoid; } p:has(+ .eq) { break-after: avoid; }
.cover { height: 245mm; display: flex; flex-direction: column; justify-content: center; break-after: page; }
.cover .sub { font-size: 12.5pt; color: #5b6573; margin-bottom: 26px; }
.cover .team { background: none; border: 0; padding: 0; font-size: 12.5pt; font-weight: 700; color: #1d2733; }
.cover ol { columns: 2; font-size: 9.6pt; margin: 22px 0 0 16px; padding: 0; color: #5b6573; }
.eq { font-family: "Times New Roman", Times, serif; font-size: 10.6pt; margin: 3px 0 4px 14px; }
.verdict { font-size: 12pt; margin: 2px 0 8px; } .verdict b { color: #0d7a2f; }
.two { display: grid; grid-template-columns: 2fr 3fr; gap: 16px; align-items: start; }
.tbl { border-collapse: collapse; margin: 5px 0 3px; font-size: 8.7pt; width: 100%; break-inside: avoid; font-variant-numeric: tabular-nums; }
.tbl td, .tbl th { padding: 1px 5px; border-bottom: 1px solid #e3e7ec; text-align: right; font-weight: 400; }
.tbl thead th { background: #f3f6f9; font-weight: 600; vertical-align: bottom; }
.tbl tbody th, .tbl td:first-child, .tbl thead th:first-child { text-align: left; }
.tbl.text { font-size: 8.4pt; line-height: 1.28; } .tbl.text td, .tbl.text th { text-align: left; vertical-align: top; } .tbl.text tr { break-inside: avoid; }
.tbl.last-left td:last-child, .tbl.last-left th:last-child { text-align: left; padding-left: 22px; }
code { font-family: Menlo, Consolas, monospace; font-size: 8.8pt; background: #f3f6f9; padding: 0 2px; border-radius: 2px; }
.cap { color: #5b6573; font-size: 8.8pt; margin: 2px 0 9px; }
figure { margin: 7px 0 8px; break-inside: avoid; } figure svg { width: 86%; height: auto; display: block; margin: 0 auto; }
.team { background: #fff4e5; border-left: 3px solid #e0a040; padding: 4px 8px; }
section:nth-last-of-type(2) { break-before: page; }
.refs { font-size: 9pt; columns: 2; column-gap: 18px; } .refs li { list-style: none; margin: 0 0 3px -16px; break-inside: avoid; }
"""


def render(cfg: Config) -> str:
    ensure_narrative()
    g = generated(cfg)
    n = json.loads((ARTIFACTS / "decision_numbers.json").read_text(encoding="utf-8"))
    body = []
    for i, (key, title, _pages, _) in enumerate(SECTIONS, 1):
        blocks = dict(g.get(key, {}))
        text = md_to_html((NARRATIVE / f"{key}.md").read_text(encoding="utf-8"))

        def place(match: re.Match, pending: dict = blocks) -> str:
            return pending.pop(match.group(1), "")

        text = re.sub(r"<p>\{\{(\w+)\}\}</p>", place, text)
        body.append(f"<section><h2>{i}. {title}</h2>{text}{''.join(blocks.values())}</section>")
    contents = "".join(f"<li>{title}</li>" for _, title, _, _ in SECTIONS)
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>QuantEdge Technical Report</title>
{FONT_LINK}
<style>{CSS.replace('"TEAM"', json.dumps(TEAM + " · QuantEdge 1.0", ensure_ascii=False)).replace("FONT", FONT)}</style></head><body>
<div class="cover"><h1>Risk-Aware Portfolio for the Serendib University Endowment Fund</h1>
<div class="sub">QuantEdge 1.0 Final Challenge · technical report and investment memo</div>
<p class="team">{TEAM}</p>
<p>USD {n['nav_usd'] / 1e6:.0f}M · seven ETFs · decision date {n['decision_date']} · market data to {n['data_end']}</p>
<ol>{contents}</ol></div>
{''.join(body)}
</body></html>"""


def main() -> None:
    cfg = load_config()
    out = ROOT / "reports" / "report.html"
    out.write_text(render(cfg), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
