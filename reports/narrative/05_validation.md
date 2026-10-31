### Design

Every model forecasts each day from data up to the day before, using the weights actually held. Forecasts are refitted every 5 days on a 500-day trailing window. We selected on 2019–2022 and tested once on 2023–2026, after a git tag (`methodology-freeze-v1`) had frozen the method.

### Tests

**Kupiec's proportion-of-failures test** asks whether the number of breaches x in T days matches the coverage p.

> LR_uc = −2 ln [ (1 − p)^(T − x) p^x / ( (1 − x/T)^(T − x) (x/T)^x ) ] ~ χ²(1)

**Christoffersen's independence test** asks whether breaches cluster, using the transition counts between breach and no-breach days. Added to Kupiec's statistic it gives conditional coverage, χ²(2). **The Basel traffic light** counts 99% breaches in each 250-day window: green up to 4, yellow 5–9, red 10 or more. We add the Acerbi-Székely Z2 test for ES, since VaR tests cannot see ES. Models that pass are ranked by the pinball loss, a proper score for quantiles.

> L = (y − q)(τ − 1{y < q})

### Selection on 2019–2022

A model passes if it clears Kupiec and conditional coverage at 5%, has no red rolling window, and has a green Z2. The rule, fixed in advance, picks the lowest pinball loss among those that pass.

{{validation}}

Models that ignore current volatility fail on clustering, however good their total count. The rule picks **GJR conditional EVT**: GJR-GARCH volatility, where falls raise volatility more than rises, with a GPD tail on the residuals (McNeil and Frey, 2000). It had 14 breaches against 10.1 expected. Every breach has a documented market cause, and six were the first days of a new crisis. It has no red rolling window, although 34% of its windows are yellow.

{{crises}}

Under stress the gap between models is wide. Models without a volatility forecast were overrun in 2008 and 2022, with up to nine times the expected breaches. Volatility-aware models stayed near expectation there. The COVID crash overran every model, because no daily model can react to a fall that sharp. That is why the fund has a crisis budget and stress tests as well as a daily risk number.

### One-shot test on 2023–2026

{{backtest_fig}}

The champion passed: 9 breaches against 9.6 expected over 955 days, Kupiec p = 0.86, conditional coverage p = 0.19, and the lowest pinball loss of eleven models (Table 10). Only three models passed; those without GJR's asymmetry failed because their breaches clustered. A separately written notebook reproduced the breaches and losses.

### What the test does not show

About ten expected breaches give limited power, so the test shows the model is not detectably wrong, not that it is right. Over all of 2008–2026 the joint coverage test falls just below 5% because of clustering in 2008.
