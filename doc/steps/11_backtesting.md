# Step 11: Backtesting & Model Validation (Layer 5)

**Owner:** V · **Week:** 3 (Days 1–3) · **Effort:** 3 days · **Depends on:** 08, 09, 10 · **Feeds:** 13, 15

## 1. Target

- A **strictly out-of-sample**, walk-forward VaR (and ES) forecast series for every model, over a user-selectable date range.
- For each model and each α in {90, 95, 99}%:
  - exception counts;
  - **Kupiec POF**;
  - **Christoffersen independence** and conditional coverage;
  - **Basel traffic light** (static and rolling);
  - (innovation) the **Acerbi-Szekely ES backtest**.
- A model-selection table that determines which VaR model the team "chooses", plus a per-crisis breakdown.

## 2. Why it matters

- Brief §8.5: "A risk model that has not been tested against reality is an opinion, not a measurement." Kupiec, Christoffersen and Basel traffic light are mandatory.
- Brief §6: the backtesting panel with a traffic-light indicator is a mandatory UI item, and the sidebar must set the backtest date range.
- EDGEFORGE slide 77: forecasts must use information strictly before each observation; Kupiec does not test clustering but Christoffersen does; Basel is calibrated for 99% over 250 observations.

## 3. How to achieve it

### 3.1 Walk-forward engine

```
for t in OOS dates (default 2008-01-02 → snapshot end):
    window = losses[t-W : t-1]               # W from sidebar, default 500
    if t is a refit day (every k=5 days for GARCH/EVT; every day for HS/Normal):
        model.fit(window)
    else:
        model.update_filter(r_{t-1})         # GARCH variance recursion only, no refit
    VaR_t(α), ES_t(α) = model.var(α), model.es(α)
    I_t = 1{ℓ_t > VaR_t}
```

- **Guarantee:** an assertion `window.index.max() < t` on every iteration, plus a unit test.
- Weights are the recommended portfolio's **target weights**, held constant. This answers "if we had held this policy, would the risk model have been right?" State this assumption. Optionally re-run with the walk-forward weights history from Step 07.
- Precompute into `data/artifacts/backtest_{model}_{W}.parquet`. The app slices by the sidebar date range and recomputes the tests live, which is cheap.

### 3.2 Kupiec POF test (unconditional coverage)

- p = 1 − α, T observations, x exceptions, p̂ = x/T.
- LR_POF = −2 ln[(1−p)^(T−x) p^x] + 2 ln[(1−p̂)^(T−x) p̂^x], which is χ²(1) under H0.
- Handle x = 0 (the second term is 0·ln 0 = 0).
- Report x, the expected count pT, p̂, LR and the p-value.

### 3.3 Christoffersen independence and conditional coverage

- Transition counts n_ij = #{I_{t−1} = i, I_t = j}.
- π₀₁ = n₀₁/(n₀₀ + n₀₁), π₁₁ = n₁₁/(n₁₀ + n₁₁), π = (n₀₁ + n₁₁)/(n₀₀ + n₀₁ + n₁₀ + n₁₁).
- LR_ind = −2 ln[(1−π)^(n₀₀+n₁₀) π^(n₀₁+n₁₁)] + 2 ln[(1−π₀₁)^n₀₀ π₀₁^n₀₁ (1−π₁₁)^n₁₀ π₁₁^n₁₁], which is χ²(1).
- LR_cc = LR_POF + LR_ind, which is χ²(2). (Use the same T−1 sample for the LR_POF term to keep the χ²(2) decomposition consistent.)
- Guard every 0·ln 0 term as 0. If n₁₀ + n₁₁ = 0 (no exceptions), the independence test is undefined: report it as "n/a".
- **Interpretation:** a rejection means exceptions cluster, so the model is slow to react to volatility regimes. This is the expected failure of HS and Normal in 2008 and 2020, and the reason GARCH-FHS and conditional EVT exist.

### 3.4 Basel traffic light

