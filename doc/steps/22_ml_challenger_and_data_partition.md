# Step 22: Leakage-Safe Data Partition & ML Challengers (LightGBM, Linear QR)

**Owner:** R (lead), D (partition, features, leakage tests), V (scoring and adoption) · **Week:** 2 (Days 3–5, foundations) → 3 (models, evaluation) → G3 freeze → 4 (Day 1, final test) · **Depends on:** 04, 07, 08, 11 · **Feeds:** 13, 15, 17, 18, 23, 21 (Paper B)

---

## 1. Target

- A **chronological partition**, enforced in code, that sits **on top of** walk-forward backtesting rather than replacing it.
- A **locked final-test period** that no one sees until the methodology is frozen by a git tag.
- One carefully scoped custom ML model, **LightGBM quantile regression** for 1-day portfolio VaR. It acts as a **challenger** to the best conventional model (the champion from Step 11), with a **linear quantile regression** baseline on the same features. Step 23 adds the LSTM deep challenger on the same framework.
- A **pre-declared adoption rule** based on one primary metric, so the ML model either earns its place or is reported honestly as not adding value.

Core principle: **don't replace walk-forward testing with ordinary splits; combine them.**

## 2. Why it matters

- **Credibility:** every later model comparison is only as good as its leakage controls. Weight leakage, test-set peeking and full-sample scaling are the three ways ML risk studies quietly cheat.
- **Brief §8.5:** "A risk model that has not been tested against reality is an opinion." A frozen, once-only test is the strongest form of that test.
- **Rubric:** innovation (a measured ML challenger) plus rigour (a pre-declared rule, uncertainty reported).
- **Publication:** this protocol is the backbone of Paper B (Step 21).

## 3. How to achieve it

### 3.1 The partition

| Period | Dates | Use |
|---|---|---|
| Development | 2004-11-18 → 2018-12-31 | Features, fitting, model design; design of the cleaning, EVT-threshold and IPS rules |
| Validation | 2019-01-01 → 2022-12-31 | Walk-forward selection and tuning (contains COVID and the 2022 rate shock) |
| Final test | 2023-01-01 → snapshot | **Locked.** Evaluated **once**, after the freeze; no retuning |

- **Walk-forward runs inside validation and test:** every forecast for day t is fitted on data ≤ t−1 (Step 11). The partition only decides *which decisions* may look at *which period*.
- **Every selection decision uses data up to 2022-12-31 only:**
  - Step 05 IPS calibration;
  - Step 07 portfolio scorecard;
  - Step 10 EVT threshold rule;
  - Step 11 champion choice;
  - this step's hyperparameters and adoption.

### 3.2 Fix 1: point-in-time weights (no weight leakage)

The ML target is the next-day loss of the portfolio, so the weights in that loss must be the weights the endowment would actually have held.

- `portfolio/weights_path.py` produces **w_τ(t)**: the weights fixed at the most recent quarterly rebalance τ ≤ t. Each rebalance optimises on data ≤ τ only, reusing the Step 07 walk-forward (`walk_forward(...).weights_history`).
- **Target:** ℓ_{t+1} = −w_τ(t)ᵀ r_{t+1}.
- **Return features** are **pro-forma** returns of the *current* weights, w_τ(t)ᵀ r_s for s ≤ t. This is valid because the weights are known at t, and it is how a risk desk measures the current book.
- **Before the first rebalance** (the 756-day warm-up), use **pre-declared fixed strategic weights** (the 60/40 benchmark mapping). Never use optimised weights there.
- This replaces Step 11's v1 assumption of "target weights held constant" for every risk target. The constant-weight backtest is kept only as a labelled sensitivity.

### 3.3 Fix 2: a test set that is genuinely untouched

- **Loader guard:** `load_returns(split="dev" | "val" | "test" | "all")`.
  - `"test"` and `"all"` raise `TestLockedError` unless the git tag `methodology-freeze-v1` exists (checked with `git tag --list methodology-freeze-v1`).
  - Every analysis function calls the loader; there is no other path to the data.
- **What is allowed before the freeze:**
  - mechanical cleaning on all dates (missing values, stale prices, splits), with no performance or risk statistics;
  - everything on dev and val.
