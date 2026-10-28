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

## Explainability (LightGBM, 99% VaR)

`scripts/run_ml_explain.py` fits one model with the selected configuration. It trains on development data only (forecast origins 2006-11-14 → 2018-12-28) and explains its validation forecasts. This is a representative fit; the arena retrains every 21 days.

- **SHAP importance:** the latest day's return (`ret_lag0`) is the largest driver, at 15% of mean |SHAP|. Next come the distance from the 252-day high (8%), EWMA volatility (8%), the previous day's return (7%) and 5- and 60-day realised volatility (7% each).
- **Crisis day:** the highest validation forecast is for the day after 2020-03-11 (99% VaR 3.64% against a model average of 0.75%). It is driven by that day's −1.9% return, the −1.5% return two days earlier, the 5-day VIX jump (+10.5 points) and short-horizon volatility.
- **Monotonicity:** LightGBM 4.x cannot impose monotone constraints with the quantile objective, so monotonicity is measured with ICE curves on 250 validation days.
  - The forecast dips somewhere for almost every day and every volatility feature, as is typical of tree ensembles.
  - For most features the largest dip is small: median 0.5–1.5 bp against a total rise of 3–25 bp.
  - **The exception is 60-day realised volatility:** the median largest dip is 17 bp against a 20 bp rise. So the model often forecasts a lower VaR when longer-run volatility is higher, which is economically implausible. 5-day volatility shows the same pattern more mildly (6 bp dip against a 12 bp rise).
  - This supports the decision not to adopt LightGBM.
