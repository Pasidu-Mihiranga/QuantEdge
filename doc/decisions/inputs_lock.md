# Input lock: the team's decisions D1–D10

**Purpose.** Every judgement that changes the verdict is recorded here, with its evidence and the booklet clause it answers, **before** Part B of `notebooks/06_decision.ipynb` and the final test are run. This is the team's protection against data snooping and the source for the report's IPS section and the app's Assumptions & Limitations page.

**Status:** values **AGREED by the team on 2026-10-28**, including D6 and D7. **Not yet locked:** the signatures below. · **Signed by:** _[names]_ · **Locked on:** _[date]_

**Rules**
- Evidence comes from data up to 2022-12-31 (`notebooks/06_decision.ipynb` Part A, `02`, `03`). The 2023–26 test is untouched.
- Each decision records **one central value** (so the verdict is mechanical) **and** the plausible range, with a robustness sentence for the memo.
- After locking, a change is allowed only as a logged deviation (date, reason, and the verdict under both values).
- Page references are to `Quant edge 1.0 Final Challenge 1.pdf` (the booklet).

---

## The return objective these decisions produce

**Return objective: US CPI + 3.5% a year (net of costs), over a 10-year rolling horizon** = 3.0% spending (D1) + 0.5% real growth.
Booklet p. 3: the endowment seeks to "preserve **and grow** its capital … balance capital preservation, income generation, and sustainable real growth"; p. 4, responsibility 2: "determine an appropriate return objective consistent with the client's mandate and risk tolerance".

## Investment horizon

The endowment is perpetual. The **return objective is judged over a 10-year rolling horizon**; risk is **monitored daily and over 10 days** (VaR, ES, EVT) and **budgeted per crisis episode** (D2). Booklet p. 4, responsibility 1: "determine what the appropriate investment horizon … should be, and defend your recommendation".

---

## D1 · Spending rate: **3.0%** of the 12-quarter average value (range 2.5–3.5%)
- **Kind:** preference (the team sets the return objective; the booklet gives no spending rate)
- **Booklet:** p. 3 "preserve **and grow** … sustainable real growth"; p. 3 "income generation"; p. 4 responsibility 2
- **Method:** decision map, sustainable-spending analysis, 10-year simulation (06 A2, A2b, A4)
- **Evidence:** with a 25% crisis budget and 0.5% real growth, the portfolio funds about **2.0%** spending at end-2022 market levels (06 A2b) and about **3.0%** if the 10-year real yield is 1 pp higher at the decision date (06 A2c). At 3% spending the 10-year chance of losing a fifth of real value is about 26% even at end-2022 levels, against about 40% at 4% (06 A4). Peer average (NACUBO FY2025): 4.9%, which needs far more risk.
- **Robustness sentence:** "3% spending is sustainable with 0.5% real growth when the 10-year real yield is at least about 1 pp above its end-2022 level; below that, the objective is not met and the memo shows the cost of closing the gap."
- **Decided by / date:** team, 2026-10-28

## D2 · Crisis budget (D_max): **25%** worst peak-to-trough loss, applied to max(historical replays, hypothetical) (range 20–30%)
- **Kind:** preference
- **Booklet:** p. 3 "avoiding large losses is more important than maximizing gains"; p. 3 "balance capital preservation … and sustainable real growth"; p. 4 "portfolio resilience during market crises"; p. 4 responsibility 3 "define and justify the risk constraints"
- **Method:** limit calibration from the frontier (03 §4); sustainable spending by budget (06 A2b)
- **Evidence:** 25% → about 36% equity, volatility limit 8.4%, 99% 1-day ES limit 2.23% (through the cycle). A 20% budget (about 24% equity) cannot fund any real growth; little extra capacity above 25%. A ~35/65 mix is conservative by industry standards.
- **Derived limits:** volatility ≤ 8.4%; 99% 1-day ES (dev data including the GFC) ≤ 2.23%. Recomputed mechanically from D2 at the decision date.
- **Sensitivity shown in the memo:** 20%.
- **Decided by / date:** team, 2026-10-28

## D3 · Caps: **AGG ≤ 65%**; XLE, XLK, EEM ≤ 10%; GLD ≤ 15%; each equity ETF ≤ 40%; equity ≤ 50%
- **Kind:** design (concentration policy)
- **Booklet:** p. 4 "a single fund or any combination of eligible funds"; p. 4 "diversification benefits"
- **Method:** cap sensitivity (02 §2)
- **Evidence:** at 30% equity, AGG caps of 60/65/70% give the same volatility (9.8%); only the AGG/GLD mix changes. Caps bind below 35% equity, not above.
- **Decided by / date:** team, 2026-10-28

