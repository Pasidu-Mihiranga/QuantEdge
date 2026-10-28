# QuantEdge 1.0: Implementation To-Do List

Work top to bottom. Tick an item only when its acceptance tests pass, and add a one-line note. Plan details for each item are in `doc/steps/NN_*.md`.

Legend: `[x]` done and tested · `[~]` partial (see note) · `[ ]` not started

**Status (2026-10-28):** 199 tests pass (`pytest -m "not network"`, incl. slow tests); `ruff check` clean. All dependencies installed (latest releases). Data snapshot downloaded; Steps 03–07 and 10 run on real data. Steps 11–13, 22 M1–M4 and the app are built; LSTM training on validation in progress. Team decisions of 2026-10-28 implemented (see `doc/decisions/`); remaining freeze blockers listed in `doc/decisions/freeze_checklist.md`.

## Post-audit work (independent audit and review, 2026-10-28)

Plan: `My reserch/specs/01_problem_spec.md` (v2) and `02_gap_register.md` (v2); gap ids G1–G26.

### Phase 0: prune and fix (branch `phase0-prune-fix`)
- [x] G13: MiroFish, LightGBM, LSTM, research-paper track removed; archived at git tag `archive/mirofish-ml` (on 0a6f909). Linear QR kept; the `--with-ml` pipeline flag now runs the linear QR arena (it used to point to a script that did not exist). Tests and docs updated
- [x] G6: the scorecard Sharpe now uses excess returns over the risk-free rate (`rf` is a required argument); regression test added
- [x] G14: crisis windows start after the peak close (replay, scorecard crisis drawdown, overlay table); test added
- [x] Found while fixing G14: `max_drawdown` and the Ulcer index ignored a loss on the first day (no initial $1 in the peak). Fixed in `metrics.underwater`; test added
- [x] G15: C7 (risk-to-capital ≤ 2.0, unreachable) removed from the verdict; the ratio is still reported. ES-share sizing rule waits for decision D8
- [ ] Team decisions D1–D9 (incl. D7 hard freeze date), then the dated input lock

### Phase 1: challenge notebooks (G16, G12)
- [x] `notebooks/01_eda_detective.ipynb`: complete template (35 cells, independent of the package, data ≤ 2022): snapshot hashes, completeness, adjustment check, returns vs published figures, stale prices, extremes with events, AGG ETF-discount crashes (G7), stylised facts and ADF/KPSS, regime correlation table, reconciliation with the pipeline (identical). Finding that changed the plan: the stock–bond hedge fails in **rate-hiking cycles** (+0.30 daily) rather than when CPI > 3% (≈ 0); the definition is exploratory and must be fixed in the input lock (G8 updated)
- [x] Skeletons 02–06 (portfolio and frontier, VaR/ES/EVT, backtesting, stress and regimes, decision), question by question with gap ids; owners write code, findings and decisions
- [x] `make notebooks` / `.\make.ps1 notebooks` runs all six (`scripts/run_notebooks.py`, fails on any cell error); tooling in `requirements-notebooks.txt`, kept out of the app's requirements
- [x] Validation ladder added: notebook 01 §7 formal tests (Jarque-Bera, Ljung-Box, ARCH-LM: p ≈ 0 for all 7 ETFs) and §8b–8f for the hedge regime (Newey-West horse race, block bootstrap, residual and rank-correlation checks, out of sample 1990–2004, evidence table → decisions). Result: H1 rate-hiking regime **moderate** evidence, H2 CPI > 3% **not supported**. Skeletons 02–06 carry a "Validation required" line per question; hypotheses H1–H6 pre-registered in the problem spec
- [x] G11 (partial): `python -m quantedge.data.download --add` appends only missing series after verifying every existing hash (tested; existing files byte-identical). Added DGS2, DFII10, T10YIE (daily panel), Sri Lanka CPI as `ctx_` (context only) and the S&P 500 1989–2004 as `ext_` (out-of-sample validation only); neither prefix can enter the risk models. Only `clean_macro.parquet` changed; verdict unchanged; 197 tests. Still to do: drop the unused BAMLH0A0HYM2 at the next full refresh
- [x] Notebook 02 (portfolio and frontier, 30 cells): textbook frontier is a corner; minimum-variance frontier at fixed equity share; no cap binds from 35% equity; every point equally efficient (H6 supported) so the choice is risk appetite (+10 pp equity ≈ +0.35 pp/yr return, −3.3 pp crisis loss); 7-ETF mix earns no alpha over SPY/AGG (H5 supported); Min-CVaR 3–4× less stable than minimum variance; lookback immaterial; income covers ≈ half of 4% spending; reconciles with the pipeline exactly
- [x] Notebook 03 (VaR/ES/EVT, 26 cells): 35% equity loses ≈ USD 125–135k on a 1-in-100 day, ES ≈ USD 175k, once-a-decade USD 430–520k (range given on purpose); crisis budget D2 sets the limits (25% → ≈ 36% equity, ES limit 2.23%); **H3 rejected for the champion's plain GARCH(1,1) filter, supported for GJR-GARCH** (test GJR in notebook 04 before the freeze); EFA = 19% of capital, 47% of tail risk; EVT threshold fixed at 90% (the stability rule only picks the grid floor)
- [x] Notebook 06 Part A (evidence for D1–D9, 31 cells): **the mandate as written is infeasible at end-2022 levels**: a 25% crisis budget sustainably funds ≈ 2.4% real spending (2.1–3.0%), break-even ERP for 4% spending 9.4%; at 4% spending P(real value < 80% in 10 years) ≈ 41–49%; an automatic de-risking trigger failed out of sample (alert only); new decision **D10** (how to state the verdict). Decision record template: `doc/decisions/inputs_lock.md`
- [ ] Team meeting: choose D1–D10 with the evidence; sign `doc/decisions/inputs_lock.md`
- [ ] Notebooks 04 (backtesting, incl. GJR-GARCH candidate) and 05 (stress and regimes)
- [ ] Owners assigned (D6); each owner re-derives notebook 01's findings in their own words, fills their skeleton and signs off in `doc/ai_log.md`

