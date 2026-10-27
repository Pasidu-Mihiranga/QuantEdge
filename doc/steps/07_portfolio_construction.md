# Step 07: Portfolio Construction & Selection (Layer 1, part B)

**Owner:** P · **Week:** 1 (baselines) and 2 (robust and selection) · **Effort:** 3 days · **Depends on:** 04, 05, 06 · **Feeds:** 08–13

## 1. Target

- Seven candidate portfolios built under the IPS constraints.
- Evaluation **walk-forward out-of-sample** with costs.
- A **recommended portfolio** chosen by a pre-declared scorecard.
- The efficient frontier with the capital market line (CML), the candidates and the required-return line.
- A **trade-off table** that answers "what does +1% expected return cost in drawdown and ES?"
- Bootstrap weight-stability evidence.

## 2. Why it matters

- Brief §3, item 1: construct and recommend a portfolio "using quantitative portfolio construction techniques".
- Brief §8.1: "Every team starts from Markowitz mean-variance … and CAPM".
- Brief §4: quantify the trade-offs; demonstrate diversification benefits.
- EDGEFORGE slide 49: mean-variance is sensitive to noisy inputs, so use shrinkage and robust constraints.
- Rubric: decision-making (30%) and innovation (15%, via the "which optimiser" differentiation).

## 3. How to achieve it

### 3.1 Inputs

- **Covariance Σ:** Ledoit-Wolf shrinkage (`sklearn.covariance.LedoitWolf`) on daily simple returns × 252. Show sample versus shrunk condition numbers to justify the choice.
- **Expected returns μ:** CAPM-implied (Step 06) as the prior. Optional Black-Litterman (BL) layer with at most two explicit, documented views, for example "GLD earns rf + 2% as an inflation hedge", with τ = 0.05 and Ω from He-Litterman. Raw historical means are shown **only** to demonstrate why they are not used (they are unstable).
- **Constraints:** from `ips.constraints_for_optimizer()`: long-only, full investment, per-asset bounds and group bounds.

### 3.2 Candidates (all solved with `cvxpy`, except ERC)

| # | Candidate | Formulation |
|---|---|---|
| 1 | Equal weight | w_i = 1/n (shown even if it breaches IPS group limits; flag it) |
| 2 | 60/40 benchmark | Fixed |
| 3 | Global minimum variance (GMV) | min wᵀΣw subject to IPS constraints |
| 4 | Constrained max-Sharpe | Homogenised form: min yᵀΣy s.t. (μ−rf)ᵀy = 1, Σy = κ, lb·κ ≤ y ≤ ub·κ, κ ≥ 0; then w = y/κ |
| 5 | Risk parity (ERC) | Spinu: min ½wᵀΣw − (1/n)Σ ln w_i via `scipy.optimize`; normalise; then project onto the IPS bounds and report any deviation |
| 6 | Minimum CVaR | Rockafellar-Uryasev linear program on S historical scenarios: min ζ + (1/((1−α)S)) Σ u_s, s.t. u_s ≥ −r_sᵀw − ζ, u_s ≥ 0, IPS constraints |
| 7 | **Robust Mean-ES (recommended candidate)** | max μᵀw s.t. RU-CVaR_99%(w) ≤ ES budget (IPS), wᵀΣw ≤ σ²_max, IPS constraints. If infeasible, report this and solve the ES-minimising version |

### 3.3 Efficient frontier and trade-offs

- Frontier: min wᵀΣw s.t. μᵀw = target for 40 targets, under the IPS bounds. The CML uses the current rf.
- **Trade-off table:** for target returns 3%, 4%, … 8%, report volatility, 99% ES, worst historical-stress drawdown and the IPS pass/fail. This visualises the conflict between required return and risk tolerance from Step 05.
- **Diversification evidence:** diversification ratio Σw_iσ_i / σ_p, plus the correlation heatmap in calm versus crisis periods (feeds Step 14).

### 3.4 Walk-forward selection (out-of-sample)

