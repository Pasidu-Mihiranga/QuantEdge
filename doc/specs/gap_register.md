# 02 · Gap register: what is wrong and how we fix it

**Status:** v2: independent review applied (`03_independent_review.md`, validated in `04_review_validation.md`) · **Date:** 2026-10-28
**Sources:** independent audit (G1–G16), research gaps (G17–G21), review additions (G22–G26).
**Rule:** tick a gap only when its "Done when" condition is met **and** checked by someone other than the person who fixed it.

Severity: **H** changes the recommendation · **M** a judge would catch it · **L** polish.
Phase: **0** prune and fix · **1** challenge notebooks · **2** data · **3** decision redesign (dry run on end-2022) · **4** freeze and final test · **5** deliverables.

## Overview

| # | Sev | Gap | Phase | Status |
|---|---|---|---|---|
| G1 | H | Expected return backward-looking; required return has a small CPI look-ahead | 3 | ☐ |
| G2 | H | Selection ignores the return objective; no single recommendation rule | 3 | ☐ |
| G3 | H | Caps choose the portfolio; CAPM-only returns push it to corners | 3 | ☐ |
| G4 | H | Limits inconsistent; ES limit tied to a date-dependent forecast | 3 | ☐ |
| G5 | M | Min-CVaR less stable than GMV (defensibility) | 3 | ☐ |
| G6 | M | Scorecard Sharpe ignores the risk-free rate | 0 | ☐ |
| G7 | M | AGG ETF-discount crash risk not discussed | 1 → 3 | ☐ |
| G8 | M | Stock–bond hedge changes by **regime** (crisis, inflation), not by horizon | 1 → 3 | ☐ |
| G9 | M | Champion under-forecasts VaR by ~15%; selection not clean | 1 → 4 | ☐ |
| G10 | M | Everything stops at 2022 | 4 | ☐ |
| G11 | M | Missing data series | 2 | ☐ |
| G12 | M | No human ownership; disclosure untrue | 1 + 5 | ☐ |
| G13 | M | Scope creep (MiroFish, ML, paper track) | 0 | ☐ |
| G14 | L | Stress window off by one day | 0 | ☐ |
| G15 | L | Check C7 unreachable → replace with an ES-share sizing rule | 0 + 3 | ☐ |
| G16 | L | No exploratory notebooks | 1 | ☐ |
| G17 | L | Look-through concentration (one number) | 3 | ☐ |
| G18 | M | Withholding drag not computed | 3 | ☐ |
| G19 | M | No trial register; Sharpe comparisons use the wrong SE | 3 | ☐ |
| G20 | L | No exception log for VaR breaches | 1 | ☐ |
| G21 | M | 2025–26 episodes and decision-date macro not used | 4 | ☐ |
| G22 | M | **Income generation** not measured (brief p. 3) | 3 | ☐ |
| G23 | M | **Risk budgeting not used as a sizing action** (brief p. 8) | 3 | ☐ |
| G24 | M | **Lookback period not justified** (brief p. 3) | 3 | ☐ |
| G25 | M | **Base currency not stated** (USD vs LKR) | 3 | ☐ |
| G26 | H | **Results-aware IPS changes not disclosed**; specs claimed limits were set "blind" | 3 | ☐ |
| G27 | H | **Diversification benefits not demonstrated** (booklet p. 4) | 1 (nb 03) | ☐ |
| G28 | M | **Model performance under stressed conditions not evaluated** (booklet p. 7, Layer 4) | 1 (nb 04) | ☐ |
| G29 | M | **Investment horizon not stated and defended** (booklet p. 4, responsibility 1) | 3 + 5 | ☐ |

---

## High severity

### G1 · Expected return backward-looking; small CPI look-ahead
- **Problem:**
  - C8 compares the realised 2008–22 CAGR (4.27%) with the required return.
  - Inflation is a trailing 10-year CPI average (2.48%).
  - `required_return(as_of=2022-12-30)` includes the December 2022 CPI, which was published in mid-January 2023.
- **Root cause:** `decision/evidence.py:75` (`row.cagr`); `decision/ips.py::required_return`.
- **How to fix (problem spec §3.1):**
  1. A function for the forward geometric return: AGG = DGS10 + s_AGG; equities = DGS10 + β × ERP; GLD = π; minus σ²/2.
  2. π = T10YIE at the decision date, lagged one day. Any CPI use respects the month m+1, day-15 publication lag.
  3. Lock the ERP and s_AGG (D4) in the input record **before** the frontier is first computed.
  4. Report the ERP range 3 / 4 / 5% and the **break-even ERP** at which the verdict flips.
  5. Commit the computation as code. The audit's earlier "4.7% / 6.7%" figures came from an uncommitted calculation at the optimistic end (ERP 5%, T-bill base) and are withdrawn.
  6. Do not re-validate the starting-yield rule on our short sample (about 2 independent 5-year windows); cite the literature.
