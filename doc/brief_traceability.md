# Booklet traceability: every requirement, where it is met, and its status

Source: `Quant edge 1.0 Final Challenge 1.pdf` (pages as printed). Checked 2026-10-28 against commit `04cab24` plus the decisions in `doc/decisions/inputs_lock.md`.
Status: ✅ met · 🟡 partly met (what is missing is stated) · ⬜ open.
Gap ids (G..) refer to the team's gap register; D.. to `doc/decisions/inputs_lock.md`.

## 1. The official brief (p. 3)

| # | Requirement | Where it is met | Status |
|---|---|---|---|
| 1 | Construct and recommend a portfolio from the universe using quantitative techniques | `portfolio/optimize.py`, `walkforward.py`; notebook 02 (minimum-variance frontier) | 🟡 recommendation computed in notebook 06 Part B after the lock |
| 2 | Measure and compare risk with VaR, ES and EVT | `risk/`; notebook 03; app pages 4–5 | ✅ |
| 3 | Validate the risk models with out-of-sample backtesting | `backtest/`; app 'Can we trust the risk model?'; notebook 04 §9 (production and notebook agree on the test) | ✅ final test run once 2026-10-29: champion passes (9 vs 9.6 breaches, Kupiec p 0.86, CC p 0.19) |
| 4 | Evaluate behaviour under historical and hypothetical stress | `stress/`; app 'What can go wrong?'; notebook 05 (replays, "Hormuz stagflation 2027" with severity calibration, reverse stress) | ✅ (D5 sizes agreed) |
| 5 | Clear recommendation in an investment committee memorandum | `decision/`; memo draft; D10 | ⬜ memo written by the team after Part B |
| 6 | Justify the approach, risk metrics, lookback and construction method | `inputs_lock.md`; notebook 02 §5 (lookback); spec §3 | 🟡 report section to write |
| — | Define a suitable portfolio, justify assumptions, communicate limitations | App 'Assumptions & Limitations' and 'What did we promise?'; `reports/limitations.py`; inputs_lock | ✅ rewritten with D1–D10 (2026-10-29) |

## 2. Manager's responsibilities (p. 4)

| # | Requirement | Where it is met | Status |
|---|---|---|---|
| 1 | Determine and defend the investment horizon and allocation | Horizon statement (G29, inputs_lock); allocation in notebook 06 Part B | 🟡 statement agreed; memo sentence and allocation pending |
| 2 | Return objective consistent with mandate and risk tolerance | **CPI + 3.5%** (D1 + growth margin, D10); notebook 06 A2–A4 | ✅ agreed; recomputed at the decision date |
| 3 | Define and justify the risk constraints | D2 (crisis budget → volatility and ES limits), D3 caps, D8 ES-share cap; notebook 03 §4 | ✅ agreed |
| 4 | Show why the portfolio suits a conservative institution | Memo; notebooks 02–03 evidence | ⬜ memo |
| 5 | Quantify the return-seeking vs risk-reduction trade-off | Notebook 02 §4 (per 10 pp of equity: +0.35 pp a year, −3.3 pp crisis loss); notebook 06 A2b | ✅ (dry run; refresh at the decision date) |
| 6 | Articulate the assumptions | inputs_lock; app 'Assumptions & Limitations' | ✅ |
| 7 | Downside protection and tail-risk management | Notebook 03 (VaR, ES, EVT, GARCH); D2; D9 alert | ✅ |
| 8 | Robustness under stress scenarios | Notebook 05: within the 25% budget in every required crisis; only a combined severe stagflation breaks it | ✅ |
| 9 | Optional: other macro, industry or market risks | Notebook 01 §8 (rate-hiking regime, tested), macro and LKR analysis (Step 14 D), Sri Lanka CPI (World Bank via FRED) | 🟡 to summarise in the report |

## 3. What the committee requires managers to demonstrate (p. 4)

| # | Requirement | Where it is met | Status |
|---|---|---|---|
| 1 | **Diversification benefits** | Notebook 03 §8: ES saving in dollars, diversification ratio, crisis comparison (G27) | 🟡 added 2026-10-28; to be re-derived by the owner |
| 2 | Robust risk measurement | Notebook 03; notebook 04 (champion GJR conditional EVT; H3 partly supported) | ✅ |
| 3 | Tail-risk awareness | Notebook 03 §3 (EVT, once-in-a-decade range) | ✅ |
| 4 | Practical stress testing | Notebook 05 (validated factor mapping, liquidity day, reverse stress) | ✅ |
| 5 | Portfolio resilience during crises | Crisis replays; D2 budget; notebook 03 §4 | 🟡 memo statement |
| — | Explain what can go wrong / how bad / how confident | Limitations page; notebook 03 dollar figures; EVT ranges; backtests; evidence tables | 🟡 memo and Q&A bank |

## 4. Investable universe (p. 5)

| Requirement | Where it is met | Status |
|---|---|---|
| Only SPY, EFA, EEM, AGG, GLD, XLE, XLK | `config.yaml → universe`; no other asset in any portfolio (cash only as a labelled sensitivity) | ✅ |

## 5. Technology and the Streamlit app (pp. 5–6)

| # | Requirement | Where it is met | Status |
|---|---|---|---|
| — | Python for all analysis; Streamlit interface; free-tier toolkit | Repo; MiroFish (paid LLM) removed | ✅ |
| 1 | Sidebar: confidence 90/95/99%, VaR methodology, backtest date range | `app/components/sidebar.py` | 🟡 date range stops at 2022 until the freeze (G10) |
| 2 | Portfolio panel: weights, cumulative return, drawdown chart | App 'How is the money invested?' (drawdown chart fixed: lines, not stacked areas) | ✅ |
| 3 | Risk dashboard: VaR, ES and EVT side by side at the same confidence | App pages 4–5 | ✅ |
| 4 | Backtesting panel: Kupiec/Christoffersen and a traffic light | App 'Can we trust the risk model?' (2008–2026, one-shot test marked) | ✅ |
| 5 | Stress-test panel: impact under each crisis scenario | App 'What can go wrong?' (every crisis in dollars, scenario builder, reverse stress) | ✅ |
| 6 | "Assumptions & Limitations" page, plain language (graded) | App 'Assumptions & Limitations' | ✅ |

