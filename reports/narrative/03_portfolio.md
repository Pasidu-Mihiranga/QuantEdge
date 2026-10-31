### Method

We start from Markowitz mean-variance and CAPM, but on these assets textbook optimisation pushes the portfolio into corners, because small errors in expected returns become large positions. We therefore separate the two jobs. The frontier minimises variance at each equity share under the caps, using a Ledoit-Wolf covariance matrix on 756 days. Expected returns are then used only to score the points.

> min wᵀΣw   subject to   Σ wᵢ = 1,   wᵢ ≥ 0,   Σ_equity wᵢ = e,   wᵢ ≤ capᵢ

Expected returns are built from yields on the decision date, not from past returns. AGG earns the 10-year yield plus 0.5%. Equities earn the yield plus beta times a 4.5% premium (CAPM). Gold earns breakeven inflation. Fees, withholding tax, trading costs and the variance drag ½wᵀΣw are deducted.

### Selection rule

The locked rule picks the lowest-risk frontier point that meets the objective inside every limit. It gives **ACCEPT at 35% equity**: SPY 15.6%, EFA 9.4%, AGG 65.0%, XLE 10.0%.

{{frontier_fig}}

{{frontier}}

### The trade-off

Moving from 30% to 35% equity adds 0.23 points of return, about USD 23,800 a year, for 2.0 points more crisis loss. Moving from 35% to 40% adds only 0.08 points, about USD 7,700 a year, for 1.5 points more crisis loss, and breaks the budget. The gain shrinks because of what equity replaces. Up to 35% it replaces gold, which is assumed to earn only breakeven inflation. Above 35% the gold is gone and it replaces AGG, which yields about 5.5%. So 35% is both the first point that meets the objective and the point where more risk starts to pay much less.

### Conventional alternatives

At the decision date, equal weight, 60/40, maximum Sharpe and risk parity all break the crisis budget (losses of 28–42%). Global minimum variance and minimum CVaR stay inside it but are expected to earn only 4.3–4.5%, short of the objective.

### History

{{growth}}

{{kpis}}

Since 2008 the strategy earned 5.8% a year with a worst fall of 21.1%. The 60/40 earned 8.1% with a worst fall of 33.5%. Their Sharpe ratios are equal at 0.60, so the recommended mix gave up return for less risk rather than for worse risk. Its Treynor ratio and Jensen's alpha are higher because it carries less market risk. The information ratio is negative, as it must be for a conservative mix measured against a riskier benchmark. In 2023–2026, a strong period for equities, the 60/40 was clearly ahead on return and Sharpe. That is the cost of the mandate, and we do not claim otherwise.
