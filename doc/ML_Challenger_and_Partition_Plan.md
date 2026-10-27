# Plan v2: leakage-safe validation, ML challengers (LightGBM, linear QR, LSTM), and a publishable forecasting study

## Context

This is version 2 of the ML plan; version 1 is in commit 374f982. The detailed specifications are in [Step 22](steps/22_ml_challenger_and_data_partition.md) and [Step 23](steps/23_lstm_deep_challenger.md); this document summarises the design. This revision does three things:

1. **Applies six review fixes** from the external review:
   - point-in-time weights;
   - a test set that is genuinely untouched;
   - low tail power;
   - correct Basel thresholds;
   - a guarded ES estimator;
   - a simpler adoption rule.
2. **Adds an LSTM deep challenger.** The goal is a model that is accurate and defensible, and also worth publishing.
3. **Turns the champion–challenger comparison into a second publishable study (Paper B).** It does not depend on MiroFish, so it is the more reliable route to a paper.

Priority order (per the review): **financial engine → leakage foundations → ML validation → MiroFish (optional)**.

The next engineering milestone is `partition.py`, `features.py` and the leakage tests, built **before** any model is trained.

## Final methodology (to be stated identically in Step 22, master plan §4c and the README)

| Period | Dates | Use |
|---|---|---|
| Development | 2004-11-18 → 2018-12-31 | Features, fitting, model design, cleaning/EVT/IPS rule design |
| Validation | 2019-01-01 → 2022-12-31 | Walk-forward selection and tuning (contains COVID and 2022) |
| Final test | 2023-01-01 → snapshot | Locked; evaluated **once** after the freeze; no retuning |

| Role | Model |
|---|---|
| Primary champion | Best validated conventional model (HS / t / GARCH-FHS / conditional EVT / MC) |
| ML challenger | LightGBM quantile VaR |
| Deep challenger (new) | LSTM joint VaR/ES network |
| ML baseline | Linear quantile regression |
| Ablation (paper only) | MLP with the same head, to isolate the gain from recurrence |
| Portfolio strategy | Robust Mean-ES candidate |
| Innovation layer | MiroFish scenario comparison (optional, lowest priority) |

## Review fixes (become sections of Step 22)

### 1. Point-in-time weights (no weight leakage)

- Add `src/quantedge/portfolio/weights_path.py`. It produces w_τ(t), the weights fixed at the most recent quarterly rebalance τ ≤ t, where each rebalance optimises on data ≤ τ only (reusing the Step 07 walk-forward).
- **Target:** ℓ_{t+1} = −w_τ(t)ᵀ r_{t+1}.
- **Return features:** pro-forma returns of the *current* weights. This is valid because the weights are known at t.
- **Before the first rebalance** (lookback warm-up): use pre-declared fixed strategic weights (the 60/40 benchmark mapping), never optimised weights.
- **Test:** perturb all data after τ, then assert that w_τ is unchanged.

### 2. A test set that is genuinely untouched

- A loader guard, `load_returns(split="dev"|"val"|"test")`. Test access raises `TestLockedError` unless the git tag `methodology-freeze-v1` exists. The guard reads the tag through `git tag --list`.
- Until the freeze, the app and notebooks show no performance or risk statistics for 2023 onwards. This **replaces** the v1 plan's "exploratory full-history" charts.
- Mechanical cleaning may touch every date. Stationarity tests and every design look use development and validation only.
- **Freeze record** `doc/decisions/methodology_freeze.md`. It holds:
  - the tag SHA;
  - SHA-256 hashes of `config.yaml`, the data manifest and the lock/requirements files;
  - model artefact hashes and hyperparameters;
  - seeds;
  - the list of champions and challengers;
  - a hash of the adoption-rule text.
- After the freeze, a **production refit** on all data with the frozen methodology is allowed: it gives today's recommendation.

### 3. Low tail power

- Report exception counts with **Clopper–Pearson 95% CIs**.
- Always show 95% VaR next to 99%.
- Add a power function, `power_kupiec(n, p0, p1)`. At n ≈ 1,000 the power to detect a doubled 99% exception rate is only about 0.8, and much lower at n = 250.
- Wording rule: "not rejected" ≠ "validated".
- The paper's panel (below) adds power through pooling.

### 4. Basel traffic light done correctly

- The 0–4 / 5–9 / ≥10 zones apply only to **rolling 250-day windows**. Report the share of windows in each zone and the worst window.
- For any other length n, use binomial cut-offs: green if P(X ≤ x) < 0.95, red if P(X ≤ x) ≥ 0.9999.
- Unit test: n = 250 reproduces 4/9.

