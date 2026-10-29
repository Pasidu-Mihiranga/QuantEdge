"""Build the Q&A decision-defence document from the executed notebooks.

    python scripts/build_defence_pack.py                  # writes reports/decision_defence.html (opens offline)
    python scripts/build_defence_pack.py --artifact PATH  # also writes a body-only copy for publishing as a page

Every chart and table is taken from the notebooks' saved outputs, so the document always shows the numbers the
notebooks produced. Run `make notebooks` first. After the methodology freeze, rerun the notebooks and this script.
"""

from __future__ import annotations

import argparse
import html
import re
from datetime import date
from pathlib import Path

import nbformat

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "notebooks"
OUT = ROOT / "reports" / "decision_defence.html"


def outputs(nb_name: str, marker: str) -> list[tuple[str, str]]:
    """Outputs of the first code cell whose source contains `marker`: ('img', b64) / ('html', table) / ('text', s)."""
    nb = nbformat.read(NB / f"{nb_name}.ipynb", as_version=4)
    for cell in nb.cells:
        if cell.cell_type == "code" and marker in cell.source:
            out = []
            for o in cell.get("outputs", []):
                data = o.get("data", {})
                if "image/png" in data:
                    out.append(("img", data["image/png"].replace("\n", "")))
                elif "text/html" in data and "<table" in data["text/html"]:
                    out.append(("html", data["text/html"]))
                elif o.get("output_type") == "stream" and o.get("name") == "stdout":
                    out.append(("text", o["text"].strip()))
            if not out:
                raise SystemExit(f"{nb_name}: cell '{marker}' has no outputs; run `make notebooks` first")
            return out
    raise SystemExit(f"{nb_name}: no cell contains '{marker}'")


def clean_table(t: str) -> str:
    t = re.sub(r"<style.*?</style>", "", t, flags=re.S)          # drop pandas' own styles; the page styles tables
    t = re.sub(r' (id|class)="[^"]*"', "", t)
    return f'<div class="table-wrap">{t}</div>'


def evidence(nb_name: str, marker: str, caption: str, pick: list[int] | None = None) -> str:
    items = outputs(nb_name, marker)
    if pick is not None:
        items = [items[i] for i in pick]
    parts = []
    for kind, data in items:
        if kind == "img":
            parts.append(f'<img src="data:image/png;base64,{data}" alt="{html.escape(caption)}">')
        elif kind == "html":
            parts.append(clean_table(data))
        else:
            parts.append(f"<pre>{html.escape(data)}</pre>")
    src = f"notebooks/{nb_name}.ipynb"
    return (f'<figure class="evidence"><div class="plate">{"".join(parts)}</div>'
            f"<figcaption>{caption} <span class=\"src\">Source: {src}</span></figcaption></figure>")


def section(sid: str, code: str, title: str, question: str, answer: str, booklet: str, robust: str,
            figures: list[str]) -> str:
    return f"""
<section class="decision" id="{sid}">
  <header class="dhead"><span class="code">{code}</span><h2>{title}</h2></header>
  <div class="qa">
    <p class="q"><span class="label">Judge</span>{question}</p>
    <p class="a"><span class="label">Our answer</span>{answer}</p>
  </div>
  <dl class="meta">
    <div><dt>Booklet</dt><dd>{booklet}</dd></div>
    <div><dt>Robustness</dt><dd>{robust}</dd></div>
  </dl>
  {''.join(figures)}
</section>"""


