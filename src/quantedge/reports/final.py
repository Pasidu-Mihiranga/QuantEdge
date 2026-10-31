"""The committee memo and the one-page tear sheet, written from `decision_numbers.json` only.

Both documents read the same file as the app, so they cannot disagree with it. The memo is a draft: the team reviews
it, rewrites it in its own words and owns the recommendation (brief §8.7).
"""

from __future__ import annotations

import html
import re

TEAM = "Team Gmora"
# Source Sans 3: a text face with tabular figures, kept in reports/fonts so the documents build the same offline.
FONT_LINK = '<link rel="stylesheet" href="fonts/source-sans.css">'
FONT = "'Source Sans 3', Helvetica, Arial, sans-serif"

GOVERNANCE = [
    "Rebalance to the target weights every quarter.",
    "If the daily risk forecast stays above the limit for 5 days, the committee meets; nothing is sold automatically.",
    "Review the spending rate, the limits and the return assumptions every year.",
]


def money(x: float) -> str:
    a = abs(x)
    body = f"${a / 1e6:.2f}M" if a >= 999_500 else f"${round(a, -2):,.0f}"
    return ("−" if x < 0 else "") + body


def headline(n: dict) -> str:
    """The decision in one sentence."""
    o, eq = n["objective"], n["advised_equity"]
    key = n["verdict"].split()[0]
    if key == "ACCEPT":
        return (f"We recommend that the committee **accepts the mandate as proposed**: invest {eq:.0%} in equities and "
                f"{1 - eq:.0%} in bonds. The portfolio is expected to earn {n['expected_return']:.2%} a year after costs, "
                f"against the {o['required_return']:.2%} needed for US inflation + 3.5%, and it stays inside every risk limit.")
    if key == "ADJUST":
        return (f"We recommend that the committee **adjusts the risk limit**: no portfolio meets the "
                f"{o['required_return']:.2%} objective inside the current limits, but one does with the crisis budget "
                "loosened by at most 5 points. The amended limit needs the committee's approval.")
    return (f"We recommend that the committee **rejects the mandate as proposed**: no portfolio inside the risk limits is "
            f"expected to earn the {o['required_return']:.2%} the objective needs. The limits can fund about "
            f"{n['sustainable_spending']:.1%} spending.")


def weight_rows(n: dict) -> list[tuple[str, float, float]]:
    nav = n["nav_usd"]
    return [(t, w, w * nav) for t, w in sorted(n["weights"].items(), key=lambda kv: -kv[1]) if w > 1e-4]


def memo(n: dict) -> str:
    """One page of plain English for the board (brief §8.6). Markdown."""
    nav, r, lim, rd, mv = n["nav_usd"], n["risk"], n["limits"], n["risk_day"], n["model_validity"]
    rob, t, ym = n["robustness"], n["ten_year"], n["yield_margin"]
    cm = n["crisis_map"]
    worst_name = max(cm, key=cm.get)
    rows = "\n".join(f"| {tk} | {w:.1%} | {money(v)} |" for tk, w, v in weight_rows(n))
    alt_lo, alt_hi = n["alternatives"]["lower_risk"], n["alternatives"]["higher_return"]
    gov = "\n".join(f"- {g}" for g in GOVERNANCE)
    return f"""# Investment committee memo: Serendib University Endowment Fund

*{TEAM} · USD {nav / 1e6:.0f}M · decision date {n['decision_date']} · market data to {n['data_end']}*

## Recommendation
{headline(n)}

| Fund | Weight | Amount |
|---|---|---|
{rows}

## Why this portfolio
- **It is the safest mix that does the job.** With {alt_lo['equity_share']:.0%} in equities the fund would fall {money(alt_lo['shortfall_usd'])} a year short of its objective; with {alt_hi['equity_share']:.0%} a repeat of 2008 would cost {money(alt_hi['worst_crisis_usd'])}, more than the {money(lim['crisis_budget'] * nav)} budget.
- **Income pays the scholarships.** Dividends and interest of about {money(r['income_yield'] * nav)} a year cover the 3% spending rate.

## What can go wrong
- **A repeat of the worst crisis on record ({worst_name}):** a loss of about {money(r['worst_crisis_loss'] * nav)}, or {r['worst_crisis_loss']:.1%}.
- **Our stagflation scenario, where stocks and bonds fall together:** about {money(n['scenario']['loss'] * nav)}, or {n['scenario']['loss']:.1%}.
- **A very bad day (the worst 1 in 100):** about {money(r['es99_ttc'] * nav)} on average over a full market cycle; about {money(rd['es99'] * nav)} in today's calmer markets.

## How sure we are
- **The risk model passed a fair test.** On {mv['days']} days it had never seen ({mv['test_start'][:4]}–{mv['test_end'][:4]}), it was beaten on {mv['exceptions']} days against about {mv['expected']:.0f} expected.
- **The return objective is a close call.** The margin is {money(n['return_margin_usd'])} a year. {ym['direction']} {ym['pp'] * 100:.2f} points, and ACCEPT needs an equity premium of at least {n['erp_breakeven']:.2%} (we assume 4.5%). Across {sum(rob.values())} combinations of our return assumptions it holds in {rob.get('ACCEPT', 0)}. Over ten years the chance of meeting the objective is about even ({t['p_objective']:.0%}).

## What we ask the committee to do
- **Approve the portfolio above**, and record that the return objective is a target, not a promise.
- **Obtain tax advice before investing.** If US tax applies to the bond fund's interest, the objective is no longer met.
{gov}
"""


