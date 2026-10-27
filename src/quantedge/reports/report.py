"""Technical report builder (Step 17 §3.1).

    python -m quantedge.reports.report   -> reports/report.html (print to PDF from a browser)

Generated content (every table and figure) is rebuilt from data/artifacts on each run. The team's
narrative lives in reports/narrative/NN_*.md: each file is created once with a [TEAM] prompt and is
never overwritten, so re-running the pipeline cannot lose the team's writing.
"""

from __future__ import annotations

import html
import json
import re

import pandas as pd
import plotly.express as px

from quantedge.config import Config, load_config
from quantedge.decision.evidence import build
from quantedge.paths import ARTIFACTS, ROOT
from quantedge.reports.limitations import LIMITATIONS

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
     "Euler contributions, decision checks, the verdict, the proposed amendments and governance."),
    ("08_limitations", "Assumptions and limitations", "1 page", "Introduce the table; add anything specific to your judgement."),
    ("09_ai_disclosure", "AI disclosure and references", "1 page", "Confirm the AI disclosure and list references."),
]


def ensure_narrative() -> None:
    NARRATIVE.mkdir(parents=True, exist_ok=True)
    for key, _title, pages, prompt in SECTIONS:
        f = NARRATIVE / f"{key}.md"
        if not f.exists():
            f.write_text(f"[TEAM: {prompt} Target length: {pages}.]\n", encoding="utf-8")


def md_to_html(text: str) -> str:
    """Minimal Markdown: paragraphs, '- ' bullet lists, **bold**; everything else escaped."""
    out = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = block.splitlines()
        conv = lambda s: re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html.escape(s))  # noqa: E731
        if all(line.lstrip().startswith("- ") for line in lines):
            out.append("<ul>" + "".join(f"<li>{conv(line.lstrip()[2:])}</li>" for line in lines) + "</ul>")
        else:
            cls = " class='team'" if block.lstrip().startswith("[TEAM") else ""
            out.append(f"<p{cls}>{conv(' '.join(lines))}</p>")
    return "\n".join(out)


def table(df: pd.DataFrame, pct: tuple[str, ...] = (), dec: dict[str, int] | None = None, index: bool = True) -> str:
    d = df.copy()
    for c in d.columns:
        if c in pct:
            d[c] = d[c].map(lambda x: f"{x:.2%}" if pd.notna(x) else "")
        elif dec and c in dec:
            d[c] = d[c].map(lambda x, n=dec[c]: f"{x:.{n}f}" if pd.notna(x) else "")
    return d.to_html(index=index, border=0, classes="tbl", escape=True)


def fig(f) -> str:
    return f.update_layout(template="plotly_white", height=320, margin=dict(l=10, r=10, t=40, b=10)).to_html(
        full_html=False, include_plotlyjs=False)


def _p(name: str) -> pd.DataFrame | None:
    path = ARTIFACTS / name
    return pd.read_parquet(path) if path.exists() else None


