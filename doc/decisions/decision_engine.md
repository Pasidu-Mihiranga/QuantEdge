# Decision record: verdict logic (Step 13)

**Date:** 2026-10-28 · **Status:** adopted by the team

## Decision

The engine returns one of three outcomes: **ACCEPT**, **ADJUST RISK LIMIT** or **REJECT**.

- **ACCEPT:** all risk checks pass, the selected model is validated, and the return objective is met (or the gap is below the disclosed tolerance). **Updated 2026-10-29 (D10):** the tolerance is 0, so ACCEPT needs the objective met; risk checks C1–C4 use the D2 measures (through-the-cycle volatility and 99% ES, worst crisis loss with today's weights) and C8 the forward expected return (notebooks 03 §4, 06 A2; `decision/objective.py`).
- **ADJUST RISK LIMIT:** some risk limits fail, but a **minimum-relaxation calculation** finds the smallest loosening of the named limits under which a candidate portfolio passes.
  - The output names each limit, its current value, the minimum required value and the relative loosening.
  - **Amendments require explicit client approval:** the investment committee must approve the amended limits before implementation. The verdict and the memo state this condition.
- **REJECT:** either of the following:
  - no risk model passes validation, so risk cannot be measured reliably; or
  - the minimum relaxation exceeds the declared maximum (`decision.max_limit_relaxation`, 50%).

## Minimum relaxation

For each candidate portfolio, the required value of each failing limit is the portfolio's own value of that measure. The candidate chosen is the one whose **largest relative loosening** across all failing limits is smallest (a minimax choice). This finds the least amendment that makes some feasible portfolio comply, rather than only loosening the limits around one pre-chosen portfolio.

## Implementation

`decision/rules.py::minimum_relaxation`, `decision/rules.py::evaluate` (`adjustments["client_approval_required"] = True`).