- **Canonical (α = 99%, 250 days):** green 0–4, yellow 5–9, red ≥ 10.
- Plus-factor table: 5 → +0.40, 6 → +0.50, 7 → +0.65, 8 → +0.75, 9 → +0.85, ≥ 10 → +1.00 (multiplier 3 + plus).
- Show the latest 250 days, and a **rolling 250-day traffic light through time** (coloured band chart). It shows *when* each model was red, e.g. Normal in 2008 and March 2020.
- **Other α or window lengths:** generalised zones from the binomial cumulative probability of observing ≤ x exceptions: green < 95%, yellow 95% to < 99.99%, red ≥ 99.99%. This reproduces the canonical table at 99% and 250 days (unit-tested). Label it clearly as **"Basel-style generalisation"**.

### 3.5 ES backtest (innovation): Acerbi-Szekely Z2

- With losses positive: Z2 = 1 − Σ_t ℓ_t I_t / (T(1−α) ES_t).
- E[Z2] = 0 under H0; Z2 < 0 means ES is underestimated.
- Critical values by **simulation under each model's own forecast distribution** (5,000 paths), giving a p-value.
- Run it at 97.5% (FRTB level).

### 3.6 Model-selection table

| Model | x / expected | Kupiec p | Ind. p | CC p | Basel zone | Z2 p | Verdict |
|---|---|---|---|---|---|---|---|

Selection rule (declared in advance): pass Kupiec and CC at 5%, green over the last 250 days, and the Z2 test not rejected. Among the passing models, prefer the simplest. If none pass, report that honestly and carry it into the decision engine (Step 13) as model risk, using the most conservative passing-ish model for limits.

### 3.7 Crisis breakdown

Exceptions and average exceedance size (ℓ − VaR) inside the GFC, COVID and 2022 windows, for every model. This links Layer 5 to the stress narrative.

## 4. Implementation plan

| # | File / function | Detail |
|---|---|---|
| 1 | `backtest/engine.py::walk_forward_var(model_factory, losses, W, alphas, refit_every, start, end) -> DataFrame[var_α, es_α, loss, I_α]` | Uses a progress bar; precomputed |
| 2 | `backtest/tests.py::kupiec(I, alpha)`, `christoffersen(I, alpha)`, `basel_zone(x, T, alpha)`, `basel_table_canonical()` | Pure functions returning dataclasses |
| 3 | `backtest/tests.py::rolling_basel(I, window=250)` | Zone series |
| 4 | `backtest/es_backtest.py::acerbi_szekely_z2(loss, var, es, alpha, sim_fn, n_sims)` | |
| 5 | `backtest/report.py::selection_table(results)` and `crisis_breakdown(results, windows)` | |
| 6 | `pipeline.py` entry: run all models × W ∈ {250, 500, 1000} × α | Store artifacts |

## 5. Acceptance tests

- **Kupiec:** a known example. T = 250, x = 6, p = 0.01: LR ≈ 3.55, p ≈ 0.06. The team reproduces the textbook value (Jorion) in the test.
- **Christoffersen:** a hand-constructed sequence with clustered exceptions (…0011100…) rejects independence; an evenly spread sequence does not.
- **Basel generalisation:** at α = 0.99 and T = 250 it reproduces green 0–4, yellow 5–9, red ≥ 10 exactly.
- **Calibration:** simulated i.i.d. Normal losses with a correct Normal model give Kupiec rejection rates of about 5% over 500 simulations (size test).
- **No look-ahead:** a mock model records the max index of each fit window and the test asserts it is less than t for every t.

## 6. Pitfalls

- Fitting the model once on the full sample and then "backtesting" it. That is in-sample, and it is the most serious rigour error possible.
- Applying the Basel 99% table to 95% VaR without adjustment.
- Reporting only Kupiec. Clustering is exactly the failure judges want discussed.
- Using smoothed GARCH or regime probabilities, which use future data. Use filtered estimates only.
- Treating "passes at 95%" as validation of 99%. Report each α separately.

## 7. Defend it in Q&A

- *"Is your backtest really out-of-sample?"* Yes. Every forecast for day t is fitted on data ending at t−1; a unit test enforces this.
- *"Your Normal VaR fails Christoffersen. What does that mean?"* Its exceptions cluster in crises; it reacts too slowly when volatility jumps. GARCH-FHS passes because it updates σ daily. This is why we chose it.
- *"Why does the Basel light only apply at 99%?"* The Basel Committee calibrated the zones on the binomial distribution for 99% over 250 days. For other levels we use the same binomial logic and label it as a generalisation.