- **What is forbidden before the freeze:** full-history charts, KPIs, VaR or backtests that include 2023 onwards. The app shows the test period as a grey "locked" band until the tag exists. This replaces the v1 idea of "exploratory full-history" charts.
- **Freeze record** `doc/decisions/methodology_freeze.md`, committed together with the tag. It contains:

  | Item | Content |
  |---|---|
  | Tag | `methodology-freeze-v1`, commit SHA, date |
  | Config | SHA-256 of `config.yaml` |
  | Data | SHA-256 of the snapshot manifest |
  | Environment | SHA-256 of `requirements.txt` and `requirements-research.txt`; Python version |
  | Models | Artefact hashes, final hyperparameters, seeds |
  | Line-up | Champion and the challenger list |
  | Rule | SHA-256 of the adoption-rule text (§3.8) |

- **After the freeze:**
  - The final-test script runs once (`backtest/final_test.py`, tag-gated).
  - A **production refit** on all data with the frozen methodology is then allowed; it produces today's recommendation.
  - Any change after the tag is logged in the freeze record as a **post-hoc deviation**, with its reason.

### 3.4 Fix 3: low tail power, reported honestly

The validation period has about 1,000 trading days, so a correct 99% VaR gives only about 10 exceptions. The test period is similar, and it contains no major crisis.

- Every exception count carries a **Clopper–Pearson 95% interval** for the exception rate.
- **95% VaR results are always shown next to 99%.**
- `power_kupiec(n, p0, p1)` reports the probability that Kupiec rejects a model whose true exception rate is p1.
  - At n ≈ 1,000, the power to detect a doubled 99% rate (p1 = 2%) is only about 0.8.
  - At n = 250 it is far lower.
  - Show the curve on the Model Arena tab.
- **Wording rule:** "not rejected" never becomes "validated". Use "no evidence of miscalibration at this sample size".
- Paper B adds power by pooling over a panel of 30 portfolios (Step 21).

### 3.5 Fix 4: Basel traffic light done correctly

- The canonical zones (0–4 green, 5–9 yellow, ≥ 10 red) apply **only to 250 observations at 99%**.
- Report **rolling 250-day windows**: the share of windows in each zone, plus the worst window and its dates.
- For any other sample length n, use **binomial cut-offs**:
  - green if P(X ≤ x | n, 1%) < 0.95;
  - red if P(X ≤ x | n, 1%) ≥ 0.9999;
  - yellow otherwise.

  Label these as a "Basel-style generalisation".
- Unit test: n = 250 reproduces the 4/9 cut-offs.

### 3.6 LightGBM quantile model

| Item | Specification |
|---|---|
| Target | ℓ_{t+1} at w_τ(t) (§3.2) |
| Quantiles | Separate models at 90, 95 and 99% (`objective="quantile"`, `alpha=q`) |
| Crossing | Monotone feature constraints do **not** stop the 90/95/99 predictions from crossing. **Monotone rearrangement** (Chernozhukov, Fernández-Val & Galichon, 2010; sort the predicted quantiles) is **mandatory** post-processing, and the number of corrections is logged |
| Training | Expanding window; retrain every 21 trading days inside the walk-forward; early stopping on the last 20% of each training window (time-ordered, never shuffled) |
| Tuning | Small grid on **validation only**: `num_leaves` ∈ {7, 15}, `min_data_in_leaf` ∈ {50, 100}, `learning_rate` 0.03, `n_estimators` ≤ 500, `feature_fraction` 0.8. That is 4 configurations, chosen once |
| Monotonicity | `monotone_constraints = +1` on every volatility feature (higher volatility never lowers VaR) |
| Explainability | SHAP values from LightGBM's built-in `pred_contrib=True` (no extra dependency): a global importance bar and a crisis-day waterfall |

**Features** (all known at t, all lag-tested; scaling statistics come from the training window only):

