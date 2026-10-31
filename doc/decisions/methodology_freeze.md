# Methodology freeze record

**Written:** 2026-10-29 01:16 UTC · **Tag:** `methodology-freeze-v1` (created by the team after committing this file)

**Champion:** GJR conditional EVT (lowest 99% pinball loss among adequately validated models (provisional until the final test)); window 500 days; portfolio Frontier 35% equity (provisional)
**Challenger:** Linear QR (LightGBM and LSTM rejected; archived at tag archive/mirofish-ml)
**Seed:** global 20261027

| Item | SHA-256 |
|---|---|
| config.yaml | `ab42ba114965c4234ae5a6e47390e2c7cc5c873bfd8a7d2d47db011e450e7ecb` |
| data/raw/manifest.json | `6b8b641e0ce10711183e88eafc83ffe8b9a8b8a77d86982ba285a6a499aef9fe` |
| requirements.txt | `b13f294abeeac29b716eccbb58d63c137871b7b4b0c7fff8e754041083dcdc8f` |
| data/artifacts/artifacts_manifest.json | `263f233738e9b68064d370978051b1a7ae49d3ab0e05c15b4c74b492dd59a552` |
| adoption rule text (Step 22 §3.8) | `749a6776453de96f9918516d5a63b68479822350ff6ee10fcf84a18f037d8bf1` |
| doc/decisions/inputs_lock.md | `ad65f96f2a00ae02fa5ecc87aaaec881704f939a4b72dbcceab94a5a00dba0f7` |
| src/quantedge/decision/rules.py | `4405cdd541d81c5f00a839ff2d164f6d146a392830f43bde9b09802ac68d82bb` |
| src/quantedge/decision/objective.py | `82dbee14762dae35918b001e118b583fa568163658a4bdc22a4a21d88f5424ef` |
| src/quantedge/backtest/final_test.py | `8c8ded8e85c0ff63037a491a80a8032b8a15fcb03e9151425d59f6541d269a88` |
| notebooks/04_backtesting.ipynb | `d9c0d127829f69458a53b059d085f697e93ad89459b622ad4a66c1e813c60ad3` |
| notebooks/05_stress_regimes.ipynb | `9797f0d789f764ff61be8754ec6d5fa13c6a1181386c2bebca6d7e284458569a` |
| notebooks/06_decision.ipynb | `760df5834e0050ef9002e7d1ed2823434d0e99ed91449ef410733e6db9542836` |

Any change after the tag is logged below as a post-hoc deviation, with its reason.

## Final test run 2026-10-29T01:48:41Z


Test period 2023-01-01 → 2026-10-26, 955 common days, run once. Scores (99% VaR):

| Model | Exceptions (exp. 9.55) | Kupiec p | Cond. coverage p | Passes | Pinball ×10⁴ | vs champion | Adoption condition 3 |
|---|---|---|---|---|---|---|---|
| Historical | 6 | 0.215 | 0.0006 | no | 1.556 | +10.8% | no |
| Normal | 7 | 0.384 | 0.0017 | no | 1.545 | +10.0% | no |
| Student-t | 7 | 0.384 | 0.0017 | no | 1.592 | +13.4% | no |
| Cornish-Fisher | 5 | 0.103 | 0.0001 | no | 1.839 | +30.9% | no |
| EVT | 7 | 0.384 | 0.0017 | no | 1.593 | +13.4% | no |
| Monte Carlo | 7 | 0.384 | 0.0017 | no | 1.614 | +14.9% | no |
| GARCH-FHS | 8 | 0.604 | 0.0041 | no | 1.464 | +4.2% | no |
| Conditional EVT | 9 | 0.857 | 0.0077 | no | 1.427 | +1.6% | yes |
| GJR-FHS | 7 | 0.384 | 0.0794 | yes | 1.435 | +2.2% | no |
| GJR conditional EVT | 9 | 0.857 | 0.1893 | yes | 1.404 | +0.0% | yes |
| Linear QR | 10 | 0.885 | 0.2333 | yes | 1.480 | +5.4% | no |

**Model validity (spec §5 step 7):** the champion passes its backtests; limits use GJR conditional EVT.
**Challenger:** Linear QR passes coverage but its pinball loss is 5.4% worse than the champion's (margin 2%): condition 3 fails, not adopted.

