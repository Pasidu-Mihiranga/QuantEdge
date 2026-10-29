# Methodology freeze checklist (gate G3)

The tag `methodology-freeze-v1` may be created only when every **blocking** item is ticked. After the tag, the final-test script runs once (Step 22 M7) and any change is logged here as a post-hoc deviation.

## Blocking

- [ ] **Input lock signed** ([inputs_lock.md](inputs_lock.md)): D1–D10 agreed 2026-10-28; signatures and reviewer names outstanding
- [x] **Hypothetical shock sizes (D5) confirmed by the team** (2026-10-28): "Hormuz stagflation 2027" at 2022-size rates (+250 bp), recorded in `inputs_lock.md` and `config.yaml`; the severe case is shown only as "what would break the budget"
- [x] **The final test runs the locked champion on the recommended portfolio** (option C, 2026-10-28): the pipeline carries the 35%-equity frontier portfolio and GJR conditional EVT (`config.yaml → portfolio.focus`, `backtest.champion`) and reproduces notebook 04 exactly on 2019–22 (`tests/test_reconciliation.py`; notebook 04 §8 asserts the same). Fallback B not needed
- [ ] **D10 wording aligned with the locked rule (team to confirm):** D10 says "otherwise ADJUST THE RISK LIMIT", but spec §5 and the A2 decision-map code give REJECT when no portfolio reaches the objective even with the budget loosened by 5 pp (the end-2022 dry run is exactly that case). Proposed: D10 = spec §5 (ACCEPT / ADJUST within 5 pp / REJECT, spending change as advice). The code, notebook 06 Part B and the defence document already follow spec §5
- [x] **Notebook 06 Part B dry run** (2026-10-29, end-2022 data): REJECT by the locked rule, for return only (35% portfolio 4.91% vs 5.90% required; every risk limit passes); robust in 18 of 18 assumption cases; flips to ACCEPT if the decision-date real yield is about 1 pp higher (TIPS ≥ about 2.58%). The real run: set `DECISION_DATE = "2026-10-26"` after the tag, rerun notebooks 05 and 06 once
- [x] **Every validation breach explained** (2026-10-29): 14 of 14 with a news-verified market cause, 0 data errors; 8 within the model's own ES forecast, 6 calm-to-stress switches ([exception_log.md](exception_log.md); notebook 04 breach anatomy). Owner to review
- [x] **The pipeline uses the agreed IPS v2** (2026-10-29): D1, D2 and D4 in `config.yaml → ips`; limits and objective measured as notebooks 03 §4 and 06 A2, reproduced within 0.01 bp (`tests/test_objective.py`, notebook 06 A9). The app, the memo and Part B cannot disagree on the verdict
- [x] IPS calibration decided ([ips_calibration.md](ips_calibration.md)): AGG cap 65%, original 40% case kept for sensitivity
- [x] Champion rule decided ([champion_rule.md](champion_rule.md)): lowest-loss adequately validated model on validation
- [x] Verdict logic decided ([decision_engine.md](decision_engine.md)): minimum relaxation + client-approval condition
- [x] Stress scenario horizon: a cumulative peak-to-trough episode of about three quarters (D5, agreed 2026-10-28; notebook 06 A5)
- [x] Credit-spread measure: BAA10Y (Moody's Baa − 10-year Treasury, daily since 1986; FRED keeps only 3 years of the ICE series). +150 bp lies between 2022 (+43 bp) and the GFC (about +330 bp)
- [x] Champion confirmed on the recommended (35%-equity frontier) portfolio: **GJR conditional EVT** by the locked rule (notebook 04: 14 exceptions vs 10.1, Kupiec p = 0.24, Christoffersen p = 0.53; statistically tied with plain conditional EVT, Holm p = 0.42)
- [x] **Which ES measure governs the IPS ES limit:** resolved by D2: a through-the-cycle 99% ES (development data including the GFC) sets the limit; the champion's conditional forecast is a monitoring alert (D9). Original note: the minimum-relaxation calculation uses realised out-of-sample 99% ES (Min CVaR 1.63%, i.e. +9%), while check C4 uses the champion's current conditional forecast (2.21% at end-2022, i.e. about +47%). Choose one measure for both (or state both explicitly in the IPS)
- [x] **C7 removed in Phase 0; replaced by the D8 ES-share cap (40%).** Original note: SPY is at 2.11 and EFA at 1.84; AGG and GLD are at their caps, and moving weight from SPY to EFA does not lower the maximum (`decision/sizing.py::propose_resize` reports "not achievable"). Risk-to-capital = marginal ES / portfolio ES, so small volatile sleeves in a bond-led portfolio always score high. Decide: redefine C7 (for example, a cap on any single asset's share of total ES), accept a documented exception, or change the caps
- [x] Official risk window W = 500 days (notebook 04; lookback justification in notebook 02 §5). Original note: W = 250 passes only Cornish-Fisher; W = 500 and 1000 both pick Conditional EVT (W = 1000: Conditional EVT and GARCH-FHS both pass, 14 exceptions each). Record whether W = 500 stays the official window
- [x] EVT threshold: fixed at the 90% quantile (about 10% of the data); the stability rule only picks the grid floor, and 99% figures barely depend on the choice (notebook 03 §3)
- [x] ML hyperparameters chosen on validation and recorded ([ml_selection.md](ml_selection.md)): LightGBM and LSTM fail coverage in every configuration; on the recommended portfolio against the locked champion, Linear QR also fails conditions 1–2 (re-run 2026-10-28) and is a reported challenger only

When every blocking item is ticked, run `scripts/freeze.py`. It hashes the adoption-rule text (Step 22 §3.8) and writes the freeze record (`config.yaml`, data manifest, `requirements*.txt`, artifact manifest, selected ML configurations, seeds, champion and challengers). The team then commits the record and creates the tag; the tag unlocks `python -m quantedge.backtest.final_test`, which runs once.

## Non-blocking (before submission)

- [x] Every quality flag confirmed against market events (2026-10-29: the last one, 2026-01-30 GLD −10.3%, is genuine: spot gold −9.5%, its largest one-day fall since 1983; [exception_log.md](exception_log.md))
- [x] Verdict sensitivity grid: MRP 4/5/6% and original IPS done (`verdict_sensitivity.parquet`); cash on/off done; estimation windows 250/1000 done
- [ ] Reviewer names filled in `doc/ai_log.md`