CSS = """
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Serif:wght@500;600&display=swap">
<style>
/* Layout: one reading column (cards per decision) with a question index; charts sit on light plates in both themes */
:root {
  --bg: #f5f6f8; --surface: #ffffff; --ink: #151a21; --ink-2: #4b5462; --line: #dde1e7;
  --accent: #1f5fae; --accent-soft: #e8eff9; --plate: #fcfcfb; --plate-line: #e4e3df;
  --good: #0d7a2f; --warn: #8a5a00; --crit: #b42318;
  --display: "IBM Plex Serif", Georgia, "Times New Roman", serif;
  --body: "IBM Plex Sans", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, Menlo, Consolas, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #0f1217; --surface: #161b22; --ink: #e7eaef; --ink-2: #a9b2bf; --line: #2b323c;
  --accent: #79aef0; --accent-soft: #1a2738; --plate: #fcfcfb; --plate-line: #3a414b;
  --good: #4cc26f; --warn: #e3a835; --crit: #f07167; color-scheme: dark } }
:root[data-theme="dark"] {
  --bg: #0f1217; --surface: #161b22; --ink: #e7eaef; --ink-2: #a9b2bf; --line: #2b323c;
  --accent: #79aef0; --accent-soft: #1a2738; --plate: #fcfcfb; --plate-line: #3a414b;
  --good: #4cc26f; --warn: #e3a835; --crit: #f07167; color-scheme: dark }
body { background: var(--bg); color: var(--ink); font-family: var(--body); font-size: 15px; line-height: 1.55; }
.wrap { max-width: 1040px; margin: 0 auto; padding-block: 28px 64px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px));
  display: grid; gap: 28px; }
h1, h2, h3 { font-family: var(--display); font-weight: 600; text-wrap: balance; margin: 0; }
h1 { font-size: clamp(1.7rem, 3.4vw, 2.4rem); line-height: 1.15; }
h2 { font-size: 1.3rem; line-height: 1.25; }
h3 { font-size: 1.05rem; }
p { margin: 0; max-width: 70ch; }
.eyebrow { font-family: var(--mono); font-size: .75rem; letter-spacing: .08em; text-transform: uppercase; color: var(--ink-2); }
.top { display: grid; gap: 12px; }
.status { border: 1px solid var(--line); border-left: 4px solid var(--warn); background: var(--surface);
  padding: 12px 14px; border-radius: 6px; color: var(--ink-2); max-width: 78ch; }
.status strong { color: var(--ink); }
.glance { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; }
.tile { background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 14px; display: grid; gap: 4px; min-width: 0; }
.tile .v { font-family: var(--mono); font-size: 1.35rem; font-weight: 500; font-variant-numeric: tabular-nums; }
.tile .k { color: var(--ink-2); font-size: .85rem; }
.index { background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 16px 18px; display: grid; gap: 10px; }
.index ol { margin: 0; padding-left: 1.3rem; display: grid; gap: 6px; }
.index a { color: var(--accent); text-decoration: none; }
.index a:hover, .index a:focus-visible { text-decoration: underline; }
.index .code { font-family: var(--mono); color: var(--ink-2); margin-right: 6px; }
.decision { background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 20px; display: grid; gap: 16px; scroll-margin-top: 16px; min-width: 0; }
.dhead { display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap; }
.code { font-family: var(--mono); font-size: .8rem; font-weight: 500; color: var(--accent); background: var(--accent-soft);
  padding: 2px 8px; border-radius: 4px; letter-spacing: .04em; }
.qa { display: grid; gap: 10px; }
.q, .a { display: grid; gap: 2px; }
.q { color: var(--ink-2); font-style: italic; }
.label { font-family: var(--mono); font-style: normal; font-size: .72rem; letter-spacing: .08em; text-transform: uppercase; color: var(--ink-2); }
.a { font-size: 1.02rem; }
.meta { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 10px; margin: 0; }
.meta div { border-top: 1px solid var(--line); padding-top: 8px; min-width: 0; }
.meta dt { font-family: var(--mono); font-size: .72rem; letter-spacing: .08em; text-transform: uppercase; color: var(--ink-2); }
.meta dd { margin: 2px 0 0; }
figure.evidence { margin: 0; display: grid; gap: 6px; min-width: 0; }
.plate { background: var(--plate); border: 1px solid var(--plate-line); border-radius: 8px; padding: 12px; display: grid; gap: 12px; color: #151a21; min-width: 0; }
.plate img { display: block; max-width: 100%; height: auto; margin: 0 auto; }
figcaption { color: var(--ink-2); font-size: .88rem; }
figcaption .src { font-family: var(--mono); font-size: .75rem; margin-left: 6px; }
.table-wrap { overflow-x: auto; }
.plate table { border-collapse: collapse; font-family: var(--mono); font-size: .8rem; font-variant-numeric: tabular-nums; margin: 0 auto; }
.plate th, .plate td { border-bottom: 1px solid #e4e3df; padding: 4px 9px; text-align: right; white-space: nowrap; }
.plate th { color: #4b5462; font-weight: 500; }
.plate caption { caption-side: top; text-align: left; font-family: var(--body); color: #4b5462; padding-bottom: 4px; }
.plate pre { margin: 0; font-family: var(--mono); font-size: .8rem; white-space: pre-wrap; }
.limits { display: grid; gap: 8px; }
.limits ul { margin: 0; padding-left: 1.2rem; display: grid; gap: 6px; max-width: 78ch; }
footer { color: var(--ink-2); font-size: .85rem; }
a:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
@media (max-width: 480px) { .decision { padding: 14px; } }
</style>
"""


