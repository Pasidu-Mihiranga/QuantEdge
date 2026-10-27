"""Investment committee memo template (Step 13 §3.5).

The engine fills in the numbers; every judgement is a `[TEAM: ...]` placeholder that the team writes
(brief §8.7: no automated recommendation is presented without the team's own judgement).
"""

from __future__ import annotations

from quantedge.decision.rules import Verdict


def _usd(x: float) -> str:
    return f"${x:,.0f}"


def render_memo(verdict: Verdict, numbers: dict, nav: float) -> str:
    """Markdown memo. `numbers` keys: portfolio, weights (dict), expected_return, required_return,
    var99, es99, return_level_10y, worst_hist_loss, worst_hist_name, worst_drawdown_held, hypothetical_loss,
    champion, champion_reason, governance (list[str])."""
    n = numbers
    weights = "\n".join(f"| {t} | {w:.1%} | {_usd(w * nav)} |" for t, w in n["weights"].items() if w > 1e-4)
    checks = "\n".join(
        f"| {c.code} | {c.name} | {c.value if isinstance(c.value, bool) else f'{c.value:.2%}'} | "
        f"{c.limit if isinstance(c.limit, bool) else f'{c.limit:.2%}'} | {'pass' if c.passed else 'FAIL'} |"
        for c in verdict.checks)
    amend = ""
    if verdict.adjustments.get("loosen_limits_to"):
        rows = "\n".join(f"| {k} | {v:.2%} |" for k, v in verdict.adjustments["loosen_limits_to"].items())
        amend = (f"\n**Proposed limit amendments (minimum relaxation)**\n\n| Limit | Amended value |\n|---|---|\n{rows}\n\n"
                 "These amendments take effect only after explicit approval by the investment committee.\n")
    gov = "\n".join(f"- {g}" for g in n.get("governance", []))
    return f"""# Investment Committee Memo: Serendib University Endowment

## 1. Recommendation
Rule-engine outcome: **{verdict.status}**.
{chr(10).join(f'- {r}' for r in verdict.reasons)}
{amend}
[TEAM: the team's recommendation in two or three sentences, in its own words.]

## 2. Proposed allocation ({n['portfolio']})
| Asset | Weight | USD |
|---|---|---|
{weights}

## 3. Expected outcome
Expected return {n['expected_return']:.2%} a year against a required {n['required_return']:.2%}.
[TEAM: what this means for spending and real growth.]

## 4. Downside in plain English
- On about 1 day in 100 we expect to lose more than {_usd(n['var99'] * nav)}; on such days the average loss is {_usd(n['es99'] * nav)}.
- A once-a-decade bad day is about {_usd(n['return_level_10y'] * nav)}.

## 5. Stress results
- Today's weights replayed through each crisis: the worst is {n['worst_hist_name']}, a loss of {n['worst_hist_loss']:.1%} ({_usd(n['worst_hist_loss'] * nav)}).
- With the weights the strategy actually held at the time (walk-forward), the deepest crisis drawdown was {n['worst_drawdown_held']:.1%}.
- Hypothetical "stagflation and correlation breakdown": {n['hypothetical_loss']:.1%}.
[TEAM: the 2022 lesson (stocks and bonds falling together) and why the allocation is resilient.]

## 6. Model confidence
Risk model: **{n['champion']}** ({n['champion_reason']}).
[TEAM: backtest evidence and its limits (about 10 expected 99% exceptions per four years).]

## 7. Checks
| Check | Measure | Value | Limit | Result |
|---|---|---|---|---|
{checks}

## 8. Key risks and limitations
[TEAM: the three most important items from the Assumptions & Limitations page.]

## 9. Governance
{gov}
"""