- **Where:** decision notebook; `decision/ips.py`, `decision/evidence.py`.
- **Done when:** the memo's expected return is forward-looking with its ERP sensitivity and break-even ERP; a test checks the CPI publication lag.

### G2 · Selection ignores the return objective; no single recommendation rule
- **Problem:** the scorecard ranks only by ES and drawdown. All candidates have similar Sharpe ratios, so the real choice is the risk level. The plan's "committee chooses" also risked scoring as no recommendation.
- **How to fix (spec §5):**
  - Frontier points at 15–50% equity.
  - **Recommended point** = the lowest-risk point that meets R_req and every limit.
  - The verdict follows §5 mechanically.
  - Present **one recommendation and two alternatives** with dollar trade-offs.
  - Spending changes are advice, not a verdict branch.
  - Pre-commit what happens if the champion fails on the test (§5 step 7).
- **Where:** decision notebook; a frontier stage in `pipeline.py`; app Home; memo.
- **Done when:** the memo names one point, two alternatives and the verdict, and the rule text was locked with the inputs before the first frontier run.

### G3 · Caps choose the portfolio; CAPM-only returns push it to corners
- **Problem:**
  - 119 of 239 Min-CVaR holdings sit at a cap, with AGG at its cap in 60 of 60 quarters.
  - Max Sharpe sits at the 50% equity cap every quarter, because CAPM-only returns push it to almost all equity (verified: SPY 66%, XLK 20%, EFA 10%).
  - Feeding the forward returns into mean-variance would give 0% GLD/EFA/EEM with XLK at its cap.
- **How to fix:**
  1. Frontier = **minimum variance (Ledoit-Wolf) at fixed equity share x**, under the caps.
  2. Forward returns **score** the points; they do not drive the optimiser.
  3. Keep the textbook Markowitz/CAPM frontier on the Portfolio page, with one sentence explaining its corners (Layer 1 requires it).
  4. Report binding constraints at each point and a ± 5 pp cap sensitivity.
  5. Prefer caps that do not bind at the recommended point.
- **Where:** portfolio notebook; `portfolio/optimize.py` (add `min_variance_at_equity`); `pipeline.py`.
- **Done when:** the frontier table shows non-degenerate allocations, its binding constraints and the ± 5 pp sensitivity.

### G4 · Limits inconsistent; ES limit tied to a date-dependent forecast
- **Problem:**
  - The ES99 / daily-σ ratio is 3.8–4.15, so a 1.5% ES limit implies about 5.5–6.3% volatility and the 8% volatility limit never binds. (The earlier "ES/VaR ≈ 1.2" reasoning was wrong.)
  - The memo mixed realised ES (+9%) with the champion's end-2022 forecast (+47%). Under that forecast, the verdict would change with market volatility on the decision date.
- **How to fix (spec §3.3):**
  1. One primary budget, D_max (D2), applied to max(historical replays, hypothetical).
  2. **Calibrate** the volatility and ES limits from the frontier point whose dev-data stress loss equals D_max, shown as one table. Do not use a formula.
  3. The ES limit uses a **through-the-cycle ES** (dev data including the GFC).
  4. The champion's conditional forecast becomes a **monitoring trigger** (D9).
  5. Update `decision/rules.py` so the C4 check and `minimum_relaxation` use the same measure.
- **Done when:** a test asserts that the limits are mutually consistent; the memo shows one ES number for the limit and one for monitoring, clearly labelled.

### G26 · Results-aware IPS changes not disclosed
- **Problem:**
  - The AGG cap went from 40% to 65% after seeing that nothing passed.
  - The champion rule changed after GARCH-FHS was seen to win under the old rule.
  - The first draft of the spec said the limits were set "before any results are seen", which was untrue.
- **How to fix:**
  - Keep the **IPS change log** (spec §4.1) in the report, and show the recommendation under every version.
  - Describe the limits as "set with knowledge of in-sample results; protected by the locked one-shot test and sensitivity tables".
- **Done when:** the change log is in the report, and no document claims the limits were set blind.

---

## Medium severity

