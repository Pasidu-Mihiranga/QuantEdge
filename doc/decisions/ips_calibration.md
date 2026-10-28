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

## Feasibility study across the frontier (Step 05 §4 task 6)

`quantedge.decision.feasibility`; pipeline stage `run_ips_feasibility`; artifacts `ips_feasibility.parquet` / `.json`; IPS page in the app.

**Method:**
- **Portfolios tested:** 25 points on the IPS-constrained mean-variance frontier, plus the full-sample minimum-ES portfolio.
- **Inputs:** Ledoit-Wolf Σ, and the CAPM prior μ with rf as at the end of 2022 (4.45%) and a 5% market premium, i.e. the optimiser's own expected return.
- **Evaluation:** each portfolio is held fixed over 2004-11-19 → 2022-12-30 (development + validation only) and checked against every risk limit, and its expected return against the required 6.68%.
- **Caveat:** weights are chosen on the same data, so this is an optimistic screen. A limit that no portfolio meets here cannot be met out of sample either.

| | Adopted IPS (AGG ≤ 65%) | Original IPS (AGG ≤ 40%) |
|---|---|---|
| Portfolios meeting every risk limit | 1 of 26 (the minimum-ES portfolio, ES 1.498% vs 1.5%) | 0 of 26 |
| Best expected return within the risk limits | 5.27% (realised CAGR 5.23%) | n/a |
| Gap to the 6.68% required return | 1.41 points | n/a |
| Lowest achievable 99% 1-day ES / volatility / stress drawdown | 1.50% / 6.07% / 15.2% | 2.39% / 9.10% / 24.4% |
| Share of points failing ES / volatility / stress drawdown | 96% / 46% / 62% | 100% / 100% / 100% |
| Finding | **Conflict**: the risk limits and the return objective cannot both be met | **Infeasible**: no compliant portfolio meets the risk limits, even in-sample (closest exceeds a limit by 59%) |

- **Under the adopted IPS:**
  - ES is the binding limit.
  - The only fully compliant portfolio is AGG 65%, GLD 19%, SPY 15%, XLK 1%, and it sits exactly on the ES limit.
  - The first frontier portfolio that reaches the required return has 9.4% volatility, 2.6% ES and a 25.9% stress drawdown. It breaches all three risk limits.
- **What this means for the decision:**
  - The recalibration makes the risk limits achievable, but not together with the return objective. The return gap is the key finding of Step 05 §3.5.
  - This is why the rule engine returns ADJUST RISK LIMIT, not ACCEPT.
- **Under the original 40% cap:** even the risk limits alone cannot be met, which confirms the internal inconsistency that prompted the review.

## Consequences

- All selection, risk, stress and backtest results are recomputed under the new limits.
- The report shows both cases side by side.
