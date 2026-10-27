# Step 14: Innovation Extensions

**Owner:** R + V · **Week:** 3 · **Effort:** 3 days total (cut in the order listed in the index if late) · **Depends on:** 08–12 · **Feeds:** 13, 15, 17

## 1. Target

Four well-justified extensions that strengthen the investment decision, not "algorithm novelty":
- **A. Regime-conditioned risk** (Markov switching and VIX regimes)
- **B. Volatility-target risk overlay**, backtested with costs
- **C. t-copula Monte Carlo**, for joint-crash dependence
- **D. Macro and FX risk assessment**: the stock-bond correlation regime, inflation, and USD/LKR

Already counted as innovation in earlier steps: GARCH-FHS (Step 08), conditional EVT and alternative threshold rules (Step 10), the Acerbi-Szekely ES backtest (Step 11), and the reverse stress test with stressed correlations (Step 12).

## 2. Why it matters

- Rubric: innovation and ambition (15%), i.e. "well-justified extensions: e.g., **regime-conditioned risk, optional risk overlays, alternative EVT threshold rules**". A and B are named verbatim.
- Brief §4, item 9 (optional): other macro, industry or market risks. These count towards the 30% decision-making criterion ("including optional items").
- EDGEFORGE slide 73: reward incremental value **after costs**, not algorithm novelty. Every extension must show its effect on a decision metric.

## 3. How to achieve it

### A. Regime-conditioned risk

- Model: `statsmodels.tsa.regime_switching.markov_regression.MarkovRegression(r_p, k_regimes=2, switching_variance=True)` on daily portfolio returns (or weekly, for stability).
- Use **filtered** probabilities P(high-vol | data up to t) only. Smoothed probabilities use future data (leakage).
- Cross-validate the regimes against VIX bands (VIX < 20 calm, 20–30 elevated, > 30 stressed) and the crisis windows.
- Outputs:
  - regime-conditional VaR and ES (HS within each regime, or Normal with regime σ);
  - the current regime probability;
  - expected duration of each regime, 1/(1 − p_ii).
- **Decision use:** in the high-vol regime, the 99% ES is X times the calm value. The governance rule says to review exposure when P(high) > 0.7.

### B. Volatility-target overlay (risk overlay)

- Rule: target portfolio volatility σ* (= IPS limit). Each week, compute the GARCH forecast σ̂_{t+1}. If σ̂ > σ*, scale the risky sleeve (equities and GLD) by σ*/σ̂ and move the difference into AGG, or into CASH if enabled. Cap total turnover at 20% a month.
- Backtest walk-forward with 5 bps per side, against the static recommended portfolio.
- Report: max drawdown, ES, CAGR, Calmar, turnover and costs, plus per-crisis performance.
- **Honesty requirement:** if the overlay does not improve drawdown after costs, report that. In 2022, moving into AGG would *not* have helped, because bonds fell too; this is a teachable finding.

### C. t-copula Monte Carlo

- Marginals: the empirical CDF of each ETF's returns, with GPD tails above and below a 10% threshold (semi-parametric). Transform to pseudo-observations u = rank/(n+1).
- Fit a Student-t copula: correlation R from Kendall's τ (ρ = sin(πτ/2)); degrees of freedom ν by profile maximum likelihood.
- Simulate 100k draws, map back through the marginals, and compute portfolio VaR and ES.
- Compare with a Gaussian copula holding the same R. Show:
  - the joint-crash probability P(SPY and EFA and EEM all below their 5% quantiles);
  - the tail-dependence coefficient λ_L = 2·t_{ν+1}(−√((ν+1)(1−ρ)/(1+ρ)));
  - the difference in ES.
- Library: hand-rolled with scipy (preferred, explainable), or `copulae` as a cross-check.
- **Decision use:** quantifies how much ES rises when joint crashes are modelled. It links to risk deck slides 18–20 and EDGEFORGE slides 64–66.

### D. Macro and FX risk assessment

- **Stock-bond correlation regime:** a rolling 1-year correlation of SPY and AGG, plotted with CPI YoY. It shows the correlation turning positive when inflation is high, as in 2022. This explains why bonds failed as a hedge and justifies the GLD sleeve and the hypothetical scenario.
- **Inflation sensitivity:** regress monthly portfolio returns on CPI surprises (actual minus prior 12-month average). Report the real-return path of each candidate.
- **Rates sensitivity:** portfolio beta to ΔDGS10 (from Step 12's factor model), i.e. "+100 bp costs us X%".
- **USD/LKR (memo context):**
  - If the university's spending is in LKR, a USD portfolio's LKR value depends on the exchange rate.
  - Data: World Bank `PA.NUS.FCRF` (annual) or yfinance `LKR=X` (check its coverage).
  - Show historical LKR depreciation (including the 2022 Sri Lankan crisis): USD assets *gained* in LKR terms, a natural hedge for an LKR spender.
  - This is outside the mandate's USD risk measures; disclose it in the limitations.

## 4. Implementation plan

| # | File / function | Detail |
|---|---|---|
| A | `risk/regime.py::fit_markov(r)`, `filtered_probs`, `regime_risk(r, probs)` | Precompute in the pipeline |
| B | `portfolio/overlay.py::vol_target_backtest(returns, weights, garch_sigma, target, cap, cost)` | Uses the walk-forward engine |
| C | `risk/copula.py::fit_t_copula(u)`, `simulate_t_copula(R, nu, n, rng)`, `semi_parametric_marginals(...)`, `CopulaMCModel` (`RiskModel` protocol) | |
| D | `macro/analysis.py::rolling_stock_bond_corr`, `inflation_beta`, `rates_beta`, `lkr_context` | Page section in Stress or IPS |

## 5. Acceptance tests

- Markov: simulated 2-regime data recover the regime variances and transition probabilities within tolerance; filtered probabilities depend only on the past (a truncation test: probabilities up to t are unchanged when data after t are removed).
- Overlay: with target = ∞ it reproduces the static portfolio exactly.
- Copula: data simulated from a t-copula (ν = 5, ρ = 0.6) recover ν ∈ [3.5, 7] and ρ within ±0.05; the Gaussian copula gives λ_L ≈ 0.
- Macro: the rolling correlation helper matches a pandas `rolling().corr()` reference.

## 6. Pitfalls

- Smoothed regime probabilities (look-ahead).
- Overlay results reported without costs or without the 2022 failure case.
- A copula fitted on raw returns instead of pseudo-observations.
- Adding extensions that never feed a decision. Each must change or confirm something in Step 13 (limits, sizing or governance triggers).

## 7. Defend it in Q&A

- *"Did the regime model add value?"* Yes or no, with evidence: conditional ES in the high-vol regime is X× calm, and we use the regime probability as a governance trigger, not as a trading signal.
- *"Does your overlay work?"* It reduced GFC and COVID drawdowns by X pp after costs, but did not help in 2022 because bonds fell with equities. So it is a supplement, not a substitute, for the strategic allocation.
- *"Why a t-copula?"* The Gaussian copula has zero tail dependence. The t-copula captures joint crashes and raised our ES by X%. This is the "correlation is not a tail contract" point.