### 5. A guarded ML ES and a separately calibrated alternative

- **(a) Ratio hybrid** ES = VaR_ML × ES_EVT/VaR_EVT, with these guards:
  - apply it only when VaR_EVT > ε (ε = 1e-4);
  - clip the ratio to [1, 2.5];
  - enforce ES ≥ VaR > 0 in loss units;
  - log every guard hit.
- **(b) Quantile-integral ES:** the average of LightGBM quantiles at 97.5, 98, 98.5, 99, 99.25, 99.5 and 99.75, rearranged.
- **(c) LSTM joint ES:** trained directly with FZ0 (below).
- All three are compared on FZ0, Acerbi–Szekely Z2 and the McNeil–Frey exceedance-residual test.
- Sign convention: FZ0 is computed on returns (VaR, ES < 0) and documented once in `scoring.py`.

### 6. Simple, pre-declared adoption rule

- **Primary metric:** 99% pinball loss on validation.
- **Secondary requirements:**
  - FZ0 non-inferior to the champion (at most 2% worse);
  - Kupiec and Christoffersen CC not rejected at 5%;
  - no red rolling-250 window.
- **Uncertainty evidence** (reported, not a gate): DM tests with Holm correction across the 3 challengers (LightGBM, LSTM, linear QR); 90% MCS membership.
- **ADOPT:**
  1. lowest primary loss on validation;
  2. the secondary requirements pass;
  3. on the final test, without retuning, the primary loss is no worse than the champion's by more than 2%.
- **CHALLENGER-ONLY:** conditions 1 and 2 hold but condition 3 fails.
- **REJECT:** otherwise.
- The rule text is hashed into the freeze record.

**Quantile crossing:**
- LightGBM's monotone feature constraints do **not** prevent crossing, so Chernozhukov rearrangement post-processing is mandatory.
- The LSTM is non-crossing by construction.

## LSTM deep challenger (new Step 23)

- **Input:**
  - a sequence of the last L days (L ∈ {20, 60}) of the same feature set as LightGBM, plus pro-forma returns;
  - standardised with statistics from the **training window only** (refit at each retrain).
- **Architecture:**
  - one LSTM layer (hidden ∈ {16, 32}), dropout 0.2, then a dense head;
  - quantile outputs: q90, q95 = q90 + softplus(·), and q99 = q95 + softplus(·), so they never cross;
  - ES99 = q99 + softplus(·), so ES ≥ VaR.
- **Loss:** pinball at 90/95 plus **FZ0 for (VaR99, ES99) jointly**. This is the publishable angle: joint elicitable training rather than quantile-only.
- **Training:**
  - expanding window, retrained every 63 days;
  - early stopping on the last 20% of each training window (time-ordered);
  - weight decay ∈ {1e-4, 1e-3}, giving an 8-config grid tuned on validation only;
  - a **5-seed ensemble**, averaged (averaging keeps quantiles ordered);
  - deterministic torch flags.
- **Stack:**
  - PyTorch CPU in `requirements-research.txt`, **not** the app requirements;
  - predictions are precomputed to parquet, so Streamlit Cloud never imports torch.
- **Honesty guardrails:**
  - about 35 tail days in development, so data hunger is real;
  - mitigated by the panel training in Paper B;
  - if it under-performs, that is reported, not tuned away.
- **Time box:** Week 3, Days 1–4. If it slips, the LSTM is dropped from the competition submission and finished in post-competition Weeks 5–8 for Paper B. LightGBM and linear QR stay in the competition.

## ★ Paper B: "Do machine-learning models improve tail-risk forecasts for a conservative multi-asset endowment? A pre-registered champion–challenger study"

Paper B is added to Step 21 as a second track, independent of MiroFish.

- **Contributions:**
  1. A leakage-safe protocol: point-in-time weights, a hybrid partition with walk-forward, a hash-frozen test set.
  2. Joint VaR/ES evaluation (FZ0, MCS) comparing econometric, gradient-boosting and deep sequence models, including an FZ0-trained LSTM.
  3. A **panel of 30 portfolios** to fix the power problem:
     - the 7 single ETFs;
     - 60/40, GMV, ERC and Robust Mean-ES;
     - 19 seeded Dirichlet long-only portfolios.

     Models are pooled across the panel, and inference uses a date-clustered bootstrap.
  4. Regime analysis (VIX ≤ 30 vs > 30; crisis windows) plus SHAP explainability.
  5. Open code and a data recipe.
