# Step 10: Extreme Value Theory (Layer 4)

**Owner:** R · **Week:** 2 (Days 3–5) · **Effort:** 3 days · **Depends on:** 08 · **Feeds:** 11, 13, 15

## 1. Target

- Peaks-over-threshold (POT) / Generalised Pareto Distribution (GPD) tail model of portfolio losses, with a **justified, diagnostic-driven threshold** and a comparison of **two threshold rules**.
- EVT-based VaR and ES at 90/95/99/99.5/99.9%, with **confidence intervals**.
- **Conditional EVT** (McNeil-Frey, GARCH-filtered), used in backtesting.
- "Return-level" communication: the **once-in-10-years daily loss** in USD.
- An EVT Diagnostics page with all supporting plots.

## 2. Why it matters

- Brief §8.4: explore advanced methods for extreme downside; evaluate performance under stress; show the limits of conventional measures; "**threshold selection in EVT must be justified, not chosen arbitrarily**".
- Rubric: innovation (15%) explicitly lists "alternative EVT threshold rules"; technical rigour (25%).
- Risk deck slides 15–17 and EDGEFORGE slide 63: POT logic, GPD shape ξ, threshold by diagnostics, and wide uncertainty at extreme quantiles.

## 3. How to achieve it

### 3.1 Data

- Positive daily portfolio losses ℓ_t = −R_p,t, using the risk series at the recommended weights (Step 04).
- Estimation sample: the full clean history (about 5,000 days). Show results for the walk-forward window as well.

### 3.2 GPD fit by maximum likelihood (hand-rolled, cross-checked)

- Exceedances: y = ℓ − u for ℓ > u, giving N_u of them.
- Negative log-likelihood for ξ ≠ 0: N_u ln β + (1 + 1/ξ) Σ ln(1 + ξy/β), subject to β > 0 and 1 + ξy/β > 0.
- Optimise with `scipy.optimize.minimize` (Nelder-Mead, then L-BFGS-B).
- Starting values come from probability-weighted moments.
- Cross-check against `scipy.stats.genpareto.fit(y, floc=0)` and against `pyextremes`.

### 3.3 Threshold selection: the core of the marks

Candidate thresholds are the 85.0, 87.5, 90, 92.5, 95 and 97.5% quantiles of losses, plus a fine grid for the plots.

| Diagnostic | What we look for |
|---|---|
| **Mean-excess plot** e(u) = E[ℓ−u \| ℓ>u] | Approximately **linear** above the right u (slope ξ/(1−ξ) > 0 means a heavy tail) |
| **Parameter-stability plots** of ξ̂(u) and the modified scale β* = β̂ − ξ̂u, with 95% confidence intervals | Above the right u, both are roughly **constant** within their confidence intervals |
| **Hill plot** (complementary ξ estimate) | Plateau region consistent with the GPD ξ |
| N_u | ≥ 50 exceedances, so the variance is acceptable |
| Goodness of fit | Anderson-Darling and Kolmogorov-Smirnov with **parametric-bootstrap p-values** (B = 200: fit, simulate, refit), plus QQ and PP plots |

- **Rule A (diagnostic rule, primary):** the lowest candidate u that lies in the region where ξ̂ is stable (its confidence interval overlaps the confidence intervals at all higher thresholds), has N_u ≥ 50 and an AD bootstrap p > 0.10. Lower u means more data and less variance; stability guards against bias. This is the **bias-variance trade-off**; say it in those words.
- **Rule B (automated, alternative):** ForwardStop sequential testing (Bader, Yan & Zhang, 2018). Test the ordered thresholds from low to high with AD p-values and choose the first threshold after which rejections stop, controlling the false discovery rate at 10%.
- **Rule C (naive benchmark):** a fixed 95% quantile. It is shown only to quantify how much the conclusion depends on the rule.
- **Partition rule (Step 22):** the threshold *rule* (A, B or C) is designed on development data and chosen on validation (≤ 2022-12-31). After the freeze, the frozen rule is applied mechanically to new windows; it is never re-chosen on 2023+ results.
- Present the **sensitivity table**: u, N_u, ξ̂ ± CI, β̂, VaR99, ES99 and VaR99.9 for each rule. If the rules agree, the conclusion is robust. If not, discuss the discrepancy openly.

### 3.4 Tail estimates

