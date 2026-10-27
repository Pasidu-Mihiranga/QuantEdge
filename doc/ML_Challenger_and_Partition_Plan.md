# Add chronological data partition + custom ML challenger (LightGBM quantile VaR) to the QuantEdge plan

## Context

The user wants the plan extended with a **hybrid validation design** and a **custom predictive model**:
- Chronological train / validation / final-test splits **on top of** (not instead of) walk-forward backtesting.
- One carefully scoped custom ML model, **LightGBM quantile regression** for conditional VaR. It acts as a **challenger** to the established models (HS, Student-t, GARCH-FHS, EVT, Monte Carlo), and its added value must be measurable.

Core principle: **don't replace walk-forward testing with ordinary splits; combine them.** The core system stays as it is: Robust Mean-ES, GARCH, EVT and the validation framework. The ML model must *earn* its place through pre-declared tests. Either outcome is defensible for a conservative $10M endowment.

The plan docs live in `C:\Users\PMIHIR\Desktop\QuantEdge\doc\` (own git repo, remote `Pasidu-Mihiranga/QuantEdge`, branch `main`). The change ends with a commit and push using the same rules as before: author Pasidu-Mihiranga, **no Claude attribution**, PDF/PPTX stay ignored.

## Design decisions (expert additions beyond the pasted text)

1. **Partition, enforced in code (`partition.py`):**

   | Period | Dates | Use |
   |---|---|---|
   | Development | 2004-11-18 → 2018-12-31 | Fitting, feature engineering, design of the EVT threshold rule, IPS feasibility |
   | Validation | 2019-01-01 → 2022-12-31 | Hyperparameters, choice of window W, champion selection, portfolio-candidate selection. Contains COVID and 2022 |
   | Final test | 2023-01-01 → snapshot | **Locked**. Evaluated once, after the methodology freeze |

   Walk-forward runs *inside* validation and test: retrain using only past data.
2. **Methodology freeze:**
   - Freeze record: `doc/decisions/methodology_freeze.md` plus git tag `methodology-freeze-v1`, made at gate G3 (end of Week 3), **before** the final-test script runs.
   - The test script refuses to run without the tag. Any change after the tag is logged as a post-hoc deviation.
3. **Retrofit to existing steps.** All selection decisions use data up to 2022 only:
   - Step 05: IPS calibration.
   - Step 07: portfolio scorecard.
   - Step 10: EVT threshold rule.
   - Step 11: champion model.

   Full-history walk-forward (2008 onwards) is still shown for reporting, labelled "exploratory, includes test period". The sidebar date range stays free, with the partition bands shaded on the charts.
4. **Honest power note.** The final test (about 950 days) contains no major crisis, so only about 9–10 exceptions are expected at 99%, and the tail tests have low power. Report this, and also show 95% results.
5. **ML model spec:**
   - **Target:** next-day portfolio loss ℓ_{t+1} at the recommended weights.
   - **Models:** separate quantile models at 90/95/99%, with crossing fixed by monotone rearrangement.
   - **Features (all known at t, lag-tested):**
     - r_t … r_{t−4};
     - realised volatility over 5/20/60 days;
     - EWMA volatility (λ = 0.94);
     - 20-day downside semivolatility;
     - **GARCH σ_{t+1|t} as a feature** (hybrid stacking);
     - VIX level and 5-day change;
     - Δ10-year yield and Δ high-yield spread;
     - 60-day average pairwise correlation and 60-day SPY–AGG correlation;
     - distance from the 252-day high.
   - **Robustness/explainability:** LightGBM `monotone_constraints` (+1 on the volatility features); a small hyperparameter grid; expanding window, retrained every 21 days in walk-forward; early stopping on an inner time split.
   - **ES companion:** ES_ML = VaR_ML × (ES/VaR ratio from conditional EVT at t), stated as a hybrid assumption.
   - **Explainability:** built-in SHAP values via `pred_contrib=True` (no extra dependency).
   - **Naive-ML baseline:** a linear quantile regression (statsmodels `QuantReg`) on the same features, so we can tell whether the gain comes from the trees or from the features.
6. **Champion–challenger evaluation** (model-risk-management framing):
   - Pinball loss.
   - **FZ0 joint VaR/ES loss** (Fissler–Ziegel; Patton, Ziegel & Chen 2019).
   - **Diebold–Mariano** test (HAC) against the champion.
   - **Model Confidence Set** (Hansen–Lunde–Nason, `arch.bootstrap.MCS`).
   - Kupiec, Christoffersen, Basel and the Acerbi–Szekely Z2 test.
   - Regime split (VIX ≤ 30 vs > 30; crisis windows).
   - Sanity check: is ML VaR systematically below the champion's in stress?
7. **Pre-declared adoption rule:**
   - **ADOPT** the ML model as champion only if, **on validation**, it has lower FZ0 and pinball loss (DM p < 0.05) **and** passes Kupiec and CC **and** is green on Basel **and** Z2 is not rejected; **and** it is confirmed on the final test without any re-tuning.
   - **CHALLENGER-ONLY** if it is good on validation but not confirmed on test.
   - **REJECT** otherwise.
   - Then report whether adoption changes the Step 13 verdict.

## Files to create / edit (all under `C:\Users\PMIHIR\Desktop\QuantEdge\doc\`)

**New:** `steps/22_ml_challenger_and_data_partition.md`, using the standard step template (target, why, how, implementation, tests, pitfalls, Q&A). Sections:
1. The partition and freeze protocol (items 1–4 above).
2. ML model specification (item 5): features table, target, training regime, ES companion, explainability.
3. Evaluation and statistics (item 6).
4. Adoption rule (item 7).
5. Implementation table:
   - `data/partition.py`;
   - `ml/features.py` (with a lag-guard test);
   - `ml/quantile_lgbm.py`, a `LGBMQuantileModel` implementing the Step 08 `RiskModel` protocol so the Step 11 engine reuses it;
   - `ml/linear_qr.py`;
   - `backtest/scoring.py` (pinball, FZ0, DM, MCS);
   - `backtest/final_test.py` (tag-gated);
   - `app` "Model Arena" tab.
6. Acceptance tests:
   - feature lag test (shifting the future leaves features unchanged);
   - quantile calibration on simulated heteroskedastic data;
   - monotonicity check;
   - pinball/FZ0 values against hand calculations;
   - the final-test script refuses to run without the tag.
7. Pitfalls:
   - random K-fold;
   - tuning on 2020/2022 *after* seeing the test;
   - scaling with full-sample statistics;
   - too few tail observations at 99% (about 35 in dev);
   - claiming "ML is better" without DM/MCS.
8. Q&A answers.
9. Schedule and owners:
   - owners R (lead) and D (features);
   - Week 2 Days 4–5: features and partition;
   - Week 3 Days 1–3: walk-forward training and evaluation;
   - G3: freeze;
   - Week 4 Day 1: final-test run.

**Edits to existing step files:**

| File | Change |
|---|---|
| `steps/00_INDEX.md` | Add row 22 (owner R + D) and dependencies (08, 11 → 22 → 13). Gates: G2 adds "partition + features"; G3 adds "ML challenger evaluated on validation; **methodology freeze tag**"; G4 adds "final-test run once". Cut order: protect a reduced scope (99% only, 8 features) before cutting entirely; cut it after the t-copula and Markov regime |
| `steps/01_project_setup.md` | Add `partition:` and `ml:` blocks to the config schema; add `lightgbm` to requirements |
| `steps/05_ips.md`, `07_portfolio_construction.md`, `10_evt.md` | One short "Partition rule" note each: selection and calibration use data up to 2022 only; 2023+ is confirmation |
| `steps/08_var.md` | Add the ML challenger (and linear QR) to the model registry table, marked "challenger, see Step 22" |
| `steps/11_backtesting.md` | New §3.0 "Partition × walk-forward" (how the two combine, the freeze tag); add pinball, FZ0, DM and MCS to the model-selection table; the selection rule uses validation only |
| `steps/15_pipeline_app.md` | Backtesting page: partition bands shaded; new "Model Arena" tab (champion vs challengers, loss table, DM/MCS, SHAP summary, adoption badge) |
| `steps/16_testing_deployment.md` | Add leakage guards: feature lag test, partition guard, tag-gated final-test test |
| `steps/17_report_tearsheet.md` | Report §5 gains "Champion–challenger and final test" (0.5 page) |
| `steps/18_pitch_defence.md` | Q&A items 38–41: "Why not a normal train/test split?", "Is your ML better than GARCH?", "Did COVID/2022 tuning leak into the test?", "Why so few tail observations?" |
| `QuantEdge_Implementation_Plan.md` | New section "4c. Hybrid validation and ML challenger", summarising the items above; add the ML row to the schedule notes |

## Steps

1. Write `steps/22_ml_challenger_and_data_partition.md`.
2. Apply the edits listed above (Edit tool, small targeted insertions).
3. `git add doc/` → commit `"Add chronological partition and LightGBM quantile VaR challenger to plan"` (no Co-Authored-By, no Claude mention) → `git push origin main`.

## Verification

- Every `doc/steps/*.md` link in `00_INDEX.md` resolves (Glob plus Grep for the `22_` link).
- Grep confirms that the partition dates (2018-12-31, 2019-01-01, 2022-12-31, 2023-01-01) are consistent across steps 11, 22 and the master plan.
- `git status` before the commit shows only `doc/` changes (no PDF/PPTX). `git log -1 --format=%B` contains no "Claude" or "Co-Authored-By". `git ls-remote origin` shows the new `main` SHA.