## 6. Deliverables (p. 6)

| # | Requirement | Where it is met | Status |
|---|---|---|---|
| 1 | Public/judge-accessible GitHub repo, clean code, README on how to run | Repo; README | 🟡 README to refresh; repo visibility to confirm |
| 2 | App deployed, or runnable locally with one command | `make run` / `.\make.ps1 run` | 🟡 deployment to Streamlit Community Cloud pending (needs the team's account) |
| 3 | 7–15-page report: methodology, data and cleaning, results, assumptions and limitations | `reports/report.html` generator; `reports/narrative/` | ⬜ narrative written by the team after the freeze |
| 4 | One-page executive tear sheet | `reports/tearsheet.html` generator | 🟡 final numbers after the freeze |
| 5 | Finalists: 10–12-minute pitch and deck; Q&A as the committee | — | ⬜ |

## 7. Technical layers (pp. 6–7)

| Layer | Requirement | Where it is met | Status |
|---|---|---|---|
| 1 | Markowitz mean-variance and CAPM; KPIs: Sharpe, Sortino, Treynor, Jensen's alpha, Information Ratio, max drawdown, Calmar, with interpretation | `portfolio/metrics.py`, `capm.py`; notebook 02 §1, §4 | ✅ |
| 2 | Historical, parametric and Monte Carlo VaR at 95% and 99% on the same portfolio; discuss where and why they disagree; evaluate assumptions | `risk/var.py`, `montecarlo.py`; notebook 03 §1 | ✅ |
| 3 | ES with a rationale for using it alongside VaR | Notebook 03 §2 (tail severity, subadditivity) | ✅ |
| 4 | EVT; **how different approaches perform under stressed conditions**; limitations of conventional measures; justified threshold | `risk/evt.py`; notebook 03 §3 (threshold justified); notebook 04 §5 (six models in the GFC, COVID and 2022 windows, G28) | ✅ |
| 5 | Out-of-sample backtest with Kupiec, Christoffersen and Basel traffic light | `backtest/coverage.py`, `engine.py`; notebook 04 (six models on the recommended portfolio; champion GJR conditional EVT) | 🟡 validation done; final test once after the freeze |

## 8. From metrics to decisions (p. 8)

| Requirement | Where it is met | Status |
|---|---|---|
| Risk budgeting and position sizing with each position's marginal VaR/ES contribution | `risk/contributions.py`; notebook 03 §6; D8 (40% cap) | 🟡 the sizing action itself in notebook 06 Part B |
| Historical crisis paths (2008, March 2020, 2022) plus one team-designed hypothetical | `stress/historical.py` (window start fixed, G14), `hypothetical.py`; notebook 05 | ✅ (D5 sizes agreed) |
| One-page plain-English memo: accept / adjust the risk limit / reject | `decision/memo.py`; D10 | ⬜ team-written memo |

## 9. Use of AI (pp. 8–9)

| Requirement | Where it is met | Status |
|---|---|---|
| Disclose tools, purpose, human validation, material AI components | `AI_DISCLOSURE.md`; `doc/ai_log.md` | 🟡 reviewer sign-offs pending |
| The team can explain any part of the code, method, analysis or recommendation | Notebook owners re-derive their layer (D6) | ⬜ owners to assign |
| Recommendations developed and defended by the team | inputs_lock signed by the team; human-written memo | 🟡 |

## 10. Data sources and governance (p. 9)

| Requirement | Where it is met | Status |
|---|---|---|
| Approved sources only: Yahoo (yfinance), FRED, World Bank/IMF | `data/download.py`; manifest; Sri Lanka CPI is World Bank data via FRED; the ERP is a disclosed assumption (D4), not data | ✅ |
| Adjusted close prices | Notebook 01 §2 (verified against close + dividends) | ✅ |
| Align trading calendars and document holiday handling | `data/cleaning.py` log; notebook 01 §1 | ✅ |
| Log returns for statistical work; state where simple returns are used and why | AGENTS.md convention; notebooks 01–03 | 🟡 one paragraph in the report |
| Flag, don't delete, suspected errors; document outlier handling | `data/quality.py`; notebook 01 §4–6 | ✅ |
| Stationarity check (e.g. ADF) on modelled returns | `data/stats.py`; notebook 01 §7 | ✅ |
| Every cleaning step reproducible from code | Pipeline; reproducibility check on a second machine passed | ✅ |

## 11. Rubric (p. 10)

| Criterion | Weight | Our main evidence | Biggest open item |
|---|---|---|---|
| Investment decision-making (incl. optional items) | 30% | Return objective CPI + 3.5%, decision evidence pack, price list of equity, macro/regime analysis | Part B verdict and the memo |
| Technical rigour and correctness | 25% | Independent audit, validation ladder, hypothesis tests, backtests | Notebook 04 (GJR-GARCH), final test |
| Software and interface quality | 15% | Mandatory app items, one-command run, tests, reproducibility | Deployment to Streamlit Community Cloud |
| Innovation and ambition | 15% | Regime-conditioned risk (tested), EVT threshold rules, risk overlay and trigger (validated, including a negative result) | Present them clearly in the report |
| Communication and defence | 15% | Notebooks with owners | Owners (D6), memo, deck, Q&A bank |