### G5 · Min-CVaR less stable than GMV
- **Problem:** under bootstrap its weights vary 2–4× more than GMV's, and its turnover is 15.6% vs 8.9%. 99% CVaR on 756 days rests on about 8 tail observations. The extra cost is trivial (about 0.7 bp a year), so the argument is **defensibility, not performance**.
- **How to fix:** build the frontier with GMV / minimum variance; keep Min-CVaR as a robustness check at the same equity level.
- **Done when:** the stability table and the "~8 tail points" sentence are in the report.

### G6 · Scorecard Sharpe ignores the risk-free rate
- **How to fix:** pass `rf` to `metrics.sharpe` in `walkforward.py::scorecard`; add a test; rerun. The app shows 0.59, not 0.69.
- **Done when:** the test passes and the app value matches the audit.

### G7 · AGG ETF-discount crashes
- **Problem:**
  - AGG fell −6.84% on 10 Oct 2008, when a 5 bp yield move implied ≈ −0.25%, and −4.00% on 12 Mar 2020 against ≈ −0.30% implied.
  - Removing the 10 largest moves cuts AGG's kurtosis 10.9×, against 2.4–3.0× for the other ETFs.
- **How to fix:**
  1. In the EDA notebook, plot AGG's move against the move implied by FRED yields on those days.
  2. Use the wording "the price a forced seller would actually get" (the NAV can be stale).
  3. Add a "liquidity day" overlay to the hypothetical stress scenario.
  4. Add a governance line on which asset funds spending in a crash.
  5. Add it to the limitations page.
- **Done when:** the chart, the stress row and the limitations line exist.

### G8 · The stock–bond hedge changes by regime, not by horizon
- **Problem:**
  - The audit's "horizon effect" was a misreading. Excluding 2008Q4 and 2020Q1, SPY–AGG correlation is −0.10 daily, +0.05 at lag 1 and −0.07 weekly.
  - In the 2021–22 inflation regime it is +0.27 daily and +0.32 weekly.
  - The full-sample +0.19 comes from a few liquidity-crisis days and the inflation regime.
- **Update from notebook 01 §8 (2026-10-28):** the inflation definition (lagged CPI > 3%) was tested and **rejected** (correlation ≈ 0, not positive; the 2008 and 2011 inflation spikes had a strongly negative correlation). Rate-hiking cycles (3-month bill up > 1 pp over 12 months) give ≈ +0.30 daily / +0.34 weekly, against ≈ −0.18 otherwise, with a dose-response across 0.5 / 1 / 1.5 pp. The definition was found on dev + val data, so it is exploratory and must be fixed in the input lock before use. **Formal tests (`audit_scripts/test_hedge_regime.py`):** in-sample, the hiking interaction is significant in a Newey-West regression that also contains inflation, crisis and high-VIX interactions (daily coef +0.14, p < 0.001; weekly p = 0.003; same with a 2-year-yield definition), while inflation is not (p = 0.3–0.8); bootstrap correlation difference +0.48 [+0.27, +0.64] vs +0.12 [−0.07, +0.29] for CPI > 3%. **Out of sample (1990–2004, S&P 500 vs a Treasury proxy, definition fixed in advance):** same sign (+0.14 vs −0.01) but not significant (bootstrap CI [−0.06, +0.38]; regression p = 0.19), and only two hiking cycles (1994–95, 1999–2000). Status: consistent, moderate evidence; not proven. Claim it as such.
- **How to fix:** **drop** the planned multi-asset 10-day ES machinery. Build a **regime correlation table** (normal / liquidity crisis / rate-hiking cycle), using Pearson and Spearman. Feed it into the stagflation scenario's correlation flip and the existing `risk/regime.py`. This is the rubric's "regime-conditioned risk".
- **Done when:** the regime table is in the report and the scenario's correlation assumption cites it.

### G9 · Champion under-forecasts VaR by ~15%; selection not clean
- **Problem:**
  - Conditional EVT has 16 exceptions against 10.1 expected (Kupiec p = 0.084). Scaling its VaR by 1.154 gives exactly 10, so it **under-forecasts by about 15%** (the earlier "60%" was wrong).
  - GARCH-FHS fails (p = 0.046).
  - The champion rule changed after results were seen, and the model was chosen among 8 models × 3 windows.
- **How to fix:**
  - State the ~15% under-forecast plainly.
  - "Conservative" = the model with the **higher current ES**.
  - Record the rule change in the trial register.
  - State that validation p-values are optimistic and only the test period is clean.
  - Apply the pre-committed test rule (spec §5 step 7).