- Estimation window 756 days (3 years), rebalanced quarterly. The first rebalance is when 3 years of data exist (late 2007), so the OOS period is about 2008 to the snapshot date and includes all three crises.
- At each rebalance, re-estimate Σ and μ using data up to t−1 only, re-optimise, and apply 5 bps per side.
- **Scorecard, declared before looking at results:**
  1. OOS 99% ES
  2. OOS max drawdown
  3. Calmar
  4. Worst crisis loss
  5. Turnover
  6. OOS return versus the required return

  Pass/fail against the IPS comes first, then a ranking on 1 and 2 (capital preservation), then 3.
- Report results for all 7 candidates in one table. The recommendation must win **on the declared criteria**, or we recommend whichever does.

### 3.5 Weight stability

Stationary block bootstrap (mean block length 20 days, 200 resamples) of the estimation window. Re-optimise each resample and show the weight distribution for each asset as boxplots. Robust Mean-ES and ERC should show tighter boxes than max-Sharpe; that is the evidence for "robust".

## 4. Implementation plan

| # | Function (`portfolio/optimize.py`, `portfolio/walkforward.py`) | Detail |
|---|---|---|
| 1 | `estimate_inputs(returns, method="ledoit_wolf", mu="capm", bl_views=None) -> (mu, Sigma)` | |
| 2 | `gmv`, `max_sharpe`, `erc`, `min_cvar`, `robust_mean_es`, `equal_weight`, `fixed` | Each returns `OptResult(weights, status, objective, diagnostics)` |
| 3 | `efficient_frontier(mu, Sigma, constraints, n=40)` | |
| 4 | `tradeoff_table(targets, ...)` | |
| 5 | `black_litterman(Sigma, w_prior, views, tau)` | Optional |
| 6 | `walk_forward(returns, strategy_fn, window, rebalance, cost_bps) -> WFResult(perf, weights_history, turnover)` | Uses `performance_series` from Step 04 |
| 7 | `bootstrap_weights(returns, strategy_fn, n=200, block=20, rng)` | |
| 8 | `scorecard(wf_results, ips) -> DataFrame` with a rank column | Persisted to artifacts |
| 9 | Solver robustness: try CLARABEL, then fall back to ECOS/SCS; surface any non-optimal status | |

## 5. Acceptance tests

- With 2 assets and no bounds, GMV matches the closed form w = Σ⁻¹1 / 1ᵀΣ⁻¹1.
- With no bounds, max-Sharpe matches the closed form Σ⁻¹(μ−rf) normalised.
- ERC: each risk contribution w_i(Σw)_i is within 1e-6 of the others.
- Min-CVaR: the realised in-sample CVaR of the solution is no greater than that of the GMV portfolio and of equal weight.
- Every solution satisfies all IPS constraints to within 1e-8.
- Walk-forward: an assertion that the estimation window end is strictly before the rebalance date (no look-ahead).

## 6. Pitfalls

- Using historical means as μ, which produces corner solutions (100% in last decade's winner, typically XLK).
- Selecting the portfolio on in-sample Sharpe.
- Optimising on the full sample and then "backtesting" the result. That is look-ahead.
- Treating ERC as satisfying the IPS when it violates the group caps. Project onto the bounds and report the deviation.
- An ES constraint estimated on the same scenarios used for evaluation. The walk-forward fixes this.

## 7. Defend it in Q&A

- *"Why not just maximise Sharpe?"* Max-Sharpe weights are unstable (bootstrap boxplots) and depend on noisy μ. The client's objective is downside control, so we optimise return **subject to an ES budget**.
- *"Why Ledoit-Wolf?"* The sample covariance is noisy (condition number X versus Y). Shrinkage stabilises the inverse that the optimiser relies on.
- *"Where is Markowitz?"* The frontier chart, GMV and max-Sharpe are all Markowitz. The recommended portfolio extends Markowitz with a tail-risk constraint.
- *"How do we know you didn't cherry-pick?"* The scorecard was declared before results and all 7 candidates are shown side by side out-of-sample.
