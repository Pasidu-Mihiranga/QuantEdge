# Investment Committee Memo: Serendib University Endowment

## 1. Recommendation
Rule-engine outcome: **ADJUST RISK LIMIT**.
- No portfolio meets the current risk limits. Minimum relaxation: Min CVaR complies if es99_1d_max is loosened to 1.63% (+9%).
- Amended limits require explicit approval by the investment committee (client) before implementation.
- Re-sizing needed for: Max risk-to-capital ratio.
- Expected return is 2.41% below the required return: lower the return objective, review the spending rate, or loosen a named risk limit.

**Proposed limit amendments (minimum relaxation)**

| Limit | Amended value |
|---|---|
| es99_1d_max | 1.63% |

These amendments take effect only after explicit approval by the investment committee.

[TEAM: the team's recommendation in two or three sentences, in its own words.]

## 2. Proposed allocation (Min CVaR)
| Asset | Weight | USD |
|---|---|---|
| SPY | 10.4% | $1,038,503 |
| EFA | 4.6% | $461,497 |
| AGG | 65.0% | $6,500,000 |
| GLD | 20.0% | $2,000,000 |

## 3. Expected outcome
Expected return 4.27% a year against a required 6.68%.
[TEAM: what this means for spending and real growth.]

## 4. Downside in plain English
- On about 1 day in 100 we expect to lose more than $171,653; on such days the average loss is $220,591.
- A once-a-decade bad day is about $341,382.
- Over 10 trading days, the 99% ES is $617,491 (6.17% of NAV, reported limit 5%).

## 5. Stress results
- Today's weights replayed through each crisis: the worst is Rate shock 2022, a loss of 15.2% ($1,524,906).
- With the weights the strategy actually held at the time (walk-forward), the deepest crisis drawdown was 17.8%.
- Hypothetical "stagflation and correlation breakdown": 12.7%.
[TEAM: the 2022 lesson (stocks and bonds falling together) and why the allocation is resilient.]

## 6. Model confidence
Risk model: **Conditional EVT** (lowest 99% pinball loss among adequately validated models (provisional until the final test)).
[TEAM: backtest evidence and its limits (about 10 expected 99% exceptions per four years).]

## 7. Checks
| Check | Measure | Value | Limit | Result |
|---|---|---|---|---|
| C1 | Volatility (OOS, annualised) | 6.31% | 8.00% | pass |
| C2 | Worst historical stress drawdown | 17.76% | 20.00% | pass |
| C3 | Hypothetical scenario loss | 12.69% | 20.00% | pass |
| C4 | 99% 1-day ES (selected model) | 2.21% | 1.50% | FAIL |
| C5a | EVT 99% ES | 1.42% | 1.88% | pass |
| C5b | Once-in-10-years daily loss (EVT) | 3.41% | 5.00% | pass |
| C6 | Backtest validity of the selected model | True | True | pass |
| C7 | Max risk-to-capital ratio | 210.95% | 200.00% | FAIL |
| C8 | Expected return vs required | 4.27% | 6.68% | FAIL |

## 8. Key risks and limitations
[TEAM: the three most important items from the Assumptions & Limitations page.]

## 9. Governance
- Rebalance quarterly to the target weights (5 bps per side assumed).
- Re-convene the committee if the 250-day Basel traffic light turns yellow or red.
- Re-convene if the portfolio drawdown exceeds 10% from its peak.
- Review the IPS limits and the spending rate annually, and after any limit amendment.
- Any amended limit takes effect only after explicit investment-committee approval.