- **Done when:** the memo's model-confidence section says all of this.

### G10 · Everything stops at 2022
- **How to fix:** on the **hard freeze date (D7)**:
  1. close the freeze checklist and tag;
  2. run `final_test` once;
  3. refit to the decision date;
  4. add a "risk today" panel;
  5. extend the app slider.

  Before that, run the whole decision layer as a **dry run on end-2022 inputs** and draft the memo from it.
- **Done when:** the memo's numbers are as of the decision date and the final-test report is committed unchanged.

### G11 · Missing data
- **How to fix:**
  - Add **DFII10** and **T10YIE** (FRED, daily from 2003, lag 1 day).
  - Add **Sri Lanka inflation** (World Bank via FRED `FPCPITOTLZGLKA` (verify) or the IMF), for context only.
  - Delete the unused `BAMLH0A0HYM2`.
  - Add the decision-date macro series for G21: DFEDTARU/DFEDTARL and DCOILBRENTEU.
  - Re-download, re-hash, rerun, **before the freeze**.
  - The dot-com replay is dropped (qualitative only).
- **Done when:** the new manifest is committed and the EDA notebook shows coverage for every series.

### G12 · Ownership and disclosure
- **How to fix:**
  - One owner per notebook (D6). Each owner re-derives their layer, reconciles it, and signs off in `doc/ai_log.md`.
  - The team writes the narrative.
  - Rewrite `AI_DISCLOSURE.md` truthfully: tools, the real test count (fast suite 203 passed, 1 skipped, 8 slow deselected; 211 in total), and what was AI-generated versus human-checked.
  - The headline shows 5 VaR models (the 3 required, the champion, EVT); all 8 stay in the backtest arena tab.
  - Delete code nobody owns.
- **Done when:** every module has a named reviewer, there are no `[TEAM: …]` placeholders, and a mock Q&A passes.

### G13 · Scope creep
- **How to fix:**
  1. **Archive** under the git tag `archive/mirofish-ml`.
  2. Then delete `src/quantedge/behavioral/`, `data/behavioral/`, app page 10, Steps 19–21, `ml/lstm_quantile.py`, LightGBM, `requirements-research.txt`, `scripts/run_behavioral.py` and the vertex proxy.
  3. Keep Linear QR.
  4. Write one paragraph: "explored, rejected for fairness (paid Vertex AI) and reproducibility; deep models failed coverage".
  5. Record the changes in TODO "Deviations"; rerun the tests.
- **Done when:** the tests pass, there's no MiroFish page, and no paid service is referenced.

### G18 · Withholding drag
- **How to fix:** compute net-of-withholding returns exactly from `clean_dividends.parquet` (15% of equity distributions), and feed that into c. Limitations: AGG interest-related dividends may be exempt (§871(k)); treaty eligibility (including any exemption for tax-exempt organisations) needs professional confirmation.
- **Done when:** c uses the computed drag and the limitations page states the caveats.

### G19 · Trial register and correct comparison statistics
- **How to fix:**
  - Keep a **trial register**: every optimiser, window, threshold, model and rule change tried.
  - Compare Sharpe ratios with the **paired** standard error of the difference (Min-CVaR minus GMV: −0.012 ± 0.038; minus Max Sharpe: +0.013 ± 0.153; minus 60/40: +0.056 ± 0.173).
  - Keep the existing Holm-adjusted p-values.
  - The **deflated Sharpe ratio is dropped**, because selection is no longer made on Sharpe.
- **Done when:** the register and the paired-SE table are in the report.

### G21 · 2025–26 context
- **How to fix:**
  - Before the freeze, describe the April 2025 and March 2026 windows as pre-registered extra historical scenarios.
  - After the freeze, compute them.
  - Take the decision-date policy range, CPI and Brent **from FRED in code** (G11), not from news.
- **Done when:** both windows are in the stress table and every macro number in the memo comes from code.

### G22 · Income generation
- **How to fix:** for each frontier point, report the trailing 12-month distribution yield net of withholding, and the share of 4% spending it covers.
- **Done when:** the frontier table and memo have an income column and sentence.

### G23 · Risk budgeting as a sizing action
- **How to fix:**
  - Add a Euler ES-share table for the recommended point.
  - Rule (D8): if any asset's ES share exceeds X%, cap it and restate the result.
  - Add one explicit sizing sentence, for example "SPY is 10% of capital but 22% of ES; …".
  - This replaces C7 (G15).
- **Done when:** the memo has the table and the sizing sentence.

