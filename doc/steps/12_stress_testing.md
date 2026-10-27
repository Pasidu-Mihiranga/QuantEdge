# Step 12: Stress Testing (Historical, Hypothetical, Reverse)

**Owner:** V · **Week:** 3 (Days 2–4) · **Effort:** 3 days · **Depends on:** 04, 07 · **Feeds:** 13, 15, 17

## 1. Target

- Portfolio impact for **all 7 candidates** under:
  - three historical crises (GFC 2008, COVID March 2020, the 2022 rate-hike drawdown), replayed on actual ETF return paths;
  - one **team-designed hypothetical scenario**, driven by macro factors estimated from data;
  - a **reverse stress test** (the most plausible shock that breaches the IPS drawdown limit);
  - a **stressed-correlation VaR**.
- Per-asset loss attribution, recovery time, and an interactive scenario builder in the app.

## 2. Why it matters

- Brief §8.6: apply historical crisis paths for 2008, March 2020 and the 2022 rate-hiking drawdown, plus **one hypothetical scenario** the team designs, and report the portfolio impact.
- Brief §4: "portfolio robustness under stress scenarios", "resilience during market crises" and "what can go wrong".
- Rubric: decision-making (30%). Stress results usually decide whether the verdict is accept or adjust.
- **Key narrative:** in 2022, AGG fell roughly 13% at the same time as equities. Bonds failed as a hedge (the stock-bond correlation turned positive). This is the biggest threat to a "conservative = bond-heavy" portfolio and must be confronted explicitly.

## 3. How to achieve it

### 3.1 Historical scenarios (dates defined on S&P 500 peak to trough; all in `config.yaml → stress:`)

| Scenario | Start | End | Rationale |
|---|---|---|---|
| GFC | 2007-10-09 | 2009-03-09 | S&P 500 peak to trough |
| COVID crash | 2020-02-19 | 2020-03-23 | Fastest bear market on record |
| 2022 rate shock | 2022-01-03 | 2022-10-12 | Fed hiking cycle; stocks and bonds fell together |

Metrics per scenario and portfolio (buy-and-hold within the window, starting from target weights):
- cumulative return and USD loss on $10M;
- maximum drawdown within the window;
- worst single day;
- volatility in the window versus normal times;
- **days to recover** to the pre-crisis peak, after the window;
- **per-asset contribution** (w_i × cumulative asset return, so the contributions sum to the total).

Show the drawdown path chart (portfolio versus 60/40 versus equal weight) for each scenario.

### 3.2 Hypothetical scenario: "Stagflation and correlation breakdown"

**Narrative:** an inflation re-acceleration forces renewed hikes. Long yields +150 bp, oil +40%, equities sell off, the USD strengthens, credit spreads widen, and stocks and bonds fall together (as in 2022, but deeper).

**Factor model (data-driven, defensible):**
1. Factors (weekly changes, to reduce asynchronous noise): ΔDGS10 (bp), Δln(oil), ΔVIX, Δln(USD index), ΔHY spread (bp).
2. Regress each ETF's weekly return on the factors, using OLS with HAC errors over the full sample **and** over a stress sub-sample. This gives betas B (7 × 5).
3. Shock vector f*: ΔDGS10 = +150 bp, oil = +40%, VIX → 45 (Δ ≈ +25), USD = +8%, HY = +300 bp.
4. ETF scenario returns R* = B f*. Cross-check AGG against the duration approximation −D·Δy (D ≈ 6, so about −9%). If they differ materially, discuss why (convexity, spread component).
5. Add an **uncertainty band** from the betas' standard errors.

**Sliders in the app** let the committee vary each factor shock live: the "scenario builder".

**MiroFish link (Steps 19–20):** the stagflation scenario is also run as MiroFish scenario B2. Both designs (analyst = variant A, MiroFish = variant B) use the **same** translation machinery: signed historical factor quantiles, then these betas, then stressed Σ. Step 20's pre-registered with/without scorecard decides which design becomes our official team-designed hypothetical. Build `factor.py` and `stressed_cov.py` as reusable functions, because `behavioral/translate.py` calls them.

