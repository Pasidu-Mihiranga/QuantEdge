# Decision record: ML challenger configurations and validation result (Steps 22–23)

**Date:** 2026-10-28 · **Status:** chosen on validation only; adoption pending the final test

## Configurations chosen on validation (2019-01-01 → 2022-12-31)

The rule (`scripts/run_ml_grid.py`): the lowest 99% pinball among configurations passing Kupiec, Christoffersen CC and no red rolling window; if none passes, the lowest-pinball configuration is kept and flagged.

| Model | Grid | Chosen | Passes coverage |
|---|---|---|---|
| Linear QR | none | — | yes (14 exceptions vs 10.1) |
| LightGBM | num_leaves {7, 15} × min_data_in_leaf {50, 100} | num_leaves 15, min_data_in_leaf 50 | **no** (every configuration 21–27 exceptions) |
| LSTM | seq_len {20, 60} × hidden {16, 32} × weight_decay {1e-4, 1e-3}, 5-seed ensembles | seq_len 20, hidden 32, weight_decay 1e-3 | **no** (every configuration 27–39 exceptions) |

Every configuration's result is in `data/artifacts/ml_grid_val.parquet`; the choice is in `data/artifacts/ml_selected_configs.json`.

## Arena on validation (portfolio: Min CVaR; champion: Conditional EVT)

| Model | Exceptions | 99% pinball vs champion | FZ0 vs champion | DM (Holm p) | 90% MCS | Coverage |
|---|---|---|---|---|---|---|
| Linear QR | 14 | −5.3% | −1.0% | −0.44 (1.0) | in | passes |
| LightGBM | 26 | −3.0% | −2.0% | −0.60 (1.0) | in | fails |
| LSTM | 27 | −0.7% | +2.4% | −0.08 (1.0) | in | fails |
| Conditional EVT (champion) | 16 | 0 | 0 | — | in | passes |
| GARCH-FHS | 17 | +1.2% | +0.4% | 1.35 (1.0) | in | fails (Kupiec p = 0.045) |

## Status against the adoption rule (Step 22 §3.8)

- **Linear QR** meets condition 1 (lowest primary loss on validation) and condition 2 (FZ0 non-inferior, Kupiec and CC not rejected, no red window). Condition 3 (confirmation on the locked final test without retuning) is pending. Its advantage is not statistically significant (DM, Holm-corrected).
- **LightGBM and LSTM** fail condition 2: their 99% VaR is systematically too low on validation in every configuration tried. They are reported, not adopted.
- **Interpretation for the report and Paper B:** on about 1,000 validation days, the nonlinear models did not improve calibrated tail forecasts over a linear quantile regression on the same features.