## Week 1: Foundations

### Step 01: Project setup & reproducibility
- [x] Python 3.12 venv, `pyproject.toml` (src layout, editable install), pinned `requirements.txt` (76 exact pins from `uv pip freeze`), `requirements-research.txt` (torch, unpinned until first install)
- [x] `config.yaml` (v1 schema incl. `partition:`, `ml:`, `ips:`, `stress.historical`) and `load_config()` with validation — 8 tests
- [x] `quantedge.paths`, global seed handling (`cfg.rng(stream)`)
- [x] `make.ps1` / `Makefile` (setup, data, pipeline, run, test, lint)
- [x] `.gitignore`, `pytest` + `ruff` configured (lint clean); CI green on GitHub (Ubuntu + Windows, run 40570753872)
- [x] `doc/ai_log.md` started

### Step 02: Data acquisition & snapshot
- [x] `data/download.py`: yfinance prices (Close + Adj Close + Volume + actions, retry/backoff, one ticker at a time) and FRED CSV fetch
- [x] `data/manifest.py`: SHA-256 manifest write/verify
- [x] `data/load.py::load_raw()` (offline, manifest-verified)
- [x] Snapshot downloaded under `data/raw/` with `manifest.json` (not yet committed): 7 ETFs 2004-11-18 → 2026-10-26 (5,518 dates), 8 FRED series. `data.end` fixed to 2026-10-26 because the 2026-10-27 bar was intraday
- [x] Tests: FRED parsing (both date columns, "." NaN), one-byte tamper detection, offline load with sockets disabled — 4 tests