def generated(cfg: Config) -> dict[str, str]:
    b = build(cfg)
    ev, v = b.evidence, b.verdict
    extras = json.loads((ARTIFACTS / "risk_extras.json").read_text(encoding="utf-8"))
    req = json.loads((ARTIFACTS / "required_return.json").read_text(encoding="utf-8"))
    nav = cfg.nav_usd
    g: dict[str, str] = {}

    g["00_executive_summary"] = (
        f"<p class='verdict'>Rule-engine outcome: <b>{v.status}</b></p><ul>"
        + "".join(f"<li>{html.escape(r)}</li>" for r in v.reasons) + "</ul>"
        + table(pd.DataFrame({"weight": b.weights}).query("weight > 1e-4"), pct=("weight",))
        + table(pd.DataFrame({"value": {
            "Expected return (a year)": f"{ev.expected_return:.2%}", "Required return": f"{ev.required_return:.2%}",
            f"99% 1-day VaR ({b.champion})": f"${b.var99 * nav:,.0f}", "99% 1-day ES": f"${ev.es99_1d * nav:,.0f}",
            "Once-in-10-years daily loss": f"${ev.return_level_10y * nav:,.0f}",
            "Worst crisis (today's weights)": f"{b.worst_hist_loss:.1%} ({b.worst_hist_name})"}}))
    )

    lim = cfg.ips["limits"]
    rows = {k: v for k, v in lim.items() if not isinstance(v, (dict, list))}
    rows |= {f"cap {t}": x for t, x in lim["asset_caps"].items()} | {f"floor {t}": x for t, x in lim["asset_floors"].items()}
    g["01_mandate_ips"] = (
        f"<p>Required return {req['required_return']:.2%} = spending {req['spending_rate']:.1%} + inflation "
        f"{req['inflation']:.2%} (10-year average CPI to {req['cpi_window_end']}) + costs {req['cost_drag']:.1%}.</p>"
        + table(pd.DataFrame({"limit": rows}), pct=("limit",)))
    alt = _p("portfolio_scorecard_val_original_agg40.parquet")
    if alt is not None:
        g["01_mandate_ips"] += ("<p>Sensitivity, original IPS (AGG ≤ 40%): candidates passing the IPS = "
                                f"{int(alt['ips_pass'].sum())} of {len(alt)}.</p>")

    flags = _p("quality_flags.parquet")
    stat = _p("stationarity.parquet")
    facts = _p("stylised_facts.parquet")
    g["02_data"] = (f"<p>{len(flags)} points flagged and kept (none deleted).</p>"
                    + table(flags[["date", "ticker", "rule", "value"]], dec={"value": 4}, index=False)
                    + table(stat[["adf_p", "kpss_p", "verdict"]], dec={"adf_p": 4, "kpss_p": 4})
                    + table(facts[["vol_ann", "skew", "excess_kurtosis", "jb_p", "arch_lm_p_lag10"]],
                            pct=("vol_ann",), dec={"skew": 2, "excess_kurtosis": 2, "jb_p": 3, "arch_lm_p_lag10": 3}))

    card = _p("portfolio_scorecard_val.parquet")
    perf = _p("wf_performance_val.parquet")
    g["03_portfolio"] = (
        table(card[["rank", "ips_pass", "es99_oos", "max_drawdown", "worst_crisis_drawdown", "cagr", "volatility",
                    "calmar", "turnover_ann"]],
              pct=("es99_oos", "max_drawdown", "worst_crisis_drawdown", "cagr", "volatility"),
              dec={"calmar": 2, "turnover_ann": 2})
        + fig(px.line((1 + perf.fillna(0)).cumprod(), title="Walk-forward growth of $1 (out-of-sample, after costs)")))

    snap = _p("risk_snapshot.parquet")
    piv = snap[snap.alpha.isin([0.95, 0.99])].pivot(index="model", columns="alpha", values=["var", "es"])
    piv.columns = [f"{m} {a:.0%}" for m, a in piv.columns]
    sens = _p("evt_sensitivity.parquet")
    h10 = _p("risk_horizon_10d.parquet")
    g["04_risk"] = (table(piv, pct=tuple(piv.columns))
                    + table(sens.drop(columns=["portfolio"]).set_index("rule"),
                            pct=tuple(c for c in sens.columns if c.startswith(("var_", "es_"))),
                            dec={"u": 4, "xi": 3, "xi_se": 3, "beta": 4, "quantile": 3})
                    + (table(h10.set_index(["alpha", "method"]).drop(columns="horizon"), pct=("var", "es"))
                       if h10 is not None else "")
                    + f"<p>Portfolio-loss excess kurtosis {extras['excess_kurtosis']:.2f}; GARCH persistence "
                      f"{extras['garch_persistence']:.3f}.</p>")

    val = _p("backtest_selection_val_500.parquet")
    crises = _p("backtest_crises_500.parquet")
    cols = ["exceptions", "expected", "kupiec_p", "cc_p", "rolling_red", "z2_zone", "pinball", "passes"]
    g["05_validation"] = (f"<p>Champion: <b>{html.escape(b.champion)}</b>: {html.escape(b.champion_reason)}.</p>"
                          + table(val[cols], dec={"expected": 1, "kupiec_p": 3, "cc_p": 3, "rolling_red": 3, "pinball": 7})
                          + table(crises, dec={"expected": 2, "mean_exceedance": 4, "max_exceedance": 4}, index=False))
    for w in (250, 1000):
        alt = _p(f"backtest_selection_val_{w}.parquet")
        if alt is not None:
            g["05_validation"] += f"<p>Window sensitivity, W = {w}: models passing = {', '.join(alt.index[alt.passes]) or 'none'}.</p>"

    arena = _p("ml_arena_val.parquet")
    grid = _p("ml_grid_val.parquet")
    g["05b_challengers"] = (
        (table(arena[["exceptions", "kupiec_p", "cc_p", "pinball", "fz0_vs_champion", "dm_p_holm", "in_mcs", "passes"]]
               .sort_values("pinball"), dec={"kupiec_p": 3, "cc_p": 3, "pinball": 7, "fz0_vs_champion": 4, "dm_p_holm": 3})
         if arena is not None else "<p>ML arena not yet computed.</p>")
        + (table(grid, dec={"pinball": 7, "fz0": 4, "kupiec_p": 3, "cc_p": 3, "rolling_red": 3}, index=False)
           if grid is not None else "")
        + "<p>Final test (2023 onwards): locked until the methodology freeze.</p>")

    matrix = _p("stress_matrix.parquet")
    g["06_stress"] = table(matrix, pct=tuple(matrix.columns))

    contrib = _p("risk_contributions.parquet")
    hist = contrib[contrib.method == "historical ES 99%"][["weight", "pct_contribution", "risk_to_capital"]]
    checks = pd.DataFrame([{"check": c.code, "measure": c.name,
                            "value": c.value if isinstance(c.value, bool) else f"{c.value:.2%}",
                            "limit": c.limit if isinstance(c.limit, bool) else f"{c.limit:.2%}",
                            "result": "pass" if c.passed else "FAIL"} for c in v.checks])
    g["07_recommendation"] = (table(hist, pct=("weight", "pct_contribution"), dec={"risk_to_capital": 2})
                              + table(checks, index=False)
                              + "".join(f"<p>{html.escape(r)}</p>" for r in v.reasons))

    g["08_limitations"] = "".join(
        f"<h4>{grp}</h4>" + table(pd.DataFrame(items, columns=["Assumption", "Why it matters", "Mitigation"]), index=False)
        for grp, items in LIMITATIONS.items())
    disclosure = ROOT / "AI_DISCLOSURE.md"
    g["09_ai_disclosure"] = (f"<pre>{html.escape(disclosure.read_text(encoding='utf-8'))}</pre>"
                             if disclosure.exists() else "")
    return g


