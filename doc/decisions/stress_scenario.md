# Decision record: hypothetical stress scenario (Step 12)

**Date:** 2026-10-28 · **Status:** adopted as initial assumptions · **Must be completed before:** methodology freeze

## Decision

The five factor shocks of "Stagflation and correlation breakdown" are retained as **initial assumptions**:

| Factor | Shock | Anchor |
|---|---|---|
| 10-year Treasury yield | +150 bp | 2022 saw about +240 bp |
| WTI oil | +40% | |
| VIX | +25 points (to about 45) | |
| Broad USD index | +8% | |
| Credit spread | +150 bp | See open item 1 |

## Open items to close before the freeze

1. **Align the credit-spread measurement.** The original design used the ICE BofA high-yield spread (+300 bp). FRED now keeps only three years of that series, so the factor model uses Moody's Baa − 10-year Treasury (`BAA10Y`). The +150 bp shock must be stated and justified on the BAA10Y scale, or re-expressed from a high-yield shock through an estimated BAA10Y/HY relationship. The series, units and the shock must all refer to the same measure.
2. **Specify the shock horizon.** The factor betas are estimated on weekly changes. The team must state over what horizon the shocks occur (for example, an instantaneous shock, one month or one quarter) and how the weekly betas are applied to it.

Until both items are closed, `config.yaml → stress.hypothetical` carries `horizon: null` and the freeze checklist lists them as blocking.