| Group | Features |
|---|---|
| Returns | Pro-forma portfolio returns r_t … r_{t−4} |
| Volatility | Realised volatility (5, 20, 60 days); EWMA volatility (λ = 0.94); 20-day downside semivolatility |
| Econometric | **GARCH(1,1)-t σ_{t+1\|t}** (hybrid stacking: the tree corrects the econometric forecast) |
| Market | VIX level and 5-day change; Δ10-year yield; Δ high-yield spread |
| Dependence | 60-day average pairwise correlation; 60-day SPY–AGG correlation |
| Drawdown | Distance from the 252-day high |

FRED series published with a delay are lagged by one extra day (Step 03 rule).

### 3.7 Fix 5: ML Expected Shortfall, guarded and compared

| Variant | Definition | Guards |
|---|---|---|
| **(a) Ratio hybrid** | ES = VaR_ML × ES_EVT,t / VaR_EVT,t (conditional EVT from Step 10) | Apply only when VaR_EVT > ε (ε = 1e-4); clip the ratio to [1, 2.5]; enforce ES ≥ VaR > 0 in loss units; log every guard hit and report the hit rate |
| **(b) Quantile integral** | Mean of rearranged LightGBM quantiles at 97.5, 98, 98.5, 99, 99.25, 99.5 and 99.75% (approximates ES_97.5 = mean tail quantile) | Same ES ≥ VaR check |
| **(c) Joint FZ0-trained ES** | From the LSTM (Step 23) | ES ≥ VaR by construction |

- All variants are compared with:
  - the **FZ0 joint loss**;
  - **Acerbi–Szekely Z2**;
  - the **McNeil–Frey exceedance-residual test**.
- **FZ0 sign convention:** FZ0 is defined on returns, with VaR and ES as negative return quantities. `scoring.py` converts from our positive-loss convention in one place, and documents it in the docstring.

### 3.8 Fix 6: simple, pre-declared adoption rule

| Component | Definition |
|---|---|
| **Primary metric** | 99% pinball (quantile) loss, averaged over the validation walk-forward |
| **Secondary requirements** | 1. FZ0 non-inferior to the champion (at most 2% worse)<br>2. Kupiec and Christoffersen CC not rejected at 5%<br>3. No red rolling-250 window |
| **Uncertainty evidence** (reported, not a gate) | Diebold–Mariano (HAC) against the champion, **Holm-corrected** across the 3 challengers (LightGBM, LSTM, linear QR); membership of the 90% Model Confidence Set (`arch.bootstrap.MCS`) |

**Decision:**
- **ADOPT** as the new champion only if:
  1. it has the lowest primary loss on validation; and
  2. it meets all the secondary requirements; and
  3. on the **final test, without retuning**, its primary loss is no more than 2% worse than the champion's.
- **CHALLENGER-ONLY:** conditions 1 and 2 hold, but condition 3 fails.
- **REJECT:** otherwise.

Whatever the outcome, report whether adoption changes the Step 13 verdict. The rule text is hashed into the freeze record.

## 4. Implementation plan

### 4.1 Milestones (build the foundations before any model is trained)

| M | Deliverable | When / gate |
|---|---|---|
| **M1** | `data/partition.py`, `TestLockedError` guard, `portfolio/weights_path.py`, `ml/features.py`, **leakage-test suite** | Week 2, Days 3–5 (must pass before any training) |
| **M2** | `backtest/scoring.py`: pinball, FZ0, DM (HAC), MCS wrapper, binomial Basel, rolling-250 zones, Clopper–Pearson, `power_kupiec`; hand-calculated tests | G2 |
| M3 | `ml/linear_qr.py` baseline | Week 3, Day 1 |
| M4 | `ml/quantile_lgbm.py` with rearrangement and ES variants (a) and (b) | Week 3, Day 2 |
| M5 | `ml/lstm_quantile.py` (Step 23) | Week 3, Days 1–4 (time-boxed) |
| M6 | Validation report, adoption decision, freeze record and tag | G3 |
| M7 | `backtest/final_test.py`, run once | Week 4, Day 1 |

Note: `weights_path.py` needs the Step 07 walk-forward. Until that exists, M1 uses the fixed 60/40 path, and the tests run on both paths.

### 4.2 Files and functions

