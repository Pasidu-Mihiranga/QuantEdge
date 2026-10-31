"""The committee pack: a one-page summary and two tables to download, built only from decision_numbers.json.

The written report and memo in reports/ are edited by the team; this pack always matches the app.
"""

from __future__ import annotations

import html

import pandas as pd

from components.ui import money, pct

NAMES = {"SPY": "US stocks", "EFA": "Developed-market stocks", "EEM": "Emerging-market stocks",
         "AGG": "US investment-grade bonds", "GLD": "Gold", "XLE": "Energy stocks", "XLK": "Technology stocks"}

PAGE = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>Committee summary</title><style>
body{{font:15px/1.5 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:#1d2733;max-width:760px;margin:32px auto;padding:0 20px}}
h1{{font-size:22px;margin:0 0 4px}} h2{{font-size:16px;margin:26px 0 8px;border-bottom:1px solid #dde1e7;padding-bottom:4px}}
.meta{{color:#5b6573;font-size:13px}} .verdict{{background:#eef3fa;border-left:4px solid #1f5fae;padding:12px 16px;margin:16px 0}}
table{{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}} td,th{{text-align:left;padding:5px 8px;border-bottom:1px solid #eef0f3}}
th{{color:#5b6573;font-weight:600;font-size:13px}} td.n,th.n{{text-align:right}} .ok{{color:#0d7a2f}} .no{{color:#b42318}}
@media print{{body{{margin:0}}}}
</style></head><body>{body}</body></html>"""


def weights_table(n: dict) -> pd.DataFrame:
    w = pd.Series(n["weights"]).loc[lambda s: s > 1e-4].sort_values(ascending=False)
    return pd.DataFrame({"fund": [NAMES[t] for t in w.index], "ticker": w.index, "weight": w.round(4).values,
                         "usd": (w * n["nav_usd"]).round(0).values})


def crises_table(n: dict) -> pd.DataFrame:
    cm = pd.Series(n["crisis_map"]).sort_values(ascending=False)
    return pd.DataFrame({"episode": cm.index, "loss_share": cm.round(4).values, "loss_usd": (cm * n["nav_usd"]).round(0).values,
                         "inside_budget": (cm <= n["limits"]["crisis_budget"]).values})


def summary_html(n: dict) -> str:
    nav, obj, lim, risk, mv = n["nav_usd"], n["objective"], n["limits"], n["risk"], n["model_validity"]
    e = html.escape
    row = lambda *c: "<tr>" + "".join(f"<td{' class=n' if i else ''}>{e(str(x))}</td>" for i, x in enumerate(c)) + "</tr>"  # noqa: E731
    check = lambda ok: "<span class=ok>met</span>" if ok else "<span class=no>not met</span>"  # noqa: E731
    limits = [("Expected return a year", pct(n["expected_return"], 2), f"at least {pct(obj['required_return'], 2)}",
               n["expected_return"] >= obj["required_return"]),
              ("Worst crisis loss", f"{pct(risk['d2_loss'])} ({risk['worst_crisis']})", f"at most {pct(lim['crisis_budget'], 0)}",
               risk["d2_loss"] <= lim["crisis_budget"]),
              ("Volatility, through the cycle", pct(risk["vol_ttc"], 2), f"at most {pct(lim['vol_max'], 2)}",
               risk["vol_ttc"] <= lim["vol_max"]),
              ("99% one-day ES, through the cycle", pct(risk["es99_ttc"], 2), f"at most {pct(lim['es99_max'], 2)}",
               risk["es99_ttc"] <= lim["es99_max"])]
    rob, ten = n["robustness"], n["ten_year"]
    body = [
        "<h1>Investment committee summary</h1>",
        f"<div class=meta>Serendib University Endowment · {money(nav)} · decision date {e(n['decision_date'])} · "
        f"market data to {e(n['data_end'])}</div>",
        f"<div class=verdict><b>{e(n['verdict'])}.</b> Invest {n['advised_equity']:.0%} in equities and "
        f"{1 - n['advised_equity']:.0%} in {'bonds' if n['weights']['GLD'] < 1e-4 else 'bonds and gold'}. Expected return {pct(n['expected_return'], 2)} a year "
        f"against the {pct(obj['required_return'], 2)} the objective needs (spending {pct(obj['spending'], 1)}, real growth "
        f"{pct(obj['real_growth'], 1)}, plus inflation).</div>",
        "<h2>Allocation</h2><table><tr><th>Fund</th><th class=n>Ticker</th><th class=n>Weight</th><th class=n>USD</th></tr>"
        + "".join(row(r.fund, r.ticker, pct(r.weight), money(r.usd)) for r in weights_table(n).itertuples()) + "</table>",
        "<h2>Every limit</h2><table><tr><th>Measure</th><th class=n>Portfolio</th><th class=n>Limit</th><th></th></tr>"
        + "".join(f"<tr><td>{e(a)}</td><td class=n>{e(b)}</td><td class=n>{e(c)}</td><td>{check(ok)}</td></tr>"
                  for a, b, c, ok in limits) + "</table>",
        "<h2>Crises, with today's weights</h2><table><tr><th>Episode</th><th class=n>Loss</th><th class=n>USD</th></tr>"
        + "".join(row(r.episode, pct(r.loss_share), money(-r.loss_usd)) for r in crises_table(n).itertuples()) + "</table>",
        "<h2>A bad day</h2>"
        f"<p>On about 1 day in 100 the fund loses more than {money(n['risk_day']['var99'] * nav)}, and "
        f"{money(n['risk_day']['es99'] * nav)} on average on those days (last two years, which were calm). Including 2008, "
        f"the average very bad day costs {money(risk['es99_ttc'] * nav)}. The risk model ({e(mv.get('champion', ''))}) "
        f"was tested once on {mv.get('days')} unseen days (2023-2026): {mv.get('exceptions')} misses against "
        f"{mv.get('expected', 0):.1f} expected, Kupiec p = {mv.get('kupiec_p', 0):.2f}.</p>",
        "<h2>How sure we are</h2><ul>"
        f"<li>The expected return clears the objective by {pct(n['return_margin'], 2)} ({money(n['return_margin_usd'])} a "
        "year): a narrow margin.</li>"
        f"<li>Across {sum(rob.values())} combinations of the equity premium, bond spread and tax assumptions the answer is "
        f"ACCEPT in {rob.get('ACCEPT', 0)}, ADJUST in {rob.get('ADJUST', 0)} and REJECT in {rob.get('REJECT', 0)}.</li>"
        f"<li>Over ten years the chance of meeting the objective is {ten['p_objective']:.0%}, and the chance the fund's real "
        f"value falls below 80% is {ten['p_real_value_below_80']:.0%} ({ten['paths']:,} simulated paths).</li></ul>",
        "<p class=meta>Generated by the QuantEdge app from data/artifacts/decision_numbers.json. History is not a forecast.</p>",
    ]
    return PAGE.format(body="\n".join(body))
