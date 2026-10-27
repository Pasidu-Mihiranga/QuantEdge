# Decision record: risk-model champion rule (Step 11)

**Date:** 2026-10-28 · **Status:** adopted by the team · **Applies before:** methodology freeze

## Decision

The champion is the **lowest-loss adequately validated model on the validation period** (2019-01-01 → 2022-12-31).

- **Adequately validated** means all of the following:
  - Kupiec not rejected at 5%;
  - Christoffersen conditional coverage not rejected at 5%;
  - no red rolling 250-day Basel window;
  - Acerbi–Szekely Z2 not rejected at 97.5%.
- **Loss** means the mean 99% pinball (quantile) loss, the same primary metric as the Step 22 champion–challenger rule.
- **Conditional EVT is the provisional candidate, not yet an unconditional winner.** The selection is confirmed only after:
  - the analysis is rerun on the recalibrated IPS portfolio;
  - Diebold–Mariano (Holm-corrected) and Model Confidence Set evidence are reviewed;
  - the locked final test is run once after the freeze.

## Why

- The previous rule ("simplest passing model") chose GARCH-FHS.
- On validation, Conditional EVT had a significantly lower pinball loss (DM −3.26, Holm p = 0.006), and GARCH-FHS fell outside the 90% Model Confidence Set (p = 0.009).
- Keeping a statistically dominated model would be hard to defend.
- Using the same primary metric as the ML adoption rule makes the two stages consistent.
- The change uses validation data only; the final-test period has not been examined.

## Implementation

`config.yaml → backtest.champion_rule: lowest_pinball_passing`; `backtest/report.py::choose_champion`.