### Step 03: Cleaning, quality flags & stationarity
- [x] `CleaningLog`, `align_calendar` (inner-join ETFs; FRED carried ≤ 3 business days, logged; CPI display-only)
- [x] `quality.py`: stale, jump (trailing σ), large negative, non-positive, adjustment break, CUSUM — flags only, nothing deleted
- [x] `stats.py`: ADF + KPSS table, stylised facts (skew, kurtosis, JB, Ljung-Box r and r², ARCH-LM)
- [x] `build_clean_dataset(cfg)` → artifacts; statistics stop at 2022-12-30 until the freeze. Real run: 0 dates dropped, 25 flags (24 jumps + XLE −20.1% on 2020-03-09), all matching known events, all kept; no CUSUM breaks. Prices: unit root (EEM inconclusive, ADF p = 0.035); returns stationary (AGG inconclusive, KPSS p = 0.044). All series fat-tailed with ARCH effects; AGG excess kurtosis 71.6
- [ ] Team: confirm each flag against market events (2026-01-30 GLD −10.3% not yet verified)
- [x] Tests: planted-error series per rule, dividend-date exemption, no look-ahead in jump σ, unit root, KPSS size over 20 draws, ffill limit — 7 tests

### Step 04: Returns & portfolio accounting
- [x] `portfolio/returns.py`: simple/log returns, `risk_free_daily` (DTB3 discount → BEY → daily, lagged one day), cash asset
- [x] `risk_series`, `performance_series` (drift, quarterly rebalance, 5 bps), `to_usd`, `horizon_returns`, `build_returns`
- [x] Tests: 50/50 aggregation (and the log-average trap), buy-and-hold, daily-rebalance = risk series, costs only at quarter-ends, rf compounding and lag, cash variance — 9 tests

### Step 22 M1 (pulled forward): leakage-safe foundations
- [x] `data/partition.py`: `Partition`, `split_of`, `restrict`, `load_returns(split)`, `TestLockedError` (git-tag check)
- [x] Leakage tests: split boundaries, dev/val never return test rows, test locked without tag, real git-tag check in a temp repo — 13 tests

### Step 05: Investment Policy Statement
- [x] `decision/ips.py`: `required_return` (10-year average YoY CPI, `as_of` for no look-ahead), `IPSLimits.check`, `constraints_for_optimizer` (LP feasibility)
- [x] `ips:` block in `config.yaml`
- [x] Tests: boundary = pass, caps/floors/equity group, feasible set, infeasible limits raise — 5 tests
- [ ] Week 2: feasibility study across the frontier → `doc/decisions/ips_calibration.md` (needs the snapshot; data ≤ 2022)

### Step 06: KPIs & CAPM
- [x] `portfolio/metrics.py` (Sharpe + Lo SE, Sortino, Treynor n/m guard, IR, TE, MDD with dates, Calmar, Omega, Ulcer, `interpret`) and `portfolio/capm.py` (HAC regression, rolling beta, CAPM μ)
- [x] Tests against hand calculations, edge cases, β recovery, SPY-on-SPY exact — 10 tests

### Step 07: Portfolio construction & selection
- [x] `portfolio/optimize.py`: GMV, max-Sharpe (homogenised), ERC (Spinu + projection), min-CVaR, Robust Mean-ES, equal weight, 60/40, frontier
- [x] `portfolio/walkforward.py`: quarterly walk-forward with costs, scorecard (IPS pass → ES/MDD rank → Calmar), bootstrap
- [x] `portfolio/weights_path.py`: point-in-time weights w_τ(t) with 60/40 warm-up; PIT risk returns; ML loss target
- [x] Tests: closed forms, ERC equal contributions, IPS respected, no look-ahead, future-perturbation, scorecard — 11 tests
- [~] Scorecard run on the real snapshot via `pipeline.run_portfolio_selection` (returns read through `load_returns("dev+val")`, OOS 2008-01-02 → 2022-12-30). Ranking: GMV, Min CVaR, Robust Mean-ES, Max Sharpe, ERC, 60/40, Equal weight. **No candidate passes the IPS**: OOS 99% ES ≥ 2.4% (limit 1.5%), vol ≥ 9.1% (limit 8%), GFC drawdown ≥ 25% (limit 20%). Robust Mean-ES fell back to min-ES at 39/60 rebalances. Recommended portfolio not chosen yet (blocked on the decision below)
- [x] **Team decision 2026-10-28 (Step 05):** AGG cap raised to 65% (asset-specific caps now replace the 40% single-asset cap); all other limits kept; original AGG ≤ 40% case kept as sensitivity (`ips.variants.original_agg40`). Record: `doc/decisions/ips_calibration.md`. Pipeline rerun on the new IPS in progress
- Finding: the 60/40 benchmark itself breaches the IPS (SPY 60% > 40% cap; equity 60% > 50%) — covered by a test; mention in the report.