### 3.3 Reverse stress test (closed form; elegant and defensible)

Question: "what is the **most plausible** set of asset returns that would cause a loss of L* (the IPS drawdown limit)?"

- Minimise the Mahalanobis distance xᵀΣ⁻¹x subject to wᵀx = −L*.
- Solution: x* = −L* · Σw / (wᵀΣw).
- Plausibility: d² = L*² / (wᵀΣw), which is χ²(n) under Normality and gives an implied probability.
- Repeat with the **stressed Σ** (estimated from crisis windows only) and compare. Under stress correlations the breaching scenario becomes much more plausible.
- Present it as: "To lose 20%, the most likely path is SPY −x%, AGG −y%, … and is a 1-in-N-years event under calm correlations, but 1-in-M under crisis correlations."

### 3.4 Stressed-correlation VaR

- Re-estimate Σ_stress from the union of the three crisis windows.
- Compute parametric and MC VaR and ES with Σ_stress at the recommended weights, and compare with calm Σ. This quantifies the "diversification disappears in crises" point from risk deck slide 3 and EDGEFORGE slide 50.

### 3.5 What-if comparisons for the decision

- Run all stresses for each candidate. The decision engine (Step 13) uses the worst stress loss against the IPS limit.
- Show how much the worst stress loss falls when equity is reduced by 5% (sensitivity).

## 4. Implementation plan

| # | File / function | Detail |
|---|---|---|
| 1 | `stress/historical.py::replay(returns, weights, start, end) -> ScenarioResult` | Contributions, drawdown, recovery |
| 2 | `stress/factor.py::estimate_factor_betas(etf_weekly, factors_weekly, sample="full"/"stress") -> BetaResult` | HAC |
| 3 | `stress/hypothetical.py::apply_shock(betas, shock, weights, nav) -> ScenarioResult` with an SE band | |
| 4 | `stress/reverse.py::most_likely_breach(Sigma, w, L_star) -> (x_star, d2, prob, years)` | |
| 5 | `stress/stressed_cov.py::stressed_sigma(returns, windows)` | |
| 6 | `stress/report.py::stress_matrix(candidates, scenarios)` | Portfolio × scenario loss table |
| 7 | App: `pages/7_Stress_Testing.py` with tabs Historical, Hypothetical (sliders), Reverse, Stressed correlation | |

## 5. Acceptance tests

- **Replay:** contributions sum to the total return within 1e-10. A one-asset portfolio's replay equals the asset's own cumulative return.
- **Factor model:** simulated data with known betas are recovered within their standard errors.
- **Reverse stress:** wᵀx* = −L* exactly, and x* minimises the Mahalanobis distance (check against random feasible x values).
- **Sanity against reality:** SPY loss in the GFC window ≈ −55% (adjusted); AGG 2022 ≈ −13 to −15% in the window. If not, investigate the data.
- The scenario dates in config match the brief's crisis names.

## 6. Pitfalls

- Using daily returns of only the worst day as "the 2008 scenario". The brief asks for crisis **paths**.
- A hypothetical scenario with invented ETF returns and no linkage. Judges will ask "where did −25% come from?" The factor model answers this.
- Forgetting that the portfolio drifts during a crisis. Buy-and-hold inside the window is realistic; say so.
- Not discussing 2022 bond losses, which is the most relevant lesson for a conservative investor.

## 7. Defend it in Q&A

- *"Why did your 'safe' portfolio lose money in 2022?"* Bonds and stocks fell together when inflation forced rate hikes. Our hypothetical scenario stresses exactly that regime. The recommended portfolio's GLD sleeve and AGG cap limited the loss to X%, versus Y% for 60/40.
- *"How did you pick the hypothetical shocks?"* The magnitudes are anchored on historical extremes (2022: +240 bp in 10-year yields; 2008: HY +1,500 bp). They are transmitted through factor betas estimated from data, with standard-error bands.
- *"What would break the portfolio?"* The reverse stress test answers this: the most plausible path to a 20% loss, and how likely it is under calm versus crisis correlations.