- **Pre-registration:** on OSF **before** the freeze tag. A null result ("ML does not beat GARCH-FHS") is still publishable when pre-registered.
- **Candidate venues** (check deadlines at Week 5): arXiv q-fin.RM preprint, then *Journal of Risk Model Validation*, *Risks*, *Journal of Risk and Financial Management*; *Finance Research Letters* as a stretch.
- **Honest novelty statement:** ML-versus-GARCH VaR comparisons already exist in the literature. The novelty here is the protocol, the joint ES training and evaluation, and the pooled-power design.

## Implementation milestones (written into Step 22 and the index)

| M | Deliverable | Gate |
|---|---|---|
| M1 | `data/partition.py`, test-lock guard, `portfolio/weights_path.py`, `ml/features.py` + **leakage tests**:<br>• lag-shift invariance;<br>• partition guard;<br>• weight-path future-perturbation;<br>• `TestLockedError` | before any model training (Week 2, Days 3–5) |
| M2 | `backtest/scoring.py`: pinball, FZ0, DM (HAC), MCS, binomial Basel, rolling-250 zones, Clopper–Pearson, `power_kupiec`; hand-calculated tests | G2 |
| M3 | `ml/linear_qr.py` baseline | Week 3, Day 1 |
| M4 | `ml/quantile_lgbm.py` (`RiskModel` protocol, rearrangement, ES variants a/b) | Week 3, Day 2 |
| M5 | `ml/lstm_quantile.py` (Step 23) | Week 3, Days 1–4, time-boxed |
| M6 | Validation report, adoption decision, freeze record + tag | G3 |
| M7 | `backtest/final_test.py`, run once | Week 4, Day 1 |

## Where the changes live (under `doc/`)

**New step files:**
- `steps/22_ml_challenger_and_data_partition.md`:
  - standard template;
  - partition and freeze;
  - fixes 1–6;
  - the LightGBM spec, linear QR and the ES variants;
  - milestones M1–M7;
  - tests, pitfalls and Q&A.
- `steps/23_lstm_deep_challenger.md`: spec above, tests, pitfalls, Q&A and the fallback.

**Changes to existing files:**

| File | Change |
|---|---|
| `steps/00_INDEX.md` | Rows 22 and 23; critical path `07 → 22(M1) → 08–11 → 22/23 → 13`; G2 = M1–M2 done; G3 = M6 + freeze tag; G4 = final test run once. Priority note: engine → ML → MiroFish. Cut order: LSTM moves to post-competition first, then MiroFish, then the existing list |
| `steps/01_project_setup.md` | `partition:` and `ml:` config blocks (dates, quantiles, ε, ratio clip, grids, seeds, retrain cadence); `lightgbm` in requirements; torch in `requirements-research.txt` |
| `steps/05`, `07`, `10` | "Partition rule" note: design on dev, select on val, 2023+ untouched until freeze |
| `steps/07` | Also: the walk-forward weight path is the single source of weights for every risk target |
| `steps/08_var.md` | Registry rows: LightGBM, LSTM, linear QR, marked "challenger, see Steps 22–23" |
| `steps/11_backtesting.md` | §3.0 partition × walk-forward; rolling-250 Basel + binomial cut-offs; CIs + power; scoring metrics; selection on validation only |
| `steps/15_pipeline_app.md` | Test-period hidden until tag; partition bands; "Model Arena" tab (loss table, DM/MCS, SHAP, adoption badge); app reads cached predictions only |
| `steps/16_testing_deployment.md` | The leakage-test suite from M1; CI runs it on every push |
| `steps/17_report_tearsheet.md` | Report §5 "Champion–challenger and final test" (0.5–1 page), including the power caveat |
| `steps/18_pitch_defence.md` | Q&A 38–43:<br>• split vs walk-forward;<br>• is ML better than GARCH?;<br>• did 2020/2022 tuning leak?;<br>• why so few tail observations?;<br>• why an LSTM, and is it overfit?;<br>• how weights avoid look-ahead |
| `steps/21_research_paper_track.md` | New section "★ Paper B" (above); MiroFish paper becomes Paper A |
| `QuantEdge_Implementation_Plan.md` | New §4c summarising the methodology table, fixes, challengers, milestones and priority order |
| `README.md` | Update the plan link description; step count 21 → 23 |

