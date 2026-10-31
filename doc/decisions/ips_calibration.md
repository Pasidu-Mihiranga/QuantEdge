# Decision record: IPS calibration (Step 05)

**Date:** 2026-10-28 · **Status:** adopted by the team · **Applies before:** methodology freeze (`methodology-freeze-v1`)

## Decision

- **AGG may be held up to 65%.** AGG is exempt from the 40% single-asset cap and has its own 65% cap.
- **All other asset limits are retained:** 40% single-asset cap; XLE, XLK, EEM ≤ 10%; GLD ≤ 20%; AGG ≥ 25%; equity ≤ 50%; cash ≤ 10%; and the risk limits (volatility ≤ 8%, 99% 1-day ES ≤ 1.5%, stress drawdown ≤ 20%).
- **The original 40% case is preserved for sensitivity comparison:** the scorecard is also computed with AGG ≤ 40% (`ips_variants.original_agg40` in `config.yaml`).

## Why

- The 40% single-asset cap exists to stop concentration in one risky holding.
- AGG is a broad investment-grade bond index (thousands of issues), which is itself diversified. It is the natural core holding for a conservative, capital-preserving endowment.
- With AGG ≤ 40% and GLD ≤ 20%, at least 40% had to sit in equities. That made the IPS internally inconsistent: no long-only portfolio could meet the volatility, ES and drawdown limits.
- The change comes from the client's profile (low willingness to take risk, income and preservation objectives), not from optimising the results. The original case stays visible so the effect of the change can be seen.

## Evidence that prompted the review (validation data, 2008–2022 walk-forward)

- **With AGG ≤ 40%:** no candidate passed the IPS (out-of-sample 99% ES ≥ 2.4%, volatility ≥ 9.1%, GFC drawdown ≥ 25%).
- **The benchmark:** the 60/40 policy benchmark also breaches the IPS (SPY 60% > 40%; equity 60% > 50%).

## Consequences

- All selection, risk, stress and backtest results are recomputed under the new limits.
- The report shows both cases side by side.