- `VaR_p = u + (β/ξ)[((n/N_u)(1−p))^(−ξ) − 1]`
- `ES_p = VaR_p/(1−ξ) + (β − ξu)/(1−ξ)`, valid for ξ < 1. Guard: if ξ ≥ 1, ES is infinite; raise a flag.
- **Confidence intervals:** profile likelihood for ξ (a χ²₁ drop of 1.92), and a parametric bootstrap for VaR and ES (B = 500).
- **Return level:** the 1-in-10-years daily loss is VaR at p = 1 − 1/(252×10) ≈ 99.96%. Report it in USD with its confidence interval. Committees understand "once in a decade" better than "99.96%".
- **Cross-check:** a block-maxima GEV on monthly maxima, giving a 10-year return level for comparison (optional).

### 3.5 Conditional EVT (McNeil & Frey, 2000), the model used in the backtest

1. Fit GARCH(1,1) with t innovations to the portfolio returns (as in Step 08).
2. Standardised residuals z_t = (r_t − μ)/σ_t are approximately i.i.d., which satisfies the EVT assumption.
3. Fit the GPD to the upper tail of −z, with the threshold chosen by Rule A on z (or a fixed 90% of z for walk-forward speed, justified by the static analysis).
4. VaR_{t+1} = −μ + σ_{t+1}·VaR_z,p and ES_{t+1} = −μ + σ_{t+1}·ES_z,p.

This removes volatility clustering, which violates the i.i.d. assumption of unconditional POT, and makes EVT responsive in crises.

### 3.6 Stress performance (brief: "how approaches perform under stressed conditions")

- Compare Normal, HS, unconditional EVT and conditional EVT on the GFC, COVID and 2022 sub-periods: exception counts and the size of exceedances.
- Show that Normal VaR is breached far more often and by larger amounts in stress windows.

## 4. Implementation plan

| # | File / function | Detail |
|---|---|---|
| 1 | `risk/evt.py::fit_gpd(y) -> GPDFit(xi, beta, nll, cov)` | MLE plus observed-information covariance |
| 2 | `profile_ci_xi(y, level=0.95)` | |
| 3 | `mean_excess(losses, grid)`, `stability(losses, grid)`, `hill(losses, k_grid)` | For the plots |
| 4 | `gof_bootstrap(y, fit, B=200, rng)` | AD and KS p-values |
| 5 | `select_threshold_diagnostic(...)`, `select_threshold_forwardstop(...)`, `select_threshold_fixed(q)` | Return `ThresholdChoice(u, rule, N_u, evidence)` |
| 6 | `evt_var(u, fit, n, N_u, p)`, `evt_es(...)`, `bootstrap_ci_var_es(...)`, `return_level(years)` | |
| 7 | `EVTModel(rule)` and `ConditionalEVTModel` implementing the `RiskModel` protocol | Step 08 interface |
| 8 | Precompute all diagnostics into `evt_diagnostics.parquet` (the bootstrap is slow) | Used by the app |

## 5. Acceptance tests

- Simulated GPD(ξ = 0.25, β = 1) with 5,000 points: estimates of ξ and β within 2 standard errors, and the profile confidence interval covers the truth in about 95% of 200 replications.
- Simulated Student-t with ν = 4 (true tail index ξ = 1/ν = 0.25): above a high threshold ξ̂ ≈ 0.25, and the stability plot is flat.
- EVT VaR at p = u's own quantile equals u (continuity check).
- EVT ES > EVT VaR; ES is infinite or flagged when ξ ≥ 1.
- The hand-rolled MLE agrees with `scipy.stats.genpareto.fit` to 1e-4.

## 6. Pitfalls

- Choosing u = the 95% quantile "because everyone does". **This is explicitly penalised.**
- Fitting the GPD to all ℓ instead of the exceedances ℓ − u.
- Applying unconditional POT to clustered data without acknowledgement. Use conditional EVT or declustering.
- Reporting a 99.9% VaR without confidence intervals; it rests on a handful of points.
- Interpreting ξ = 0.2 as "a 20% crash probability" (risk deck slide 17 warns against this).

## 7. Defend it in Q&A

- *"How did you choose the threshold?"* By the bias-variance trade-off: the lowest u where the mean-excess plot is linear and ξ is stable, with N_u ≥ 50 and the goodness-of-fit not rejected. An independent automated rule (ForwardStop) chose u′; both give similar VaR99 (table).
- *"What does ξ = 0.2 mean?"* The loss tail decays like a power law with tail index 1/ξ = 5. Extremes are more likely than under a Normal; moments above the 5th do not exist.
- *"Why is EVT VaR99 close to HS VaR99?"* At 99% there is still data, so the models agree. EVT's value appears at 99.5–99.9% and in return levels, where HS runs out of observations and Normal understates.
- *"What are EVT's limits?"* Few data points, wide confidence intervals, an assumption that the tail is stable over time, and it is univariate on the portfolio (no joint-crash structure; see the copula work in Step 14).