def build() -> str:
    S = []
    S.append(section(
        "verdict", "Verdict", "The verdict by the locked rule (dry run on end-2022 data)",
        "So, do you accept the mandate? And if not, what should the committee do?",
        "On end-2022 market levels the locked rule says <strong>REJECT the mandate as proposed</strong>, and it says it "
        "for one reason only: return. Four portfolios (20–35% equity) pass every risk limit, but the best of them is "
        "expected to earn 4.91% a year against the 5.90% that CPI + 3.5% needs (about USD 98,000 a year short). Taking "
        "more risk does not fix it: even 50% equity earns only 5.07%, so loosening the risk limit cannot reach the "
        "objective, and an ADJUST would not be honest. The verdict flips to ACCEPT if the 10-year real yield is about "
        "1 pp higher at the decision date (TIPS at about 2.6% or more), a threshold fixed in advance and checked once on "
        "26 October. Until then our advice is the 35% portfolio, resized so no ETF carries more than 40% of the tail "
        "risk, which can sustain about 2% spending with real growth.",
        "p. 8 memo options &ldquo;accept the mandate as proposed / adjust the risk limit / reject&rdquo;; p. 4 "
        "responsibility 5 &ldquo;quantify the trade-offs between return-seeking and risk reduction&rdquo;; p. 8 "
        "&ldquo;one clear recommendation&rdquo;.",
        "REJECT in all 18 combinations of the equity premium (3.5–5.5%), AGG spread (0.3–0.9%) and AGG tax; an ERP "
        "of 7.75% would be needed to flip it. Ten-year odds of a 3.5% real return at 35% equity: about 34%. The app's "
        "rule engine gives the same verdict. The real verdict is computed once, after the freeze, with decision-date "
        "yields.",
        [evidence("06_decision", "meets = sc[\"meets required return\"]", "The verdict on one chart: no point reaches "
                  "the required return inside the budget or the +5 pp zone.", [1, 0]),
         evidence("06_decision", "def verdict_with", "Robustness: the verdict over every combination of our assumptions."),
         evidence("06_decision", "def dollars(w)", "The advised portfolio and two alternatives in dollars, and the "
                  "D8 resizing (EFA's tail-risk share cut from 47% to 40%).", [0, 1, 2]),
         evidence("06_decision", "def rule(spending, limits)", "Model validity, the verdict under each IPS version, "
                  "and the rupee view.", [0, 1, 2])]))
    S.append(section(
        "objective", "D1 · D10", "Return objective: CPI + 3.5% a year (3% spending + 0.5% real growth)",
        "Why do you spend 3% when most endowments spend 4–5%? And why should we accept your portfolio at all?",
        "The booklet asks the endowment to preserve <em>and grow</em> its capital, and leaves the return objective to us. "
        "A conservative portfolio of these seven ETFs can sustain about 3% spending plus 0.5% real growth only if real "
        "bond yields are about 1 pp above their end-2022 level; at end-2022 levels it sustains about 2%. A peer-level 4% "
        "would need far more equity risk than this committee accepts. So we set CPI + 3.5% and the verdict is "
        "<strong>ACCEPT</strong> if a portfolio meets it inside every risk limit at the decision date; "
        "<strong>ADJUST THE RISK LIMIT</strong> if one would with the crisis budget at most 5 pp looser; otherwise "
        "<strong>REJECT</strong>, with the spending rate the limits can sustain given as advice.",
        "p. 3 &ldquo;preserve and grow its capital &hellip; sustainable real growth&rdquo;; p. 4 responsibility 2 "
        "&ldquo;determine an appropriate return objective&rdquo;; p. 8 memo options.",
        "At 3% spending the 10-year chance of losing a fifth of real value is about 26% (about 40% at 4%), even in the "
        "low-yield case. The verdict turns on the decision-date real yield (table below), computed once after the freeze.",
        [evidence("06_decision", "def best_feasible", "Sustainable spending by crisis budget and ERP, end-2022 levels; "
                  "reference portfolios outside the IPS.", [0, 1, 2]),
         evidence("06_decision", "for dy in [0.0, 0.005", "Real-yield scenario: sustainable spending and verdict for 3% "
                  "spending as the 10-year real yield rises above its end-2022 level."),
         evidence("06_decision", "def simulate(x, s", "10-year simulation: chance that real value ends below 80%, and "
                  "the median real value, by equity share and spending rate.")]))
    S.append(section(
        "d2", "D2", "Crisis budget: the portfolio may lose at most 25% in a crisis",
        "Why 25%? Isn't that a lot for a conservative endowment?",
        "It is the largest loss in a GFC-type crisis that still lets the fund grow in real terms. A 20% budget allows only "
        "about 24% equity and cannot fund any real growth; above 25% the extra equity buys almost nothing after costs. "
        "Each 10 points of equity bought about 0.35 pp a year of return and cost about 3.3 pp more at the bottom of a "
        "crisis (about USD 35,000 a year for USD 330,000 more at the trough). A 35/65 mix is conservative by industry "
        "standards.",
        "p. 3 &ldquo;avoiding large losses is more important&rdquo; and &ldquo;balance capital preservation, income "
        "generation, and sustainable real growth&rdquo;; p. 4 responsibility 3.",
        "The volatility (8.4%) and 99% ES (2.23%) limits are calibrated from this one budget, so they no longer "
        "contradict each other. 20% is shown as a sensitivity.",
        [evidence("02_portfolio_frontier", "What extra equity bought", "Return against worst crisis loss, 2008–2022 "
                  "walk-forward (historical, not a forecast)."),
         evidence("03_var_es_evt", "dev = R.loc[:\"2018-12-31\"]", "Limits calibrated from the crisis budget "
                  "(development data including the GFC).")]))
    S.append(section(
        "ips", "IPS v1 → v2", "Why the risk limits changed, and what that does to the verdict",
        "Your limits changed after you looked at the data. Isn't that moving the goalposts until your portfolio passes?",
        "No. The old limits contradicted each other: on the same frontier, the 8% volatility limit allowed about 34% "
        "equity, the 20% crisis limit 24% and the 1.5% ES limit only 21%. Three limits, three answers. The reason is "
        "simple: a bad-day loss (99% ES) is about four times daily volatility, so 8% volatility already implies about "
        "2.1% ES. The new limits come from <em>one</em> client preference, the 25% crisis budget, so they all agree "
        "(36% equity, volatility 8.4%, ES 2.23%). The causality runs one way: the committee's preference sets the "
        "limit, and the limit sets the portfolio. Under the new limits the 35% portfolio passes every risk check. "
        "What now decides the verdict is <strong>return</strong>: at end-2022 yields the portfolio is about 1 pp short of "
        "CPI + 3.5%, so the end-2022 dry run says ADJUST. The real verdict uses the decision-date yields and is computed "
        "once, after the freeze.",
        "p. 4 responsibility 3 &ldquo;define and justify the risk constraints&rdquo;; p. 3 &ldquo;avoiding large losses "
        "is more important than maximizing gains&rdquo;; p. 8 &ldquo;adjust the risk limit&rdquo; memo option.",
        "Agreed and locked on 2026-10-28, before the 2023–2026 test, using data up to 2022 only. The app's production "
        "code was written separately and reproduces every calibration number and forward return in the notebook "
        "within 0.01 bp (<code>tests/test_objective.py</code>). The old limits stay in the app as a sensitivity "
        "case, so the change log is visible.",
        [evidence("06_decision", "V1 = {\"vol\"", "Where each limit cuts the frontier: the old limits give three "
                  "different answers, the new ones one.", [1, 0]),
         evidence("06_decision", "p35 = fr.loc[0.35]", "The recommended 35% portfolio under the old and the new "
                  "limits, and the return gap at end-2022 levels.", [2, 0, 1]),
         evidence("06_decision", "Production check", "Two separately written codes, one answer: the notebook against "
                  "the app's pipeline.")]))
    S.append(section(
        "d3", "D3", "Caps: AGG at most 65%, each sector or EM fund at most 10%, gold at most 15%, equity at most 50%",
        "Why let one bond fund hold 65% of the endowment?",
        "AGG holds thousands of bonds, so the cap guards against interest-rate concentration, not issuer risk. Moving it "
        "between 60% and 70% changes the mix but not the risk (volatility stays at 9.8% at 30% equity). From 35% equity "
        "no cap binds, so the recommendation is driven by risk, not by a number we typed.",
        "p. 4 &ldquo;a single fund or any combination of eligible funds&rdquo;; p. 4 &ldquo;diversification "
        "benefits&rdquo;.",
        "Cap sensitivity ±5 pp shown below; the IPS change log records every earlier cap change.",
        [evidence("02_portfolio_frontier", "Minimum-variance mix at each equity share", "Minimum-variance mix at each "
                  "equity share and the caps that bind."),
         evidence("02_portfolio_frontier", "Cap sensitivity at 30% equity", "Moving a cap by 5 pp changes the mix, "
                  "not the risk.")]))
    S.append(section(
        "d4", "D4", "Equity risk premium 4.5% and AGG spread 0.5%, stated as assumptions",
        "Where does your 4.5% equity premium come from? Isn't that a data source outside the approved list?",
        "It is a disclosed assumption, not data. It is anchored on approved Yahoo and FRED data and only cross-checked "
        "against published estimates (roughly 4.2–5.5% in 2025–26). More importantly, the verdict does not depend on "
        "it: at end-2022 levels even an ERP of 7.75% would be needed for 3% spending, and in the real-yield scenario the "
        "verdict is the same across 3.5–5.5%.",
        "p. 9 &ldquo;using an undisclosed or proprietary data source is a rubric violation&rdquo;.",
        "Break-even ERP far outside the plausible range; the same with a lower AGG spread and with AGG taxed.",
        [evidence("06_decision", "spy_x = float", "Evidence from approved data: realised premia 2004–2022 and "
                  "end-2022 market levels."),
         evidence("06_decision", "def breakeven_erp", "Break-even equity premium for each spending rate (25% budget).")]))
    S.append(section(
        "d5", "D5", "Our hypothetical scenario: \u201cHormuz stagflation 2027\u201d",
        "Why this scenario? Why not a tech crash, a 2008-style crash or a rupee crisis?",
        "Because it is the one crisis in which this portfolio's protection fails: bonds fall with stocks, as in 2022, "
        "and diversification saves almost nothing. Over about three quarters, oil rises 40%, the 10-year yield rises "
        "250 bp (2022-size), the VIX rises 25 points, the dollar 8% and credit spreads 150 bp, with one panic day on "
        "AGG. It is the most severe version that is still within history: more extreme than 2022 or the GFC, less than "
        "COVID. The 35% portfolio loses 21.2%; including the scholarships paid during the crisis, the endowment falls to "
        "about USD 7.65M (−23.5%), inside the 25% budget. We compared it with four alternatives; only this one meets "
        "all six criteria.",
        "p. 8 &ldquo;one hypothetical scenario the team designs itself&rdquo;; p. 9 FRED series for stress-scenario "
        "construction; standard: &ldquo;severe but plausible&rdquo; (BIS) and calibration to past recessions (US "
        "Federal Reserve).",
        "Sizes calibrated on data up to 2022 only; the story uses October 2026 news (flagged). The factor mapping "
        "reproduces 2022 (17.8% predicted vs 18.8% actual). A version beyond anything on record would cost 25.5%.",
        [evidence("05_stress_regimes", "alternatives = pd.DataFrame", "Why this scenario: five candidates against six "
                  "criteria."),
         evidence("05_stress_regimes", "hist_chg = ", "How severe each candidate is against every three-quarter "
                  "period on record."),
         evidence("06_decision", "worst = {h:", "Why a three-quarter episode: how fast past crises hit today's 35% "
                  "portfolio."),
         evidence("05_stress_regimes", "etf_ret = pd.Series", "The endowment view: value at the trough including "
                  "spending, and which holding to sell.")]))
    S.append(section(
        "d8", "D8", "Risk budget: no ETF may carry more than 40% of the portfolio's tail risk",
        "How did you size the positions?",
        "With each position's contribution to Expected Shortfall. In the 35% portfolio, EFA is 19% of the money but "
        "47% of the worst-day risk, so we cap it and move the difference to SPY. International equity also cost return "
        "over 2008–2022, so there are two independent reasons for the change.",
        "p. 8 &ldquo;risk budgeting and position sizing, using each position's marginal VaR/ES contribution&rdquo;.",
        "The contributions add up exactly to total ES (Euler check). The cap binds at 30–35% equity, where the "
        "recommendation sits.",
        [evidence("03_var_es_evt", "Where the money is vs where the risk is", "Share of capital against share of 99% "
                  "ES (35% equity)."),
         evidence("06_decision", "largest share", "Largest tail-risk share at every equity level.")]))
    S.append(section(
        "d9", "D9", "Monitoring: an alert that convenes the committee, no automatic trading",
        "Will you cut risk automatically when markets get dangerous?",
        "We tested that rule and it failed. It looked good on 2008–2018, but on 2019–2022 every version deepened the "
        "worst loss and cut the return: COVID was over before it fired, and the fund then missed the rebound. So the "
        "risk forecast raises an alert (5 days above the limit) and the committee decides.",
        "p. 10 innovation examples &ldquo;regime-conditioned risk, optional risk overlays&rdquo;.",
        "Designed on one period, confirmed on another; reported as a negative result.",
        [evidence("06_decision", "design = pd.DataFrame", "Trigger backtest: design period 2008–2018 and the "
                  "out-of-sample check 2019–2022."),
         evidence("06_decision", "N_PICK = 10", "Holding the 35% portfolio against the same portfolio with the "
                  "trigger.")]))
    S.append(section(
        "risk", "Risk", "How bad can a bad day get, and how sure are we?",
        "What can you lose, in dollars?",
        "For the 35% portfolio on USD 10M: about USD 125,000–135,000 on a 1-in-100 day (three methods agree within 5%), "
        "about USD 175,000 on average on those days, and USD 430,000–520,000 on a once-in-a-decade day. We give a "
        "range for the rarest case on purpose: that is where any model is least certain.",
        "p. 5 &ldquo;how bad losses could become; how confident you are&rdquo;; Layers 2–4.",
        "The normal model under-states rare losses (83 exceptions against 38 expected over 2008–2022 with today's "
        "weights); the champion model is volatility-adjusted.",
        [evidence("03_var_es_evt", "methods = {", "99% VaR in dollars by method (35% equity).", [1]),
         evidence("03_var_es_evt", "roll_hs = loss_all", "Rolling 99% VaR against daily losses, today's weights.")]))
    S.append(section(
        "backtest", "H4", "Does the risk model work out of sample?",
        "How do you know your VaR is right?",
        "We tested six models on the portfolio we recommend, using 2019–2022 data they never saw. The four "
        "volatility-adjusted models pass Kupiec, Christoffersen and the traffic light; historical VaR gets the count "
        "right but its breaches bunch together, and the normal model fails. The pre-registered rule picks "
        "<strong>GJR conditional EVT</strong> (14 breaches against 10 expected), statistically tied with the runner-up. "
        "Every model fails in a COVID-speed crash, which is why we also hold a crisis budget and stress tests. All 14 "
        "breaches have a verified market cause; 8 were no larger than the model's own ES forecast, and the other 6 "
        "are sudden calm-to-crisis switches.",
        "p. 7 Layer 5 &ldquo;Kupiec, Christoffersen, Basel traffic light&rdquo;; Layer 4 &ldquo;how different "
        "modelling approaches perform under stressed market conditions&rdquo;.",
        "Chosen on four years, where Kupiec has 79% power (24% over one year). The same champion wins with 250- and "
        "1000-day windows. The app's code reproduces this independently written backtest exactly (same breaches, "
        "same loss), so the 2023–2026 test, run once after the freeze, is run by the production code and checked "
        "by the notebook.",
        [evidence("04_backtesting", "assert basel_zone(4, 250)", "Validation 2019–2022: the six models against "
                  "every test."),
         evidence("04_backtesting", "champ = json.loads", "Two separately written codes, one answer: the notebook "
                  "against the app's pipeline on 2019–2022.", [1]),
         evidence("04_backtesting", "exceptions ÷ expected", "Breaches in each crisis window (1 = as many as "
                  "expected).", [1]),
         evidence("04_backtesting", "log = d[d[", "The champion's 99% VaR and every breach on validation, each with "
                  "its verified cause."),
         evidence("04_backtesting", "Breach anatomy", "Every breach explained: who lost, what moved, the loss against "
                  "the model's own ES forecast, and the statistical checks.")]))
    S.append(section(
        "stress", "D2 · D5", "What happens in a crisis?",
        "What would a 2008 or a 2022 do to the endowment?",
        "With today's 35% portfolio: a GFC repeat costs about USD 2.4M at the worst point (24.4%) and about 7 months "
        "to recover; COVID about 15%; 2022 about USD 1.9M (18.8%), half of it from bonds. Our scenario, Hormuz stagflation "
        "2027, costs 21.2% with a liquidity day; only a version beyond anything on record breaks the 25% budget. The most likely route to a breach is a GFC-type deflationary crash, about a 1% chance per stress "
        "episode.",
        "p. 8 &ldquo;historical crisis return paths &hellip; plus one hypothetical scenario&rdquo;; p. 4 "
        "&ldquo;practical stress testing&rdquo; and &ldquo;resilience during market crises&rdquo;.",
        "The factor mapping reproduces 2022 (17.8% predicted vs 18.8% actual). Less equity does not protect against "
        "a rate shock.",
        [evidence("05_stress_regimes", "def replay(wx, a, b)", "Each required crisis with today's weights, and "
                  "the budget line.", [1, 0]),
         evidence("05_stress_regimes", "SHOCK = pd.Series", "Hormuz stagflation 2027: results by equity share, the severity ladder "
                  "and where the loss comes from.", [1, 2, 0]),
         evidence("05_stress_regimes", "Sigma_f = data", "Reverse stress: the most plausible shock that would "
                  "cost 25%."),
         evidence("05_stress_regimes", "crisis_map = pd.DataFrame", "The crisis map: four kinds of crisis against "
                  "one budget.")]))
    S.append(section(
        "diversification", "G27", "Does diversification help?",
        "Your seven-ETF mix did not beat a simple SPY/AGG mix. Why diversify?",
        "Because the benefit is in risk, not return. Diversification removes about a quarter of the worst-day risk "
        "(about USD 77,000 on a bad day) and avoided 5.4 points of loss in the GFC. It has a known weak spot: in the "
        "2022 rate shock it saved only 0.6 points, because stocks and bonds fell together.",
        "p. 4 &ldquo;diversification benefits&rdquo;.",
        "The saving shrinks from 32% of tail risk on calm days to 23% on crisis days; we show both.",
        [evidence("03_var_es_evt", "CRISIS_DAYS", "Portfolio ES against the sum of each asset's ES, by equity share."),
         evidence("03_var_es_evt", "Crisis drawdowns", "Loss avoided by diversification in each crisis.")]))
    S.append(section(
        "hedge", "H1", "When does the bond hedge fail?",
        "Isn't AGG a safe haven?",
        "In crashes and normal times, yes. In rate-hiking cycles, no: there the stock–bond correlation is about +0.3 "
        "instead of −0.2 (Newey-West p &lt; 0.001; the same sign out of sample 1990–2004, but not significant). Our "
        "original idea, that high inflation alone breaks the hedge, was tested and not supported.",
        "p. 4 optional macro and market risks; p. 10 &ldquo;regime-conditioned risk&rdquo;.",
        "Evidence graded moderate: strong in-sample, directional out of sample, definition fixed before use.",
        [evidence("01_eda_detective", "roll = lr[\"SPY\"].rolling(252)", "SPY–AGG 1-year correlation, rate-hiking "
                  "cycles shaded."),
         evidence("01_eda_detective", "def horse_race", "Regression with all regimes competing (HAC standard "
                  "errors).")]))
    S.append(section(
        "model", "H3", "Is the risk model right?",
        "How do you know your volatility model works?",
        "We test its leftovers. After dividing returns by the GARCH volatility forecast, what remains should be random. "
        "The plain GARCH(1,1) used by the current champion leaves volatility clustering (p ≈ 0.007); GJR-GARCH, where "
        "losses raise volatility more than gains, passes (p ≈ 0.16) and fits better. GJR is compared with the champion "
        "on validation data before the freeze.",
        "Layer 4 &ldquo;evaluate how different modelling approaches perform&rdquo;; Layer 5 backtesting.",
        "Model choice is made on 2019–2022 validation data only; 2023–2026 is tested once after the freeze.",
        [evidence("03_var_es_evt", "arch_model(y_ret", "Residual tests for GARCH and GJR-GARCH, and the residual "
                  "distribution.")]))

    index = "".join(f'<li><a href="#{sid}"><span class="code-i">{code}</span> {q}</a></li>'
                    for sid, code, q in [
                        ("verdict", "Verdict", "Do you accept the mandate? If not, what should we do?"),
                        ("objective", "D1 · D10", "Why 3% spending, and will you accept the mandate?"),
                        ("d2", "D2", "Why a 25% crisis budget?"),
                        ("ips", "IPS v1 → v2", "Why did your risk limits change? Isn't that moving the goalposts?"),
                        ("d3", "D3", "Why can AGG be 65%?"),
                        ("d4", "D4", "Where does the 4.5% equity premium come from?"),
                        ("d5", "D5", "Why this hypothetical scenario, and not another?"), ("d8", "D8", "How did you size positions?"),
                        ("d9", "D9", "Will you cut risk automatically?"), ("risk", "Risk", "What can you lose, in dollars?"),
                        ("backtest", "H4", "Does your risk model work out of sample?"),
                        ("stress", "D2 · D5", "What would a 2008 or a 2022 do to the endowment?"),
                        ("diversification", "G27", "Why diversify if it didn't add return?"),
                        ("hedge", "H1", "When does the bond hedge fail?"), ("model", "H3", "Is the risk model right?")])
    return f"""<title>Serendib Decision Defence</title>
{CSS}
<main class="wrap">
  <div class="top">
    <span class="eyebrow">QuantEdge 1.0 · Serendib University Endowment Fund · USD 10M</span>
    <h1>Serendib Decision Defence</h1>
    <p>Every decision the team made, the question a judge is likely to ask about it, our answer in plain English, and the
    chart or table that backs it. Built from the analysis notebooks on {date.today():%d %B %Y}.</p>
    <p class="status"><strong>Dry run.</strong> These figures use data up to 2022-12-31. The 2023–2026 test period stays
    locked until the methodology freeze on 30 October 2026; after it, the notebooks and this document are regenerated
    with decision-date market levels, and the final verdict is computed once.</p>
  </div>
  <div class="glance">
    <div class="tile"><span class="v">REJECT · dry run</span><span class="k">risk passes; return 1 pp short at end-2022 yields</span></div>
    <div class="tile"><span class="v">CPI + 3.5%</span><span class="k">return objective (3% spending + 0.5% growth)</span></div>
    <div class="tile"><span class="v">25%</span><span class="k">largest crisis loss accepted</span></div>
    <div class="tile"><span class="v">≈ 35%</span><span class="k">equity at the 25% budget</span></div>
    <div class="tile"><span class="v">8.4% · 2.23%</span><span class="k">volatility and 99% ES limits, both set by the budget</span></div>
    <div class="tile"><span class="v">$125–135k</span><span class="k">1-in-100-day loss (35% equity)</span></div>
    <div class="tile"><span class="v">$430–520k</span><span class="k">once-in-a-decade day</span></div>
  </div>
  <nav class="index" aria-label="Questions">
    <h3>Likely questions</h3>
    <ol>{index}</ol>
  </nav>
  {''.join(S)}
  <section class="decision limits" id="limits">
    <header class="dhead"><span class="code">Limits</span><h2>What this analysis does not claim</h2></header>
    <ul>
      <li>Expected returns are forward-looking estimates built from yields and an assumed equity premium; the realised
      2008–2022 returns are shown as history, not as a forecast.</li>
      <li>The sample starts in November 2004 (GLD's launch), so the 2000–2002 technology crash is not in the data.</li>
      <li>In crises AGG can trade well below the value of its bonds (−6.8% on 10 October 2008 when yields implied
      about −0.3%); a forced seller gets the ETF price.</li>
      <li>US withholding tax applies to dividends (15% under the treaty); whether AGG's interest dividends are exempt
      needs a tax adviser.</li>
      <li>Model choices were made on 2019–2022 validation data, so their p-values are optimistic; only the one-shot
      2023–2026 test is clean.</li>
    </ul>
  </section>
  <footer>Source of every chart and table: the notebooks in <code>notebooks/</code>; decisions and their evidence:
  <code>doc/decisions/inputs_lock.md</code>; booklet coverage: <code>doc/brief_traceability.md</code>. Regenerate with
  <code>python scripts/build_defence_pack.py</code>.</footer>
</main>""".replace('class="code-i"', 'class="code"')


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--artifact", type=Path, help="also write a body-only copy for publishing as a page")
    args = ap.parse_args()
    body = build()
    full = ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
            f"{body.split('<main', 1)[0]}</head>\n<body>\n<main{body.split('<main', 1)[1]}\n</body>\n</html>\n")
    OUT.write_text(full, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1e6:.1f} MB)")
    if args.artifact:
        args.artifact.write_text(body, encoding="utf-8")
        print(f"wrote {args.artifact}")


if __name__ == "__main__":
    main()
