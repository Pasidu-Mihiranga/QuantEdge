# Input lock: the team's decisions D1–D10

**Purpose.** Every judgement that changes the verdict is recorded here, with its evidence, **before** Part B of `notebooks/06_decision.ipynb` and the final test are run. This is the team's protection against data snooping and the source for the report's IPS section and the app's Assumptions & Limitations page.

**Status:** NOT LOCKED · **Locked on:** _[date]_ · **Signed by:** _[names]_

**Rules**
- Evidence comes from data up to 2022-12-31 (`notebooks/06_decision.ipynb` Part A, `02`, `03`). The 2023–26 test is untouched.
- Each decision records **one central value** (so the verdict is mechanical) **and** the plausible range, with a robustness sentence for the memo.
- After locking, a change is allowed only as a logged deviation (date, reason, and the verdict under both values).

---

## D1 · Spending rate
- **Kind:** preference (the client's policy; no "true value" in the data)
- **Method:** decision map, sustainable-spending analysis, 10-year simulation (06 A2, A2b, A4)
- **Evidence:** with a 25% crisis budget the portfolio sustainably funds about **2.4%** real spending (2.1–3.0% for ERP 3–6%). At 4% spending, P(real value < 80% within 10 years) is 41–49%, and the median loses 15–19% of purchasing power. NACUBO FY2025 average effective spending rate: 4.9%.
- **Plausible range:** 2.5–4.5%
- **Team choice:** _[value]_ · **Range stated in the memo:** _[range]_
- **Robustness sentence:** _[e.g. "The recommendation is the same for spending between … and …"]_
- **Decided by / date:** _[names, date]_

## D2 · Crisis budget (D_max: worst peak-to-trough loss accepted, applied to max(historical replays, hypothetical))
- **Kind:** preference
- **Method:** limit calibration from the frontier (03 §4); sustainable spending by budget (06 A2b)
- **Evidence:** 20% → about 24% equity (volatility limit 6.6%, 99% ES limit 1.63%); 25% → about 36% equity (8.4%, 2.23%). Spending capacity barely rises above 25%.
- **Plausible range:** 20–30% · **Proposed:** 25%
- **Team choice:** _[value]_ · **Derived limits:** volatility ≤ _[ ]_, 99% 1-day ES (through the cycle) ≤ _[ ]_
- **Decided by / date:** _[names, date]_

## D3 · AGG cap (and confirmation of the other caps)
- **Kind:** design (concentration policy)
- **Method:** cap sensitivity (02 §2)
- **Evidence:** at 30% equity, AGG caps of 60/65/70% give the same volatility (9.8%); only the AGG/GLD mix changes. Other caps: XLE, XLK, EEM ≤ 10%; GLD ≤ 15%; each equity ETF ≤ 40%; equity ≤ 50%.
- **Plausible range:** 60–70% · **Proposed:** 65%
- **Team choice:** _[value]_ · **Decided by / date:** _[names, date]_

## D4 · Equity risk premium and AGG spread
- **Kind:** uncertain quantity
- **Method:** our data, outside estimates (to be cited by the owner), break-even test (06 A1, A3)
- **Evidence:** realised SPY premium over T-bills 2004–22: 7.6% a year (an exceptional period). AGG over a duration-6 Treasury proxy: about 0.9% a year. Break-even ERP for 4% spending: 9.4%, far above any plausible value. The ERP is **arithmetic**; the volatility drag is subtracted.
- **Plausible range:** ERP 3–6%, spread 0.3–0.9% · **Proposed:** ERP 4%, spread 0.5%
- **Sources cited:** _[owner]_
- **Team choice:** _[values]_ · **Decided by / date:** _[names, date]_

## D5 · Hypothetical shock horizon
- **Kind:** design
- **Method:** speed of past crises (06 A5)
- **Evidence:** GFC 81% of its loss in the worst quarter; COVID 15.5% in 23 days; 2022 only 52% within a quarter, over 9 months.
- **Proposed:** a cumulative peak-to-trough episode of about three quarters (2022-like), comparable with D_max; the worst quarter shown as speed.
- **Team choice:** _[value]_ · **Decided by / date:** _[names, date]_

## D6 · Notebook owners
| Notebook | Owner | Reviewer |
|---|---|---|
| 01 EDA detective | _[ ]_ | _[ ]_ |
| 02 Portfolio and frontier | _[ ]_ | _[ ]_ |
| 03 VaR, ES, EVT | _[ ]_ | _[ ]_ |
| 04 Backtesting | _[ ]_ | _[ ]_ |
| 05 Stress and regimes | _[ ]_ | _[ ]_ |
| 06 Decision | _[ ]_ | _[ ]_ |

## D7 · Hard freeze date
- **Freeze date:** _[date]_ (proposed: about 5 days before submission). After it: tag `methodology-freeze-v1`, run `final_test` once, refit to the decision date, write the memo.

## D8 · Tail-risk share cap (risk budgeting)
- **Kind:** preference / design
- **Method:** Euler 99% ES shares across the frontier (06 A6, 03 §6)
- **Evidence:** EFA's share passes 40% from 30% equity and 50% from 40% equity. A 40% cap binds where the recommendation is likely to sit and forces a resizing towards SPY.
- **Plausible range:** 35–50% · **Proposed:** 40%
- **Team choice:** _[value]_ · **Decided by / date:** _[names, date]_

## D9 · Monitoring trigger
- **Kind:** design, backtested
- **Method:** walk-forward trigger test, designed on 2008–18 and confirmed on 2019–22 (06 A7)
- **Evidence:** an automatic de-risking rule helped in the design period (N = 5: worst loss 21.2% vs 24.4%) but made things worse out of sample for every N (worst loss 20.8–21.6% vs 20.3%; lower return).
- **Proposed:** alert only. If the 99% ES forecast stays above the limit for 5 trading days, the committee is convened to review; no automatic trading.
- **Team choice:** _[rule]_ · **Decided by / date:** _[names, date]_

## D10 · How to state the verdict when the return objective is infeasible
- **Kind:** preference (the committee's mandate)
- **Evidence:** at end-2022 market levels the mandate as written (preserve real value, spend 4%, conservative risk) is not achievable with these seven ETFs, whatever the risk budget; this is robust to D4 (06 A2–A4).
- **Options for the committee:** (1) keep 4% and accept real erosion of about 1.5% a year; (2) keep real value and phase spending down to about 2.5–3%; (3) keep 4% and real value with about 100% equity and a 55% crisis loss (contradicts the committee's beliefs).
- **Framing under the brief:** "reject the mandate as proposed, with a recommended amendment" **or** "adjust, with an amended return objective".
- **Team choice and justification:** _[ ]_ · **Decided by / date:** _[names, date]_

---

## Also locked with these inputs
- **Regime definition** (notebook 01 §8): rate-hiking cycle = 3-month T-bill up by more than 1 pp over 12 months, known at t−1.
- **Pre-registered hypotheses H1–H6** (problem spec §5): wording fixed as of the lock.
- **Champion-model rule:** lowest 99% pinball loss among models passing Kupiec, Christoffersen and Basel on validation (2019–22), with GJR-GARCH added as a candidate filter **before** the lock (notebook 03 §5).
- **Decision date for the final numbers:** _[date]_ (after the freeze; the dry run uses 2022-12-30).