## D4 · Equity risk premium **4.5%** (arithmetic; range 3.5–5.5%) and AGG spread **0.5%** (range 0.3–0.9%)
- **Kind:** uncertain quantity, stated as a **disclosed assumption**
- **Booklet:** p. 9 "using an undisclosed or proprietary data source is a rubric violation"; approved sources: Yahoo Finance, FRED, World Bank/IMF
- **Method:** anchored on approved data (SPY's realised premium over T-bills, 2004–22: 7.6% a year, an exceptional period; AGG over a duration-6 Treasury proxy: about 0.9% a year), cross-checked against published estimates (06 A1), and tested by break-even (06 A3)
- **Cross-check only (not used as data):** published 2025–26 estimates of the US equity premium lie roughly between 4.2% and 5.5% (an academic implied-ERP series, a valuation-firm recommendation and a practitioner survey; the owner cites them in the report's references)
- **Robustness:** the verdict does not change anywhere in 3–6% (break-even ERP for the old 4% spending: 9.4%)
- **Decided by / date:** team, 2026-10-28

## D5 · Hypothetical shock horizon: **a cumulative peak-to-trough episode of about three quarters** (2022-like), with its worst quarter shown as speed
- **Kind:** design
- **Booklet:** p. 8 "one hypothetical scenario the team designs itself"; p. 9 FRED macro series "used in … stress-scenario construction"
- **Method:** speed of past crises (06 A5)
- **Evidence:** GFC 81% of its loss in the worst quarter; COVID 15.5% in 23 days; 2022 only 52% within any quarter over 9 months. Peak-to-trough makes the scenario comparable with D_max.
- **Shock sizes (agreed 2026-10-28): "Hormuz stagflation 2027"**: 10-year yield +250 bp, oil +40%, VIX +25, dollar +8%, Baa spread +150 bp over about three quarters, plus one liquidity day (AGG −5%). Chosen as the most severe candidate still within history (joint distance 5.1: beyond 2022's 3.9 and the GFC's 3.5, below COVID's 6.0; notebook 05 §4b), following the "severe but plausible" standard (BIS) and the Federal Reserve's practice of calibrating to past recessions. The original design (+150 bp) gave the same loss as the 2022 replay, so it added nothing. The severe case (distance 6.5, beyond anything on record) is shown only as "what would break the budget". The factor mapping was validated on 2022 (17.8% predicted vs 18.8% actual). The story uses October 2026 news; the sizes use data up to 2022 only.
- **Why this scenario and not another:** compared in notebook 05 §4c with an AI/semiconductor crash, a deflationary crash, a "sell America" shock and a rupee crisis; only stagflation targets this portfolio's specific weakness, adds information beyond the historical replays, and can be calibrated and validated before the freeze.
- **Decided by / date:** team, 2026-10-28

## D6 · Notebook owners (open)
- **Booklet:** p. 9 "teams may be asked to explain any part … inability … may result in reduced marks or disqualification"
- **Agreed:** all six notebooks (01–06) are owned by the **team lead** (name added at signing), who re-runs each one and signs it off in `doc/ai_log.md`.
- **Risk this creates, and how we cover it:** judges may question **any** member on any part (booklet p. 9). Each of the other four members is assigned as **reviewer** of at least one notebook below, must be able to explain the verdict and that layer, and rehearses with `reports/decision_defence.html` before the pitch.

| Notebook | Owner | Reviewer (must be able to explain it) |
|---|---|---|
| 01 EDA detective | team lead | _[ ]_ |
| 02 Portfolio and frontier | team lead | _[ ]_ |
| 03 VaR, ES, EVT | team lead | _[ ]_ |
| 04 Backtesting | team lead | _[ ]_ |
| 05 Stress and regimes | team lead | _[ ]_ |
| 06 Decision | team lead | _[ ]_ |

## D7 · Hard freeze date (open)
- **Submission:** the second week of November 2026 (9–13 November).
- **Freeze date: Friday 30 October 2026** (fallback: Monday 2 November if the pre-freeze work is not finished). The data snapshot ends on 26 October 2026, so that is the decision date for market levels. After it: tag `methodology-freeze-v1`, run `final_test` once, refit to the decision date (the freeze day), write the memo and deck, regenerate `reports/decision_defence.html`.

## D8 · Tail-risk share cap: **no ETF above 40% of 99% ES** (range 35–50%)
- **Kind:** preference / design
- **Booklet:** p. 8 "Risk budgeting and position sizing — using each position's marginal VaR/ES contribution"
- **Method:** Euler 99% ES shares across the frontier (06 A6, 03 §6)
- **Evidence:** EFA's share passes 40% from 30% equity (47% at 35%). The cap forces a resizing towards SPY, which is the graded sizing action.
- **Decided by / date:** team, 2026-10-28

## D9 · Monitoring: **alert only**. If the 99% ES forecast stays above the ES limit for 5 trading days, the committee is convened; no automatic trading
- **Kind:** design, backtested
- **Booklet:** p. 10 innovation examples "regime-conditioned risk, optional risk overlays"
- **Method:** walk-forward trigger test, designed on 2008–18 and confirmed on 2019–22 (06 A7)
- **Evidence:** an automatic de-risking rule helped in the design period but made things worse out of sample for every N. Reported honestly as a validated negative result.
- **Decided by / date:** team, 2026-10-28

## D10 · Verdict framing: **ACCEPT with the team-set objective (CPI + 3.5%)** if the recommended point meets it and every risk limit at the decision date; otherwise **ADJUST THE RISK LIMIT** with the minimum change and its dollar cost
- **Kind:** preference
- **Booklet:** p. 8 the memo's options "accept the mandate as proposed / adjust the risk limit / reject"; p. 4 responsibility 2 (the team determines the return objective); p. 4 responsibility 5 "quantify the trade-offs between return-seeking and risk reduction"
- **Evidence:** a peer-level 4% spending objective is not achievable at a conservative risk level (06 A2–A4). The agreed CPI + 3.5% objective is met within the 25% budget if the decision-date 10-year real yield is at least about 1 pp above end-2022 (ACCEPT at 35% equity, ERP 4.5%), and not met at end-2022 levels (06 A2c). The verdict is therefore decided by the market level at the decision date, computed once after the freeze. The memo quantifies what 4–5% spending would cost in extra crisis loss.
- **Decided by / date:** team, 2026-10-28

---

## Also locked with these inputs
- **Regime definition** (notebook 01 §8): rate-hiking cycle = 3-month T-bill up by more than 1 pp over 12 months, known at t−1.
- **Pre-registered hypotheses H1–H6** (problem spec §5): wording fixed as of the lock.
- **Champion-model rule:** lowest 99% pinball loss among models passing Kupiec, Christoffersen and Basel on validation (2019–22).
- **Champion chosen by that rule (notebook 04, 2026-10-28): GJR conditional EVT**: GJR-GARCH(1,1) with Student-t errors on a 500-day window, refitted every 5 days, with a GPD tail on the top 10% of standardised losses. On the 35%-equity portfolio, 2019–22: 14 exceptions vs 10.1 expected (Kupiec p = 0.24, Christoffersen p = 0.53, adapted zone green, no red 250-day window). It is statistically tied with plain conditional EVT (Diebold-Mariano Holm p = 0.42); the rule decides. Limitation disclosed: clustering remains in 44% of 500-day windows, and every model fails in a COVID-speed crash.
- **How the one-shot final test runs (agreed 2026-10-28, option C):** before the tag the pipeline gains the GJR option and the frontier portfolio, and must reproduce notebook 04 on 2019–22 (same exceptions, same pinball loss). After the tag the pipeline's `final_test` runs **once** (official), and notebook 04's independent code replicates it (effective challenge, SR 26-2). **Fallback B:** if the pipeline does not match by 29 October evening, notebook 04 runs the official test once (with a run-once guard) and the pipeline is updated afterwards as a logged implementation step.
- **Option C met (2026-10-28):** the pipeline reproduces notebook 04 on 2019–22 for every model (same exceptions, same pinball loss; VaR forecasts within 0.03 bp of NAV), and its own rule picks the same champion at 250-, 500- and 1000-day windows. The champion and the portfolio are fixed in `config.yaml` (`backtest.champion`, `portfolio.focus`); `tests/test_reconciliation.py` guards the match.
- **Pre-registered test portfolio:** the 35%-equity frontier point. If Part B recommends a different point, its test is reported as well, mechanically.
- **Decision date for the final numbers:** 26 October 2026, the last day of the data snapshot (the dry run uses 2022-12-30).