## Week 2: Risk layers
- [~] Step 08: HS, Normal, t (MLE ν), Cornish-Fisher (non-monotonicity flag), Monte Carlo (multivariate t, batch SE), GARCH-FHS behind `RiskModel`; `risk/diagnostics.py` (disagreement table, tail statistics, window sensitivity, draft gap sentence) — tested. `risk/horizon.py` 10-day VaR/ES (simulated GARCH-FHS paths, overlapping history, √h comparison) — 1 slow test. Min CVaR 10-day 99% ES: 6.17% by simulated paths (above the 5% reported limit; GARCH persistence ≈ 1 inflates it) vs 4.50% by history
- [x] Step 09: ES for every model (Acerbi-Tasche sample ES, closed forms, CF numeric); ES/VaR ratio table vs Normal reference; exact subadditivity demo (VaR(A+B) = 95 > −10, ES subadditive) — tested
- [~] Step 10: `risk/evt.py` — GPD MLE (agrees with scipy), profile CI for ξ (coverage ≈ 95% in 200 reps), VaR/ES/return level, parametric bootstrap CIs, mean-excess/stability/Hill, AD/KS bootstrap GOF, Rules A/B/C + sensitivity table, `EVTModel`, `ConditionalEVTModel` — 15 tests. Real run (GMV, provisional, dev+val): A and B both pick u = 85% quantile (ξ = 0.17 ± 0.04), C gives ξ = 0.24; VaR99 1.61% vs 1.59%, 1-in-10-year loss 4.0% vs 4.4%. Still to do: rerun on the recommended portfolio; team to justify the 85% grid floor or add mean-excess linearity to Rule A (both rules land on the lowest candidate); design on dev, choose on val (Step 22)
- [x] Step 22 M1 (rest): `ml/features.py` — pro-forma return lags, RV 5/20/60, EWMA, downside semivol, walk-forward GARCH σ (refit every 21 days, filtered between refits), VIX level/Δ5, Δ10y, ΔBAA10Y (FRED lagged 1 day), 60-day avg pairwise and SPY–AGG correlation, distance from 252-day high. Tests: future replaced by noise leaves features unchanged (incl. GARCH σ), pro-forma weights, FRED lag — 4 tests
- [x] Step 22 M2: `backtest/scoring.py` (pinball, FZ0, DM with Newey-West, Holm, MCS via `arch`, score table) and `backtest/coverage.py` (Kupiec, Christoffersen, binomial Basel cut-offs, plus factors, rolling-250 zones, Clopper–Pearson, `power_kupiec`). Kupiec textbook LR = 3.55; Basel 4/10 at T = 250; power to detect a doubled 99% rate at T = 1,000 ≈ 0.8; FZ0 ranks the true (VaR, ES) best — 14 tests
- [ ] Gate G2 checklist (see `doc/steps/00_INDEX.md`)