| File / function | Detail |
|---|---|
| `data/partition.py::Partition`, `split_of(date)`, `load_returns(split)` | Dates from `config.partition`; `TestLockedError` check |
| `portfolio/weights_path.py::point_in_time_weights(wf_result, dates, warmup_weights)` | Forward-fills the rebalance weights; asserts that each τ uses data ≤ τ |
| `ml/features.py::build_features(prices, macro, weights_path) -> DataFrame` | Every feature at row t uses data ≤ t; FRED lag rule |
| `ml/linear_qr.py::LinearQRModel` | statsmodels `QuantReg`, one fit per quantile, same rearrangement |
| `ml/quantile_lgbm.py::LGBMQuantileModel` | Implements the Step 08 `RiskModel` protocol, so the Step 11 engine runs it unchanged |
| `ml/rearrange.py::rearrange(q_preds)` | Sorts the quantile vector row-wise; returns the number of fixes |
| `ml/es_variants.py::ratio_es(...)`, `integral_es(...)` | Guards from §3.7 |
| `backtest/scoring.py` | `pinball`, `fz0`, `dm_test`, `mcs`, `basel_binomial`, `rolling_basel`, `clopper_pearson`, `power_kupiec` |
| `backtest/arena.py::run_arena(models, split="val")` | Loss table, DM/MCS, adoption decision → `data/artifacts/arena_val.parquet` |
| `backtest/final_test.py` | Tag-gated; writes `arena_test.parquet` and appends to the freeze record |
| `config.yaml` → `partition:`, `ml:` | See Step 01 |

## 5. Acceptance tests (leakage tests first)

- **Lag-shift invariance:** replace every value after t with noise; the features at t are unchanged.
- **Weight-path invariance:** perturb all returns after τ; w_τ is unchanged.
- **Partition guard:** `load_returns("test")` raises `TestLockedError` without the tag, and succeeds once a temporary repo has the tag.
- **No full-sample scaling:** the scaler fitted on a window equals the scaler fitted on the same window inside a longer series.
- **Quantile calibration:** on simulated heteroskedastic data (GARCH-t), LightGBM 95% coverage lies within the binomial 95% band.
- **Rearrangement:** after post-processing, q90 ≤ q95 ≤ q99 on every row.
- **Scoring:** pinball and FZ0 match hand calculations on a 5-row example; DM on two identical forecasts gives a statistic of 0.
- **Basel:** the binomial cut-offs at n = 250 are 4 and 9.
- **Power:** `power_kupiec(1000, 0.01, 0.01)` is about 0.05 (size).
- **ES guards:** a near-zero VaR_EVT triggers the fallback, and ES ≥ VaR always holds.

## 6. Pitfalls

- Random K-fold or shuffled early-stopping sets on time series.
- Tuning on 2020/2022 *after* seeing 2023+ numbers. That is what the tag prevents.
- Scaling features with full-sample means or standard deviations.
- Building the target with today's optimised weights applied to history (weight leakage).
- Too few tail observations: about 35 at 99% in dev. Do not over-tune the 99% model.
- Saying "ML is better" from one lower loss number, without DM/MCS and the power caveat.
- Trusting monotone constraints to stop quantile crossing (they don't).

## 7. Defend it in Q&A

- *"Why not a normal train/test split?"* Random splits leak the future in time series. We combine a chronological partition (to decide *what* may be tuned on *which* period) with walk-forward forecasting (to make every forecast genuinely out-of-sample).
- *"Is your ML better than GARCH?"* We pre-declared one primary metric and a non-inferiority rule, and we show the DM/MCS uncertainty. The answer is whatever the frozen test says, and it is reported either way.
- *"Did your COVID/2022 tuning leak into the test?"* No. 2020 and 2022 are in validation. The test period (2023 onwards) was locked in code until the freeze tag; the freeze record has the hashes.
- *"How do your weights avoid look-ahead?"* Each historical target uses the weights from the preceding rebalance, which was optimised only on data up to that date. A unit test perturbs the future and checks that the weights don't move.
- *"Only about 10 exceptions: how can you conclude anything?"* We can't conclude much at 99% alone, and we say so: confidence intervals, power curves and 95% results are reported side by side.
