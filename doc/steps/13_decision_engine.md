# Step 13: Risk Budgeting & Decision Engine

**Owner:** P · **Week:** 3 (Days 3–5) · **Effort:** 2 days · **Depends on:** 05, 08–12 · **Feeds:** 15, 17, 18

## 1. Target

- **Euler risk decomposition:** marginal, component and percentage contributions to VaR and ES for each asset, which add up to the total.
- **Position-sizing recommendations** derived from the risk budget.
- A transparent, **rule-based verdict: ACCEPT / ADJUST RISK LIMIT / REJECT**, with every check visible, plus the adjusted portfolio and limits when the verdict is ADJUST.
- A data-filled **investment committee memo template** (the team writes the narrative).

## 2. Why it matters

- Brief §8.6: "Risk budgeting and position sizing, using each position's marginal VaR/ES contribution", and "a one-page, plain-English recommendation (accept the mandate as proposed / adjust the risk limit / reject)".
- Rubric: investment decision-making (30%), i.e. "a sound, actionable, client-appropriate recommendation, not just a set of numbers".
- Brief §8.7: the recommendation must be the team's own judgement. The engine computes the evidence and a rule outcome; the team owns the final call and the wording.

## 3. How to achieve it

### 3.1 Euler allocation

Risk measures that are homogeneous of degree 1 satisfy ρ(w) = Σ w_i ∂ρ/∂w_i.

| Measure | Marginal | Component |
|---|---|---|
| Parametric VaR (μ ≈ 0) | z_α (Σw)_i / σ_p | w_i z_α (Σw)_i / σ_p |
| Parametric ES (Normal) | [φ(z_α)/(1−α)] (Σw)_i / σ_p | w_i × marginal |
| Simulation or historical ES | −E[r_i \| ℓ_p ≥ VaR_p] | −w_i E[r_i \| ℓ_p ≥ VaR_p] (average over the tail scenarios) |
| Simulation VaR | −E[r_i \| ℓ_p ≈ VaR_p], using a kernel window of ±k scenarios around the VaR order statistic | Noisy; report it with a caveat and prefer ES |

**Outputs:**
- %-contribution = component / total.
- The **risk-to-capital ratio** RC_i = %-contribution / w_i.
- The chart: capital weights against ES contributions (side-by-side bars). The typical insight: "XLK is 8% of capital but 20% of tail risk; AGG is 35% of capital but 10% of tail risk."

### 3.2 Position-sizing rules

- **Flag** any asset with RC_i > 1.5 (it takes more than 1.5× its capital share of tail risk).
- **Marginal re-sizing:** the move that reduces ES the most per unit of expected return given up is to cut the asset with the highest marginal ES / μ_i and add to the one with the lowest, subject to the IPS bounds.
- **Proposed adjusted portfolio:** re-solve Step 07's Robust Mean-ES with the binding limit tightened, or with a per-asset ES-contribution cap of 25% each. Show before and after for weights, VaR, ES, worst stress and expected return.

### 3.3 Decision rules (`decision/rules.py`), declared and versioned

| Check | Source | Pass condition |
|---|---|---|
| C1 Volatility | Step 06 (walk-forward OOS) | ≤ IPS limit |
| C2 Worst historical stress drawdown | Step 12 | ≤ IPS limit |
| C3 Hypothetical scenario loss | Step 12 | ≤ IPS limit |
| C4 99% 1-day ES (selected model) | Steps 09 and 10 | ≤ IPS budget |
| C5 EVT 99% ES and 1-in-10-year loss | Step 10 | ≤ IPS budget × tolerance (e.g. 1.25) |
| C6 Backtest validity | Step 11 | Selected model: Kupiec and CC p > 0.05; Basel green |
| C7 Concentration | Step 13 | No RC_i > 2.0 |
| C8 Return objective | Steps 05 and 07 | Expected return ≥ required return (or gap disclosed) |

Verdict logic:
- **ACCEPT** if C1–C7 all pass and C8 passes or its gap is under 1%.
- **ADJUST RISK LIMIT** if:
  - (a) some of C1–C5 or C7 fail, **and** a feasible re-sized portfolio exists that passes them; output the new weights; **or**
  - (b) C8 fails by 1% or more; output the trade-off (accept a lower return objective or a spending-rate review, versus loosening a named risk limit by a stated amount).
- **REJECT** if C6 fails for all models (risk cannot be measured reliably), **or** no feasible portfolio satisfies the IPS risk limits.

Every check is displayed as a row: value, limit, margin and a pass/fail icon. The verdict banner appears on Home and in the tear sheet.

### 3.4 Sensitivity of the verdict (robustness)

Re-run the verdict under:
- confidence 95% versus 99%;
- window 250, 500 or 1000;
- cash allowed versus not;
- MRP 4%, 5% or 6%.

Show a small matrix. A verdict that flips easily must be disclosed; a stable verdict strengthens the defence.

### 3.5 Committee memo template (`decision/memo.py`)

The template is auto-filled with numbers; the team writes the narrative. Sections:
1. Recommendation
2. Proposed allocation (and USD amounts)
3. Expected outcome
4. Downside in plain English ("On 1 day in 100 we expect to lose more than $X; on such days the average loss is $Y; a once-a-decade bad day is about $Z")
5. Stress results
6. Model confidence
7. Key risks and limitations
8. Governance (rebalancing, review triggers such as "re-convene if the 250-day Basel zone turns yellow or drawdown exceeds 10%")

## 4. Implementation plan

| # | File / function | Detail |
|---|---|---|
| 1 | `risk/contributions.py::euler_parametric(w, Sigma, alpha, measure)` | |
| 2 | `risk/contributions.py::euler_simulation_es(w, scenarios, alpha)` and `euler_simulation_var(..., k)` | |
| 3 | `decision/sizing.py::risk_to_capital(w, contrib)`, `propose_resize(...)` | Uses Step 07's optimiser |
| 4 | `decision/rules.py::evaluate(evidence: Evidence, ips: IPSLimits) -> Verdict(status, checks, adjusted)` | Pure function, fully unit-tested |
| 5 | `decision/rules.py::verdict_sensitivity(grid)` | |
| 6 | `decision/memo.py::render_memo(evidence, verdict, narrative_md) -> md/html` | Feeds the tear sheet (Step 17) |

## 5. Acceptance tests

- Euler components sum to total VaR/ES within 1e-8 (parametric) or within the MC standard error (simulation).
- A two-asset analytical example matches the hand calculation.
- Rule engine: a table-driven test with about 12 synthetic evidence sets covering every branch (ACCEPT, both ADJUST cases, both REJECT cases, and boundary values).
- Changing an IPS limit in config flips the verdict as expected (integration test).

## 6. Pitfalls

- Euler contributions of simulation VaR are very noisy. Lead with ES contributions.
- A verdict that depends on a hidden threshold. Every threshold lives in `config.yaml` and is displayed.
- Letting the engine "write" the recommendation. Brief §8.7 forbids presenting an AI or automated recommendation without the team's own judgement. The engine provides the evidence; the team signs the memo.

## 7. Defend it in Q&A

- *"Why is your verdict ADJUST and not ACCEPT?"* Point to the failed check(s) and margin, the proposed adjustment and its cost in expected return.
- *"Which position would you cut first in a crisis?"* The highest risk-to-capital asset (from the chart), because cutting it reduces ES most per dollar of expected return.
- *"Would your verdict change at 95%?"* Show the sensitivity matrix.