def memo_page(n: dict) -> str:
    """The memo as one A4 page of HTML, from the same Markdown."""
    inline = lambda t: re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html.escape(t))  # noqa: E731
    out: list[str] = []
    for block in memo(n).strip().split("\n\n"):
        for chunk in re.split(r"\n(?=## )", block):
            head, _, rest = chunk.partition("\n")
            if head.startswith("# "):
                out.append(f"<h1>{inline(head[2:])}</h1>")
            elif head.startswith("## "):
                out.append(f"<h2>{inline(head[3:])}</h2>")
                chunk = rest
            lines = [x for x in chunk.splitlines() if not x.startswith("# ")]
            if not lines:
                continue
            if lines[0].startswith("|"):
                rows = [[c.strip() for c in x.strip("|").split("|")] for x in lines if not x.startswith("|--")]
                body = "".join("<tr>" + "".join(f"<t{'h' if i == 0 else 'd'}>{c}</t{'h' if i == 0 else 'd'}>" for c in r) + "</tr>"
                               for i, r in enumerate(rows))
                out.append(f"<table>{body}</table>")
            elif lines[0].startswith("- "):
                out.append("<ul>" + "".join(f"<li>{inline(x[2:])}</li>" for x in lines) + "</ul>")
            elif lines[0].startswith("*"):
                out.append(f"<p class='sub'>{inline(lines[0].strip('*'))}</p>")
            else:
                out.append(f"<p>{inline(' '.join(lines))}</p>")
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Investment Committee Memo</title>
{FONT_LINK}
<style>
@page {{ size: A4; margin: 15mm 17mm; }}
body {{ font-family: {FONT}; font-size: 11.4pt; color: #1d2733; line-height: 1.42; margin: 0; }}
h1 {{ font-size: 21pt; line-height: 1.2; font-weight: 700; margin: 0 0 5px; color: #16304f; }}
h2 {{ font-size: 13pt; font-weight: 600; color: #1f5fae; margin: 15px 0 4px; }}
.sub {{ color: #5b6573; font-size: 10pt; }} p {{ margin: 0 0 5px; }} b {{ font-weight: 600; }}
ul {{ margin: 3px 0 4px 16px; padding: 0; }} li {{ margin-bottom: 3px; }}
table {{ border-collapse: collapse; margin: 5px 0; font-size: 10.8pt; font-variant-numeric: tabular-nums; }}
td, th {{ padding: 2px 20px 2px 0; border-bottom: 1px solid #e3e7ec; text-align: left; font-weight: 400; }} th {{ font-weight: 600; }}
</style></head><body>{''.join(out)}</body></html>"""


def tear_sheet(n: dict) -> str:
    """One A4 page of HTML for the executive reader."""
    nav, o, r, lim, mv = n["nav_usd"], n["objective"], n["risk"], n["limits"], n["model_validity"]
    colour = {"ACCEPT": "#0d7a2f", "ADJUST": "#a15c00", "REJECT": "#b42318"}[n["verdict"].split()[0]]
    bars = "".join(f"<tr><td>{tk}</td><td class='bar'><span style='width:{w * 100:.1f}%'></span></td>"
                   f"<td class='num'>{w:.1%}</td><td class='num'>{money(v)}</td></tr>" for tk, w, v in weight_rows(n))
    crises = "".join(f"<tr><td>{html.escape(k.replace(' (pre-registered)', '').replace(' (scenario)', ' (our scenario)'))}</td>"
                     f"<td class='num'>−{v:.1%}</td><td class='num'>{money(-v * nav)}</td></tr>"
                     for k, v in sorted(n["crisis_map"].items(), key=lambda kv: -kv[1]))
    lead = html.escape(headline(n)).replace("**", "")
    rob = n["robustness"]
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Serendib Endowment Tear Sheet</title>
{FONT_LINK}
<style>
@page {{ size: A4; margin: 14mm 15mm; }}
body {{ font-family: {FONT}; font-size: 11.2pt; color: #1d2733; margin: 0 auto; max-width: 780px; line-height: 1.42; }}
h1 {{ font-size: 22pt; line-height: 1.2; font-weight: 700; margin: 0 0 4px; color: #16304f; }}
h2 {{ font-size: 13pt; font-weight: 600; margin: 16px 0 5px; color: #1f5fae; }} b {{ font-weight: 600; }}
.sub {{ color: #5b6573; font-size: 10pt; }}
.badge {{ display: inline-block; padding: 4px 10px; border-radius: 4px; color: #fff; font-weight: 700; background: {colour}; margin: 8px 0 4px; }}
.cols {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
.tiles {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin: 8px 0; }}
.tile {{ border: 1px solid #dde1e7; border-radius: 6px; padding: 8px 10px; font-size: 10.2pt; }} .tile b {{ display: block; font-size: 15pt; font-weight: 700; }}
table {{ border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; }} td {{ padding: 3px 4px; border-bottom: 1px solid #e8ebef; }}
.num {{ text-align: right; white-space: nowrap; }} .bar {{ width: 40%; }} .bar span {{ display: block; height: 9px; background: #1f5fae; border-radius: 2px; }}
ul {{ margin: 2px 0 0 16px; padding: 0; }} li {{ margin-bottom: 2px; }}
</style></head><body>
<h1>Serendib University Endowment Fund</h1>
<div class="sub">{TEAM} · USD {nav / 1e6:.0f}M · seven ETFs · decision date {n['decision_date']} · market data to {n['data_end']}</div>
<div class="badge">{html.escape(n['verdict'])}</div>
<p>{lead}</p>
<div class="tiles">
<div class="tile"><b>{n['expected_return']:.2%}</b>expected a year (needs {o['required_return']:.2%})</div>
<div class="tile"><b>{money(-r['worst_crisis_loss'] * nav)}</b>worst crisis (limit {money(lim['crisis_budget'] * nav)})</div>
<div class="tile"><b>{money(-r['es99_ttc'] * nav)}</b>a very bad day, worst 1 in 100</div>
<div class="tile"><b>{mv['exceptions']} vs {mv['expected']:.1f}</b>days worse than forecast, {mv['test_start'][:4]}–{mv['test_end'][:4]}</div>
</div>
<div class="cols"><div>
<h2>The portfolio</h2><table>{bars}</table>
<h2>Income</h2><p>About {money(r['income_yield'] * nav)} a year ({r['income_yield']:.2%}) against 3% spending.</p>
</div><div>
<h2>What each crisis would cost today</h2><table>{crises}</table>
</div></div>
<h2>How sure we are</h2>
<ul>
<li><b>Risk model:</b> {html.escape(mv['champion'])} passed a one-time test on data it had never seen (Kupiec p = {mv['kupiec_p']:.2f}, Christoffersen conditional coverage p = {mv['cc_p']:.2f}).</li>
<li><b>Return:</b> a narrow margin of {money(n['return_margin_usd'])} a year. The answer changes if the equity premium is below {n['erp_breakeven']:.2%} or if the 10-year real yield falls below {n['yield_margin']['tips_threshold']:.2%}. It holds in {rob.get('ACCEPT', 0)} of {sum(rob.values())} assumption combinations.</li>
<li><b>Ten years ahead:</b> the chance of meeting the objective is about {n['ten_year']['p_objective']:.0%}, and the chance real value ends below 80% of today's is {n['ten_year']['p_real_value_below_80']:.0%}.</li>
</ul>
<h2>Next steps</h2>
<ul><li>Take tax advice on the bond fund's interest before investing: if it is taxed, the objective is no longer met.</li>
{''.join(f'<li>{html.escape(g)}</li>' for g in GOVERNANCE)}</ul>
</body></html>
"""