**Reporting note (2026-10-29):** the run finished every computation and wrote `final_test_result.json`, `final_test_scores.parquet` and one forecast file per model, then stopped while appending this table, because `DataFrame.to_markdown` needs the optional package `tabulate`, which is not installed. The test was **not** rerun. The table above was written from `final_test_scores.parquet` by hand on 2026-10-29; `final_test.py` now falls back to plain text when `tabulate` is missing (a reporting-only change after the tag, no effect on any number).

## Changes after the tag (2026-10-29), each pre-registered as runbook step 5 or reporting only

| Change | Why | Effect on any decision |
|---|---|---|
| `final_test.py`: plain-text fallback when `tabulate` is missing | Reporting only (see the note above) | None |
| Notebook 04 §9, notebook 05 §8, notebook 06 `DECISION_DATE = 2026-10-26` | Runbook steps 2–4 | None: they execute the locked rule |
| `decision/decision_date.py` and the pipeline's decision stage | Runbook step 5: one production source for every headline number, implementing the locked spec §5 rule exactly as notebook 06 Part B | None: reproduces Part B (verdict, weights, limits, frontier to 1e-4; `tests/test_decision_date.py`) |
| `stress/factor.py`: regime stress weeks, weekly log returns, scenario loss with the liquidity day | Runbook step 5: the app's scenario uses notebook 05's agreed D5 model (was a different factor model without the liquidity day) | None on the verdict: the scenario binds at no point; it now matches notebook 05 (21.1% at 35% equity) |
| `config.yaml`: `decision.date`, frontier levels, D8 cap, robustness grid, simulation settings, `stress.hypothetical.liquidity_day` | Values already locked in `inputs_lock.md` and notebook 06, now readable by the production code | None (config hash changes; values are the locked ones) |

## Post-hoc deviation (2026-10-31): scenario returns added as simple returns

**What was wrong.** The frozen `scenario_loss` and notebooks 05 and 06 computed expm1(Σ wᵢ xᵢ), which sums log returns across ETFs and breaks the repo's convention ("never sum log returns across assets"). Found in the app review of 2026-10-29.

**The correction.** Each ETF's log move xᵢ = (B s)ᵢ becomes a simple return, then the simple returns are weighted: R = Σ wᵢ (exp(xᵢ) − 1), plus the liquidity day. This is the exact buy-and-hold result over the episode.

**Result under both versions (decision date):**

| Equity share | Scenario loss, as frozen | Corrected | Difference | Worst historical crisis | Worst of the two decides the budget |
|---|---|---|---|---|---|
| 20% | 19.78% | 19.76% | $2,437 | 18.45% | scenario, both versions |
| 25% | 20.16% | 20.13% | $2,917 | 19.98% | scenario, both versions |
| 30% | 20.62% | 20.58% | $3,754 | 21.94% | history |
| **35% (recommended)** | **21.09%** | **21.04%** | **$4,363** | **23.90%** | **history** |
| 40% | 21.13% | 21.08% | $4,987 | 25.43% | history |
| 45% | 21.18% | 21.13% | $5,504 | 27.04% | history |
| 50% | 21.23% | 21.17% | $5,913 | 29.98% | history |

**Effect on decisions: none.** The verdict (ACCEPT at 35% equity), the weights, the expected return, the limits recalibrated at the budget (set where history binds), the final test and the champion are unchanged. The frozen figure overstated the loss slightly, so it erred on the cautious side. Knock-on figures in notebook 05: severe case 25.5% → 25.3%; endowment at the trough after spending USD 7.65M → 7.66M.

**Why corrected after the freeze.** The freeze guards against tuning a method to the test data. This change is not informed by test results, cannot change a decision, and aligns the code with a rule fixed before the freeze. The hashes above identify the frozen files; `git diff methodology-freeze-v1` shows this change.

## Other changes after the tag (2026-10-31), reporting and hosting only

- The memo and tear sheet are written from `decision_numbers.json`; the pre-freeze generators were removed. No number changes.
- The app reads 2023+ returns without looking for the git tag, because a hosted clone may not carry tags. The guard in `partition.py` is unchanged for all analysis code.
