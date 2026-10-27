"""One-page executive tear sheet (Step 17 §3.2), generated from the same evidence as the app and memo.

    python -m quantedge.reports.tearsheet      -> reports/tearsheet.html (print to A4 PDF from a browser)
"""

from __future__ import annotations

import html
import json

import pandas as pd

from quantedge.config import Config, load_config
from quantedge.decision.evidence import DecisionBundle, build
from quantedge.paths import ARTIFACTS, ROOT

STATUS_COLOR = {"ACCEPT": "#2e7d4f", "ADJUST RISK LIMIT": "#a46900", "REJECT": "#b23a2e"}


def _usd(x: float) -> str:
    return f"${x:,.0f}"


def _bars(weights: dict[str, float], nav: float) -> str:
    rows = []
    for t, w in sorted(weights.items(), key=lambda kv: -kv[1]):
        if w <= 1e-4:
            continue
        rows.append(f"<tr><td>{t}</td><td class='bar'><span style='width:{w * 100:.1f}%'></span></td>"
                    f"<td class='num'>{w:.1%}</td><td class='num'>{_usd(w * nav)}</td></tr>")
    return "\n".join(rows)


def render(cfg: Config, b: DecisionBundle) -> str:
    nav = cfg.nav_usd
    ev, v = b.evidence, b.verdict
    snap = pd.read_parquet(ARTIFACTS / "risk_snapshot.parquet")
    champ = snap[snap.model == b.champion].set_index("alpha")
    stress = pd.read_parquet(ARTIFACTS / "stress_matrix.parquet").loc[b.focus]
    val = pd.read_parquet(ARTIFACTS / "backtest_selection_val_500.parquet").loc[b.champion]
    status = json.loads((ARTIFACTS / "status.json").read_text(encoding="utf-8"))
    risk_rows = "\n".join(
        f"<tr><td>{a:.0%}</td><td class='num'>{_usd(champ.loc[a, 'var'] * nav)}</td>"
        f"<td class='num'>{_usd(champ.loc[a, 'es'] * nav)}</td></tr>" for a in (0.95, 0.99))
    stress_rows = "\n".join(f"<tr><td>{html.escape(k)}</td><td class='num'>{x:.1%}</td>"
                            f"<td class='num'>{_usd(-x * nav)}</td></tr>" for k, x in stress.items())
    failed = [c for c in v.checks if not c.passed]
    amend = v.adjustments.get("loosen_limits_to", {})
    amend_txt = "; ".join(f"{k} → {x:.2%}" for k, x in amend.items()) or "none"
    provisional = ("<div class='prov'>Provisional: methodology not yet frozen; the final out-of-sample test "
                   "(2023 onwards) is still locked.</div>") if status.get("provisional", True) else ""
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>QuantEdge Tear Sheet</title>
<style>
@page {{ size: A4; margin: 12mm; }}
body {{ font-family: Calibri, Arial, sans-serif; font-size: 10.5pt; color: #1d2733; margin: 0; }}
h1 {{ font-size: 16pt; margin: 0 0 2px; }} h2 {{ font-size: 11.5pt; margin: 10px 0 4px; color: #23476b; }}
.sub {{ color: #5b6773; font-size: 9pt; }}
.badge {{ display:inline-block; padding: 4px 10px; border-radius: 4px; color: #fff; font-weight: 700;
          background: {STATUS_COLOR[v.status]}; margin-top: 6px; }}
.prov {{ background:#fff4e5; border:1px solid #f0c27a; color:#7a4a00; padding:4px 8px; margin:6px 0; font-size:9pt; }}
.cols {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
table {{ border-collapse: collapse; width: 100%; }} td, th {{ padding: 2px 4px; border-bottom: 1px solid #e3e7ec; }}
th {{ text-align: left; font-size: 9pt; color: #5b6773; }} .num {{ text-align: right; white-space: nowrap; }}
.bar {{ width: 45%; }} .bar span {{ display:block; height: 9px; background:#178a85; border-radius:2px; }}
ul {{ margin: 2px 0 0 16px; padding: 0; }} li {{ margin-bottom: 2px; }}
</style></head><body>
<h1>Serendib University Endowment: Recommended Portfolio</h1>
<div class="sub">USD {nav:,.0f} · 7 ETFs · data to {status.get('data_end')} · analysis to {status.get('analysis_end')} ·
all losses 1-day unless stated</div>
<div class="badge">Rule-engine outcome: {v.status}</div>
{provisional}
<div class="cols"><div>
<h2>Allocation ({html.escape(b.focus)})</h2>
<table>{_bars(b.weights, nav)}</table>
<h2>Return</h2>
<table><tr><td>Expected (walk-forward, a year)</td><td class="num">{ev.expected_return:.2%}</td></tr>
<tr><td>Required (spending + inflation + costs)</td><td class="num">{ev.required_return:.2%}</td></tr>
<tr><td>Volatility (a year)</td><td class="num">{ev.vol_oos:.2%}</td></tr></table>
</div><div>
<h2>Risk ({html.escape(b.champion)})</h2>
<table><tr><th>Confidence</th><th class="num">VaR</th><th class="num">ES</th></tr>{risk_rows}
<tr><td>Once in 10 years</td><td class="num" colspan="2">{_usd(ev.return_level_10y * nav)}</td></tr></table>
<div class="sub">Backtest 2019–2022: {int(val.exceptions)} exceptions vs {val.expected:.1f} expected ·
Kupiec p = {val.kupiec_p:.2f} · conditional coverage p = {val.cc_p:.2f}</div>
<h2>Stress (today's weights)</h2>
<table>{stress_rows}</table>
</div></div>
<h2>What you get / what could go wrong / how we will monitor</h2>
<ul>
<li><b>What you get:</b> a bond-led allocation that kept the worst crisis loss to {b.worst_hist_loss:.1%} with today's weights.</li>
<li><b>What could go wrong:</b> stocks and bonds falling together (as in 2022); a once-a-decade day of about {_usd(ev.return_level_10y * nav)}.</li>
<li><b>How we will monitor:</b> quarterly rebalance; re-convene if the 250-day Basel light turns yellow or drawdown exceeds 10%.</li>
</ul>
<h2>Decision checks not met</h2>
<ul>{''.join(f"<li>{html.escape(c.name)}: {c.value:.2%} vs limit {c.limit:.2%}</li>" for c in failed if not isinstance(c.value, bool))}</ul>
<div class="sub">Minimum limit amendment: {amend_txt}. Amendments take effect only after explicit investment-committee approval.
The rule engine summarises evidence; the recommendation is the team's own judgement.</div>
</body></html>"""


def main() -> None:
    cfg = load_config()
    b = build(cfg)
    if b is None:
        raise SystemExit("Run `python -m quantedge.pipeline` first.")
    out = ROOT / "reports" / "tearsheet.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(render(cfg, b), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
