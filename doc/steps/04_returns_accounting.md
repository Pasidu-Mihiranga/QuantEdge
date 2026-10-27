# Step 04: Returns & Portfolio Accounting

**Owner:** P · **Week:** 1 (Day 3) · **Effort:** 1 day · **Depends on:** 03 · **Feeds:** 06–14

## 1. Target

- One correct, documented convention for every return series used in the project.
- Two distinct portfolio series:
  - (a) **Performance series**: realistic, with weights that drift between rebalances and transaction costs. Used for KPIs, cumulative return and drawdown.
  - (b) **Risk series**: current target weights applied to historical asset returns. Used for VaR, ES, EVT and backtesting inputs.
- A daily risk-free rate series, and an optional **cash sleeve** asset.
- Loss and P&L in USD on a $10M NAV.

## 2. Why it matters

- Brief §9.2: "Convert to log returns for statistical work and clearly state where simple returns are used instead and why."
- EDGEFORGE slide 16: a weighted average of log returns is **not** the portfolio log return.
- Mixing up (a) and (b) is the most common silent error in student risk projects.

## 3. How to achieve it

### 3.1 Conventions (write these on the Methodology page verbatim)

| Quantity | Formula | Used for |
|---|---|---|
| Asset simple return | R_i,t = P_i,t / P_i,t−1 − 1 | Portfolio aggregation |
| Portfolio simple return | R_p,t = Σ w_i,t−1 R_i,t | Exact across assets |
| Portfolio log return | r_p,t = ln(1 + R_p,t) | Statistical tests, GARCH, distribution fitting |
| Loss (USD) | L_t = −R_p,t × NAV | VaR, ES and EVT reported in $ |
| Loss (%) | ℓ_t = −R_p,t | Model fitting |

Sign convention: **VaR and ES are positive numbers meaning losses.** State this on every chart.

### 3.2 Performance series with drift and rebalancing

```
V_i,t = V_i,t−1 × (1 + R_i,t)                         # positions drift
on rebalance dates (quarter-end):
    target = w* × V_total,t
    cost   = c × Σ |target_i − V_i,t|                 # c = 5 bps per side
    V_i,t  = target_i − cost × w*_i                   # cost charged pro rata
R_perf,t = V_total,t / V_total,t−1 − 1
```

ETF expense ratios are **already embedded** in ETF prices and NAV. Do not subtract them again; say so in the assumptions.

### 3.3 Risk series

R_risk,t = Σ w*_i R_i,t, i.e. "what would today's portfolio have experienced on each historical day". This is the standard input for VaR and backtesting.

### 3.4 Risk-free rate and cash sleeve

- DTB3 is an annualised **bank-discount** rate d (%, 360-day basis, 91-day bill).
- Convert to the bond-equivalent yield: `BEY = 365·d / (360 − 91·d)`, with d in decimals.
- Daily rate: `rf_t = (1 + BEY)^(1/252) − 1`, applied to the next trading day (use the yield known at t−1, so there is no look-ahead).
- **Cash sleeve:** when `allow_cash=true`, add a synthetic asset "CASH" with return rf_t and zero volatility. Optimisers then treat it as an 8th asset with bounds from the IPS. It is labelled "T-bill sleeve (sensitivity)" everywhere.

### 3.5 Horizons

- 1-day is the base horizon.
- For h-day figures (10-day, 1-year) the default is **simulation or overlapping-window historical**, with √h scaling shown only as a labelled approximation. Note that √h assumes i.i.d. returns, which Step 03 shows is violated.

## 4. Implementation plan

| # | Function (`portfolio/returns.py`) | Detail |
|---|---|---|
| 1 | `simple_returns(prices)`, `log_returns(prices)` | Drop the first NaN row and log it |
| 2 | `risk_free_daily(dtb3, index) -> Series` | Discount → BEY → daily, lagged one day, aligned |
| 3 | `add_cash_asset(returns, rf) -> DataFrame` | Adds a CASH column |
| 4 | `risk_series(returns, weights) -> Series` | Fixed weights; validates that they sum to 1 and that tickers match |
| 5 | `performance_series(returns, weights, rebalance="Q", cost_bps=5) -> PerfResult(returns, values, weights_path, turnover, costs)` | Drift and rebalance engine |
| 6 | `to_usd(loss_pct, nav)` | Helper |
| 7 | `horizon_returns(r, h, overlapping=True)` | For h-day empirical distributions |

## 5. Acceptance tests

- Two assets with weights 50/50: R_p equals the mean of the simple returns exactly. Assert that the mean of log returns **differs** from ln(1+R_p) when returns are nonzero (this documents the trap).
- No rebalancing and zero cost: the performance series equals buy-and-hold computed independently.
- Daily rebalancing with zero cost: the performance series equals the risk series.
- `rf_daily` compounded over 252 days is within 1 bp of the BEY.
- The cash asset has zero variance and its covariance row is all zeros.

## 6. Pitfalls

- Summing log returns across assets.
- Using the performance series (with drifting weights) for VaR. Risk must reflect **current** weights.
- Applying rf without the one-day lag.
- Double-counting expense ratios.
- Reporting VaR as a negative return in one chart and a positive loss in another.

## 7. Defend it in Q&A

- *"Log or simple returns?"* Simple returns to aggregate across assets, because that is exact. Log returns for statistical modelling of the single portfolio series, because they are time-additive and closer to symmetric. For 1-day horizons the difference is tiny, but the aggregation rule matters.
- *"Why two portfolio series?"* Performance must reflect what really happens (drift and costs). Risk must reflect what we hold now.