### G24 · Lookback justification
- **How to fix:** one paragraph (756-day optimiser, 500-day risk window), plus the existing 250 / 500 / 1000 sensitivity table.
- **Done when:** it is in the report's methodology section.

### G25 · Base currency
- **How to fix:** state USD and US CPI as the base (an assumption); add one LKR-terms sensitivity line (LKR 104.6 → 362.2 per USD, 2004–22) and one Sri Lanka CPI paragraph.
- **Done when:** the spec, memo and limitations page say it.

---

## Found in the booklet traceability check (2026-10-28)

### G27 · Diversification benefits not demonstrated
- **Problem:** the committee "requires managers to demonstrate diversification benefits" (p. 4). Notebook 02 showed the seven-ETF mix earned no extra **return** over SPY/AGG, and nothing yet shows the benefit in **risk** terms.
- **How to fix:** notebook 03 §8: (1) ES diversification saving = Σ wᵢ·ESᵢ − ES_portfolio, in dollars; (2) diversification ratio = Σ wᵢσᵢ / σ_p; (3) crisis loss of the portfolio vs the weighted sum of its assets' crisis losses; (4) the same in calm vs crisis periods, to show how much of the benefit survives stress (links to the regime finding).
- **Done when:** the memo states the dollar risk saving and how much of it survives a crisis.

### G28 · Model performance under stressed conditions
- **Problem:** Layer 4 asks teams to "evaluate how different modelling approaches perform under stressed market conditions" (p. 7); the notebook 04 plan only scored whole periods.
- **How to fix:** notebook 04 §7: each model's exceptions vs expected, Kupiec p, and pinball/FZ0 inside the GFC, COVID and 2022 windows (the pipeline's `backtest_crises_500.parquet` is the reconciliation target).
- **Done when:** the report has a crisis-window model table and one sentence on which models fail in stress.

### G29 · Investment horizon
- **Problem:** the booklet asks the manager to "determine what the appropriate investment horizon … should be, and defend your recommendation" (p. 4); the spec had horizons but no defended statement.
- **How to fix:** horizon statement in the spec (§9) and `inputs_lock.md`: perpetual fund, objective judged on a 10-year rolling horizon, risk monitored at 1/10 days and budgeted per crisis. One sentence in the memo and the IPS page.
- **Done when:** memo and app state it in those words.

## Low severity

| # | Fix | Done when |
|---|---|---|
| G14 | `stress/historical.py::replay`: start from the first return **after** `start`; update the test | 2022 replay = −14.65% |
| G15 | Remove the unreachable C7; replace it with the G23 ES-share rule in `decision/rules.py` and its tests | Tests pass with the new rule |
| G16 | **5–6 notebooks, one per owner:** (1) EDA detective, (2) portfolio and frontier, (3) VaR/ES/EVT, (4) backtesting, (5) stress and regimes, (6) decision. Run with one `make notebooks` target, not in CI | All run top to bottom on a clean clone |
| G17 | One look-through top-5 exposure number for the recommended point, from `yfinance` `Ticker.funds_data.top_holdings` (approved source), or described qualitatively | Number or sentence in the memo |
| G20 | Exception log: every validation-period 99% breach with date, loss, VaR and a one-line cause | Table in the report appendix |

## Order of work

1. **Phase 0 (code only, now):**
   - G6, G13 (archive tag first), G14;
   - G15 (remove C7; the new rule waits for D8);
   - clean the audit scripts.
2. **Decisions D1–D9**, including **D7, the hard freeze date**, then **lock the inputs** (spec §5 step 1).
3. **Phase 1:** notebooks (G16) with owners (G12 start), including G7, G8 and G20 in the EDA, backtest and stress notebooks.
4. **Phase 2:** G11 data.
5. **Phase 3, as a dry run on end-2022 inputs:**
   - G1, G4, G26, G3, G5, G2;
   - G22–G25, G18, G19, G17;
   - draft the memo and tear sheet in parallel.
6. **Phase 4, on the freeze date:** G9, G10, G21.

**Added after the booklet traceability check:** G27 (notebook 03) and G28 (notebook 04) belong to Phase 1; G29 to Phases 3 and 5. **Never cut:** G27–G29 (the booklet names them).
7. **Phase 5:** G12 finish; deliverables.

**If time runs short, cut in this order:** G17 → G20 → the 10-year simulation's sensitivity rows → the Min-CVaR robustness check → the volatility-target overlay page. **Never cut:** G1–G4, G10, G22–G26.