def render(cfg: Config) -> str:
    ensure_narrative()
    g = generated(cfg)
    status = json.loads((ARTIFACTS / "status.json").read_text(encoding="utf-8"))
    body = []
    for key, title, pages, _ in SECTIONS:
        narrative = (NARRATIVE / f"{key}.md").read_text(encoding="utf-8")
        body.append(f"<section><h2>{title}</h2><div class='budget'>Page budget: {pages}</div>"
                    f"{md_to_html(narrative)}<div class='gen'>{g.get(key, '')}</div></section>")
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>QuantEdge Technical Report</title>
<script src="https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.35.2/plotly.min.js"></script>
<style>
@page {{ size: A4; margin: 15mm; }}
body {{ font-family: Calibri, Arial, sans-serif; font-size: 10.5pt; color: #1d2733; max-width: 900px; margin: 24px auto; }}
h1 {{ font-size: 18pt; }} h2 {{ font-size: 13pt; color: #23476b; border-bottom: 1px solid #d6dde5; margin-top: 26px; }}
h4 {{ margin: 10px 0 4px; }} .budget {{ color: #7a8794; font-size: 8.5pt; }}
.team {{ background: #fff4e5; border-left: 3px solid #e0a040; padding: 4px 8px; }}
.verdict {{ font-size: 12pt; }} .tbl {{ border-collapse: collapse; margin: 6px 0; font-size: 9pt; }}
.tbl td, .tbl th {{ padding: 2px 6px; border-bottom: 1px solid #e3e7ec; text-align: right; }}
.tbl th {{ background: #f3f6f9; }} pre {{ white-space: pre-wrap; font-size: 9pt; }}
section {{ page-break-inside: auto; }}
</style></head><body>
<h1>QuantEdge 1.0: Risk-Aware Portfolio for the Serendib University Endowment</h1>
<p>Technical report draft · data to {status.get('data_end')} · analysis to {status.get('analysis_end')} ·
results provisional until the methodology freeze. Orange boxes are for the team to write.</p>
{''.join(body)}
</body></html>"""


def main() -> None:
    cfg = load_config()
    out = ROOT / "reports" / "report.html"
    out.write_text(render(cfg), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
