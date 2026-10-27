# Step 06: Performance KPIs & CAPM (Layer 1, part A)

**Owner:** P · **Week:** 1 (Days 3–4) · **Effort:** 1.5 days · **Depends on:** 04 · **Feeds:** 07, 15, 17

## 1. Target

- A tested KPI library that computes **every** KPI named in the brief, plus a few institutional extras, for any return series against any benchmark.
- **CAPM** estimation for each ETF and each portfolio: beta, Jensen's alpha with **robust t-statistics**, R², and a Security Market Line (SML) chart.
- A plain-English interpretation string for each KPI, shown in the app.

## 2. Why it matters

- Brief §8.1: teams must "**compute and interpret**" Sharpe, Sortino, Treynor, Jensen's alpha, Information Ratio, Max Drawdown, Calmar, "etc."
- Rubric: technical rigour (25%), i.e. "correct … implementation and interpretation of KPIs".
- CAPM also supplies the **expected-return prior** for portfolio construction (Step 07). That is more defensible than raw historical means.

## 3. How to achieve it

### 3.1 KPI definitions

Daily data, annualisation factor A = 252. Excess return e_t = R_t − rf_t.

| KPI | Formula | Note |
|---|---|---|
| CAGR | (V_T/V_0)^(A/T) − 1 | Geometric |
| Volatility | std(R)·√A | |
| Sharpe | mean(e)·A / (std(e)·√A) | Report the **Lo (2002) standard error**, √((1 + ½SR²)/T) (annualise carefully), giving a confidence interval |
| Sortino | mean(e)·A / DD, where DD = √(mean(min(e,0)²))·√A | Downside deviation versus MAR = rf |
| Treynor | mean(e)·A / β | β from CAPM; only meaningful when β is clearly above 0 |
| Jensen's α | Intercept of e_p = α + β·e_m + ε, annualised as α·A | HAC (Newey-West) t-statistic |
| Information Ratio | mean(R_p − R_b)·A / (std(R_p − R_b)·√A) | Benchmark = 60/40 policy |
| Max drawdown | min_t (V_t / max_{s≤t} V_s − 1) | Also peak date, trough date, recovery date and duration |
| Calmar | CAGR / \|MDD\| | |
| Omega(0) | Σmax(R,0) / Σmax(−R,0) | Extra |
| Ulcer index | √(mean(DD_t²)) | Extra: captures depth *and* duration |
| Skew, excess kurtosis, hit rate | | Feed the tail discussion |
| Tracking error | std(R_p − R_b)·√A | |

### 3.2 CAPM

- Market proxy: SPY (documented limitation: US-only, equity-only).
- Regress the daily excess return of each ETF on SPY excess return with `statsmodels.OLS(...).fit(cov_type="HAC", cov_kwds={"maxlags": 5})`.
- Output per asset: β, α (annualised), t(α), R², and the residual (idiosyncratic) volatility.
- Also run rolling 3-year betas to show **beta instability**. AGG's and GLD's betas change sign across regimes, which supports the 2022 discussion.
- **CAPM-implied expected returns:** μ_i = rf + β_i × MRP. MRP is an explicit assumption (base 5%, sensitivity 4–6%) because it is not observable from approved data; state this.
- **Known weakness to discuss:** CAPM gives GLD (β ≈ 0) an expected return close to rf, which understates its role as an inflation and crisis hedge. Step 07 can add a Black-Litterman view to correct this transparently.
- **SML chart:** x = β, y = annualised realised excess return; plot the CAPM line. Points above the line have positive realised α.

## 4. Implementation plan

| # | Function (`portfolio/metrics.py`, `portfolio/capm.py`) | Detail |
|---|---|---|
| 1 | `drawdown_series(values) -> DataFrame(dd, peak, ...)` | Underwater curve for the app |
| 2 | `max_drawdown_info(values) -> dict` | Depth, peak, trough, recovery and durations |
| 3 | `sharpe(r, rf)`, `sharpe_se_lo(r, rf)`, `sortino`, `treynor`, `information_ratio`, `calmar`, `omega`, `ulcer` | Each with a docstring formula |
| 4 | `kpi_table(r, rf, bench, market) -> DataFrame` | One row per portfolio |
| 5 | `capm_regression(asset_excess, market_excess) -> CAPMResult` | HAC errors |
| 6 | `rolling_beta(asset, market, window=756)` | For the instability chart |
| 7 | `capm_expected_returns(betas, rf_annual, mrp)` | Prior for Step 07 |
| 8 | `interpret(kpi_name, value) -> str` | e.g. "Sortino 0.9: each unit of downside volatility earned 0.9 units of excess return." |

## 5. Acceptance tests

- Hand-computed toy series (10 numbers) for every KPI, matched to 1e-10.
- Constant returns give Sharpe = inf, guarded to return NaN with a warning; a series with no drawdown gives MDD = 0.
- Simulated returns with known β = 0.7 and α = 0 give an estimated β within 0.02 and an α t-statistic not significant.
- SPY regressed on itself gives β = 1 and α = 0 exactly.
- A cross-check of MDD, Sharpe and Sortino against `empyrical`-style formulas (implemented independently in the test).

## 6. Pitfalls

- Annualising Sharpe with √252 when daily means and standard deviations are computed on **excess** versus raw returns inconsistently.
- Treynor for portfolios with β ≈ 0, which explodes. Display "n/m" (not meaningful) below |β| < 0.1.
- OLS t-statistics without HAC on autocorrelated, heteroskedastic data.
- Calling a positive α "skill" without a confidence interval. Most will be insignificant; say so honestly.

## 7. Defend it in Q&A

- *"Is your Sharpe ratio statistically different from the benchmark's?"* Here are the Lo standard errors and confidence intervals; they overlap or don't. We don't over-claim.
- *"Why SPY as the market?"* It is the only broad-market proxy in the universe. We acknowledge it is not the global market portfolio, so we use it for relative sensitivity, not as truth.
- *"Why is Sortino more relevant here?"* The client cares about downside, and Sortino penalises only downside deviation.
