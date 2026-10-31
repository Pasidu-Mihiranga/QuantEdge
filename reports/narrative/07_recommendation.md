### Position sizing

Position sizing uses each holding's marginal contribution to ES. Euler's theorem splits the total, so the contributions add up exactly.

> ESᵢ = wᵢ × E[ −Rᵢ | L ≥ VaR ]     and     Σ ESᵢ = ES

{{contributions}}

No fund carries more than 40% of the tail risk, so the sizing rule moved nothing. The largest share is SPY at 33%. XLE is the most risk-dense holding, at three times its weight. AGG is 65% of the money but 16% of the tail risk, which is how a conservative portfolio should look.

### Verdict

The rule has three outcomes. ACCEPT if a portfolio meets the objective inside every limit. ADJUST THE RISK LIMIT if one would with the crisis budget loosened by at most 5 points. REJECT otherwise. We recorded in advance that the verdict would turn on real yields: on end-2022 yields the same rule gave REJECT, and a 10-year TIPS yield of about 2.58% would flip it. On the decision date it was 2.66%, and the rule gave **ACCEPT at 35% equity**.

### How close it is

ACCEPT is lost if the real yield falls by 0.15 points or if the equity premium is below 4.15%, against our 4.5%. Across 18 assumption combinations it is ACCEPT in 7, ADJUST in 4 and REJECT in 7. The largest single swing is tax: if AGG's interest is taxed at 15%, the base case becomes REJECT.

{{grid}}

Over ten years, a block bootstrap puts the chance of meeting the objective at about 49%, with a median real return of 3.5% a year and an 8% chance that real value ends below 80% of today's. These figures are context, not part of the rule.

### Why this suits a conservative institution

- **It protects capital first.** Each limit holds, and the worst crisis on record stays inside the budget.
- **Income pays the scholarships.** Dividends and interest of about USD 327,000 a year (3.27%) cover the 3% spending rate, so the fund does not need to sell in a crisis.
- **It is simple and liquid.** Four liquid ETFs and a quarterly rebalance.
- **Its weaknesses are known.** The committee sees in advance where the bond hedge fails and what would change the answer.

### Governance

- Rebalance to target weights every quarter.
- If the daily risk forecast stays above the limit for 5 days, the committee meets. Nothing is sold automatically, because an automatic de-risking rule made results worse out of sample.
- Review the spending rate, the limits and the return assumptions every year.
- Obtain tax advice on AGG's interest before investing.
