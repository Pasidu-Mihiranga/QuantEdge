# Methodology freeze checklist (gate G3)

The tag `methodology-freeze-v1` may be created only when every **blocking** item is ticked. After the tag, the final-test script runs once (Step 22 M7) and any change is logged here as a post-hoc deviation.

## Blocking

- [x] IPS calibration decided ([ips_calibration.md](ips_calibration.md)): AGG cap 65%, original 40% case kept for sensitivity
- [x] Champion rule decided ([champion_rule.md](champion_rule.md)): lowest-loss adequately validated model on validation
- [x] Verdict logic decided ([decision_engine.md](decision_engine.md)): minimum relaxation + client-approval condition
- [ ] Stress scenario: state the shock **horizon** ([stress_scenario.md](stress_scenario.md), open item 2)
- [ ] Stress scenario: **align the credit-spread measure** and justify +150 bp on BAA10Y (open item 1)
- [ ] Champion confirmed on the recalibrated portfolio (DM / MCS evidence reviewed by the team). Rerun 2026-10-28: Conditional EVT (16 exceptions vs 10.1, Kupiec p = 0.08, CC p = 0.12); GARCH-FHS now fails Kupiec (p = 0.046)
- [ ] **Which ES measure governs the IPS ES limit:** the minimum-relaxation calculation uses realised out-of-sample 99% ES (Min CVaR 1.63%, i.e. +9%), while check C4 uses the champion's current conditional forecast (2.21% at end-2022, i.e. about +47%). Choose one measure for both (or state both explicitly in the IPS)
- [ ] EVT threshold rule: justify the 85% grid floor or add mean-excess linearity to Rule A (design on dev, choose on val)
- [ ] ML hyperparameters chosen on validation (LightGBM 4-config grid, LSTM 8-config grid) and recorded
- [ ] ML adoption rule text hashed (Step 22 §3.8)
- [ ] Freeze record written: tag SHA, SHA-256 of `config.yaml`, data manifest, `requirements*.txt`, model artefacts, seeds, champion and challenger list

## Non-blocking (before submission)

- [ ] Every quality flag confirmed against market events (2026-01-30 GLD −10.3% still to verify)
- [ ] Verdict sensitivity grid (95/99%, windows 250/500/1000, cash on/off, MRP 4/5/6%)
- [ ] Reviewer names filled in `doc/ai_log.md`