## Week 3: Validation, stress, decision, app
- [x] Step 11: `backtest/engine.py` (point-in-time weights held during each day, refit cadence, GARCH filter `update` between refits, look-ahead assertion), `backtest/es_backtest.py` (Z2 with fixed critical values), `backtest/report.py` (selection table with CIs, rolling-250 zones, Z2, pinball, FZ0; simplest passing model = champion; crisis breakdown) — 6 tests. Real run (GMV provisional, W = 500, 2008–2022, 576 s): **champion = GARCH-FHS** (simplest model passing every test on 2019–2022: 11 exceptions vs 10.1 expected, Kupiec p = 0.77, CC p = 0.26, no red rolling window, Z2 green); Conditional EVT also passes with slightly better pinball/FZ0. HS, Normal, t, CF, EVT and MC fail on clustering/coverage (Normal 19 exceptions, 30% red windows). On 2008–2018 even GARCH rejects independence (p = 0.002): GFC clustering is not fully absorbed, disclose as a limitation. Window sensitivity (`scripts/run_window_sensitivity.py`): W = 250 passes only Cornish-Fisher; W = 500 and W = 1000 both choose Conditional EVT (see the freeze checklist)
- [~] Step 12: `stress/historical.py` (replay, contributions, recovery), `stress/factor.py` (weekly factor betas, HAC; full and stress samples), `stress/hypothetical.py` (R* = B f*, portfolio SE band, duration check), `stress/reverse.py` (most likely breach, stressed Σ, calm vs stressed VaR) — 7 tests. Real run (data ≤ 2022): sanity checks pass (SPY −54.8% GFC, AGG −15.0% 2022); 2022 is the worst historical window for every optimised candidate; GMV hypothetical −15.7% ± 2.0%; stressed-correlation 99% VaR 2.67% vs 1.47% calm. Still to do: app page, re-run on the recommended portfolio. **Team decision 2026-10-28:** the five shocks are kept as initial assumptions; before the freeze the team must state the shock horizon and align the credit-spread measure (`doc/decisions/stress_scenario.md`; `stress.hypothetical.horizon` is still null)
- [~] Step 13: `risk/contributions.py` (parametric and simulation Euler VaR/ES), `decision/rules.py` (C1–C8 checks, verdict, thresholds in `config.yaml → decision`) — 17 tests incl. 13 verdict branches. `decision/sizing.py` (concentration flags, marginal swap, before/after), `decision/memo.py` (memo with `[TEAM: …]` placeholders), `decision/evidence.py` (one evidence builder shared by app, memo and tear sheet). Real run on the recalibrated IPS: **ADJUST RISK LIMIT** (Min CVaR: ES limit 1.5% → 1.63% (+9%) needs committee approval; risk-to-capital 2.62 > 2.0 needs re-sizing; return 4.27% vs 6.68% required). Memo draft: `reports/committee_memo_draft.md`. Fixed: risk-to-capital ignored residual zero weights (XLK showed 2.62 at 0%); real maximum is SPY 2.11. Verdict sensitivity (`pipeline.run_verdict_sensitivity`): ADJUST for MRP 4/5/6% (Min CVaR ignores μ), ADJUST with a cash sleeve (GMV meets every risk limit with no loosening but the return gap widens to 3.0 pts), REJECT under the original AGG ≤ 40% IPS (needs +58%). Re-sizing (`propose_resize`): reducing SPY cannot bring risk-to-capital below 2.0 within the IPS caps (reported as not achievable; C7 design question on the freeze checklist). Still to do: team writes the memo narrative **Team decision 2026-10-28:** ACCEPT / ADJUST RISK LIMIT / REJECT with a minimum-relaxation calculation across IPS-compliant candidates (minimax relative loosening, ≤ 50%) and an explicit client-approval condition for any amended limit (`decision/rules.py::minimum_relaxation`; `doc/decisions/decision_engine.md`) — 3 new tests
- [x] Step 14: (A) Markov regimes, parameters fitted on dev and filtered forward (99% ES 4.7× higher in the high-vol regime; durations 84 / 15 days); (B) volatility-target overlay with costs and a 20%/month turnover cap (into AGG barely helps and not in 2022; into T-bills cuts the GFC drawdown 17.8% → 13.5% and ES to 1.41% for −0.3 pt return); (C) t-copula with semi-parametric marginals (ν = 10.6, ES +5.1% vs Gaussian, joint-crash probability 1.9% vs 1.7% vs 2.4% observed); (D) macro and FX (stock–bond correlation 0.04 → 0.32 in 2022; +100 bp ≈ −3.5%; LKR 104.6 → 362.2 per USD, a natural hedge for rupee spending). App page 11 and report section — 10 tests
- [~] Step 22 M3–M4: `ml/quantile_models.py` — `LinearQR`, `LGBMQuantile` (early stopping on the time-ordered last 20%, SHAP via pred_contrib), row-wise rearrangement, guarded ratio ES, quantile-integral ES, leakage-safe `walk_forward_ml`, monotonicity diagnostic — 5 tests. Real arena on validation 2019–2022 (GMV provisional, champion GARCH-FHS, `score_arena`): **Linear QR has the lowest pinball** (0.0002323 vs 0.0002523, −8%), passes Kupiec/CC/rolling/Z2, FZ0 1.7% better, in the 90% MCS (p = 1.0); DM vs champion −1.08 (Holm p = 1.0, not significant) → meets adoption conditions 1–2, condition 3 (final-test confirmation) pending the freeze. LightGBM (first grid config only): pinball 0.0002475, fails Kupiec (19 exceptions, p = 0.012); its ratio-ES variant has the best FZ0 (−2.7%). Conditional EVT beats GARCH-FHS significantly (DM −3.26, Holm p = 0.006) and GARCH-FHS is outside the 90% MCS (p = 0.009). Still to do: remaining 3 LightGBM grid configs on validation; monotonicity diagnostic; SHAP summary
- [x] ~~Step 23 (LSTM)~~ **Removed 2026-10-28** (failed coverage in all 8 configs; archived at tag `archive/mirofish-ml`). Original note: Step 23: torch 2.14.1 (CPU) installed and pinned in `requirements-research.txt`; `ml/lstm_quantile.py` (ordered softplus head, pinball + FZ0 loss, train-window-only scaler, 5-seed ensemble, deterministic CPU, warm-started quarterly retrains) — 5 tests incl. leakage and determinism; `scripts/run_lstm_arena.py` trains it on validation and rescores the arena. Real run on validation with the default config (L = 60, H = 32, wd = 1e-4, 772 s): pinball 0.000240 (≈ Conditional EVT) but **27 exceptions vs 10 expected** (Kupiec p ≈ 1e-5, 12% red rolling windows): 99% VaR too low → fails adoption condition 2. Still to do: the 8-config grid on validation (also try a lower FZ0 weight); report the result either way (Paper B)
- [x] **Team decision 2026-10-28 (Step 11):** champion = lowest 99% pinball among adequately validated models on validation (`backtest.champion_rule: lowest_pinball_passing`); Conditional EVT is the provisional candidate, confirmed only after the rerun and the final test. Record: `doc/decisions/champion_rule.md`
- [~] Step 22 M6: ML grid done (`scripts/run_ml_grid.py`, 68 min; record `doc/decisions/ml_selection.md`): Linear QR meets adoption conditions 1–2 (pinball −5.3% vs Conditional EVT, passes coverage, DM not significant); LightGBM (4 configs) and LSTM (8 configs) fail coverage everywhere. Freeze tooling: `scripts/freeze.py` refuses while blocking items are open, then writes the record with hashes and prints the tag command (never tags itself). Still to do: close the blocking items in `doc/decisions/freeze_checklist.md`, then freeze
- [~] Step 15: `pipeline.py` runs every stage end to end in about 18 s with cached backtests (`--force-backtests` recomputes, about 10 min); writes `status.json` marking results provisional. Streamlit app: Home (rule-engine verdict, KPI cards, allocation, five committee answers) + 10 pages (IPS, Data & Quality, Portfolio, Risk Dashboard, Tail Risk EVT, Backtesting with Model Arena tab, Stress Testing with scenario sliders and reverse stress, Assumptions & Limitations, Methodology & AI Disclosure, Behavioural Stress Lab placeholder). `AppTest` smoke test on all 11 pages + no-torch guard — 12 tests. Still to do: estimation windows 250/1000 and 10-day horizon in the sidebar, custom-portfolio path, usability test, deploy
- [x] ~~Steps 19–20 (MiroFish)~~ **Removed 2026-10-28** (ran on paid Vertex AI against the brief's free-tier rule; archived at tag `archive/mirofish-ml`). Original note: Steps 19–20 (MiroFish): LLM = gemini-2.5-flash on Vertex AI via a local proxy (`behavioral/vertex_proxy.py`: localhost only, shared local key, hard token budget, usage log; tested live); MiroFish cloned outside the repo at 7657031 with `.env` pointing at the proxy; questionnaire schema, anonymised seed builder, BeST translation layer, scripted client and run cache built and tested (19 tests); scenarios B1–B3, R1–R4 and the Step 20 scorecard pre-registered (`doc/decisions/behavioral_preregistration.md`, SHA-256 4c04b42a…). **Waiting for:** the Zep Cloud API key, then `docker compose up` and the feasibility-gate run (one end-to-end run < 45 min, ≥ 4/5 schema-valid answers). **Team:** write the variant A analyst answers (`data/behavioral/analyst/<id>.json`) before seeing any MiroFish output
- [ ] Gate G3 checklist

## Week 4: Final test, deliverables
- [~] Step 22 M7: `python -m quantedge.backtest.final_test` is built (tag-gated, runs once, reruns must log a deviation, applies adoption condition 3) — 4 tests. Still to do: run it after the freeze; production refit
- [~] Step 16: CI green; `.streamlit/config.toml`, `-e .` in requirements for Streamlit Community Cloud; pipeline writes `artifacts_manifest.json` (SHA-256 per artifact, config hash, git commit). Still to do: reproducibility run on a second machine (compare manifests), deploy to Streamlit Community Cloud (needs the team's account)
- [~] Step 17: tear sheet (`reports/tearsheet.html`), report draft (`reports/report.html`: generated tables and figures + team narrative in `reports/narrative/*.md`, never overwritten), `AI_DISCLOSURE.md` draft, shared limitations list — 4 tests. Still to do: the team writes the narrative files; final numbers after the freeze
- [ ] Step 18: pitch deck and Q&A drills (deferred until the numbers are final after the freeze)
- [ ] Gate G4 checklist

## Deviations from the plan
- 2026-10-28: the snapshot can be extended with `download --add` (append-only, hash-checked) instead of a full refresh, so verified results do not move; new file prefixes `ctx_` (context) and `ext_` (validation history) are never loaded by `load_raw`.
- 2026-10-28: Steps 19–21 and 23 removed and LightGBM dropped after the independent audit (gap G13); archived at tag `archive/mirofish-ml`. `ml.lgbm.retrain_every` moved to `ml.retrain_every` (used by linear QR and the GARCH-sigma feature). `requirements-research.txt` and the `lightgbm` pin removed.
- 2026-10-28: crisis-window path measures now start after the peak close, and drawdowns are measured from the initial $1 (gaps G14 and the first-day-loss fix). Stress and scorecard numbers change slightly.
- Repo root is `Desktop/QuantEdge` (not a `quantedge/` subfolder as in Step 01); the package lives at the root.
- Dependencies are the latest releases (numpy 2.5.4, scipy 1.18.1, pandas 3.1.0, pyarrow 26.0.0, statsmodels 0.15.0, scikit-learn 1.9.1, arch 8.0.0, cvxpy 1.9.3, lightgbm 4.7.0, yfinance 1.7.0), installed one at a time because of an unstable network. Pins will be frozen from the working environment.
- Historical ES uses the exact Acerbi-Tasche estimator (handles fractional tail sizes) instead of "mean of the worst ⌈(1−α)n⌉ losses".
- Coverage tests live in `backtest/coverage.py` (the plan's `backtest/tests.py` name would be confused with the test suite).
- LightGBM 4.x rejects `monotone_constraints` with the quantile objective (its quantile leaf renewal would break them), so the LightGBM challenger is unconstrained and monotonicity in volatility is reported via `monotonicity_violations` instead of imposed.
- Z2 uses the fixed Acerbi–Szekely critical values at 97.5% (−0.70 at 5%, −1.80 at 0.01%) instead of model-specific simulation.
- `pyextremes` dropped: its latest release (2.5.0) requires `pandas<3`, which would downgrade pandas 3.1.0. The hand-rolled GPD MLE is cross-checked against `scipy.stats.genpareto` instead.
- Credit-spread factor: FRED now serves only the last 3 years of ICE BofA `BAMLH0A0HYM2` (from 2023-10-30), so `BAA10Y` (Moody's Baa − 10y Treasury, daily since 1986) is added as the long-history credit spread for features and stress factors.
- Cornish-Fisher reports a `monotone` flag; when the expansion is non-monotone (very fat tails) its numbers are flagged as unreliable rather than shown as valid.
