# Booklet traceability: every requirement, where it is met, and its status

Source: `Quant edge 1.0 Final Challenge 1.pdf` (pages as printed). First checked 2026-10-28; deliverables re-checked 2026-10-31 against the booklet pages.
Status: ✅ met · 🟡 partly met (what is missing is stated) · ⬜ open.
Gap ids (G..) refer to the team's gap register; D.. to the team's numbered decisions.

## 1. The official brief (p. 3)

| # | Requirement | Where it is met | Status |
|---|---|---|---|
| 1 | Construct and recommend a portfolio from the universe using quantitative techniques | `portfolio/optimize.py`, `walkforward.py`, `decision/decision_date.py`; notebooks 02 and 06 Part B | ✅ ACCEPT at 35% equity on 2026-10-26 |
| 2 | Measure and compare risk with VaR, ES and EVT | `risk/`; notebook 03; app 'Risk and confidence' (A bad day, Compare every model, Why the models disagree) | ✅ |
| 3 | Validate the risk models with out-of-sample backtesting | `backtest/`; app 'Risk and confidence' → 'Is the model right?'; notebook 04 §9 (production and notebook agree on the test) | ✅ final test run once 2026-10-29: champion passes (9 vs 9.6 breaches, Kupiec p 0.86, CC p 0.19) |
| 4 | Evaluate behaviour under historical and hypothetical stress | `stress/`; app 'What can go wrong' (replays, scenario builder with plausibility, reverse stress); notebook 05 (replays, "Hormuz stagflation 2027" with severity calibration, reverse stress) | ✅ (D5 sizes agreed) |
| 5 | Clear recommendation in an investment committee memorandum | `reports/Investment_Committee_Memo.pdf` | 🟡 draft with final numbers; the team reviews and rewrites it |
| 6 | Justify the approach, risk metrics, lookback and construction method | Report sections 2–6; notebook 02 §5 | ✅ |
| — | Define a suitable portfolio, justify assumptions, communicate limitations | App 'Assumptions & Limitations' (every limit with room left and its source, first draft → agreed, 24 limitations with mitigations); `reports/limitations.py` | ✅ rewritten with D1–D10 (2026-10-29) |

## 2. Manager's responsibilities (p. 4)

| # | Requirement | Where it is met | Status |
|---|---|---|---|
| 1 | Determine and defend the investment horizon and allocation | Report sections 2 and 4; memo | ✅ |
| 2 | Return objective consistent with mandate and risk tolerance | **CPI + 3.5%** (D1 + growth margin, D10); notebook 06 A2–A4 | ✅ agreed; recomputed at the decision date |
| 3 | Define and justify the risk constraints | D2 (crisis budget → volatility and ES limits), D3 caps, D8 ES-share cap; notebook 03 §4 | ✅ agreed |
| 4 | Show why the portfolio suits a conservative institution | Report section 9; memo | ✅ |
| 5 | Quantify the return-seeking vs risk-reduction trade-off | Notebook 02 §4 (per 10 pp of equity: +0.35 pp a year, −3.3 pp crisis loss); notebook 06 A2b | ✅ (dry run; refresh at the decision date) |
| 6 | Articulate the assumptions | App 'Assumptions & Limitations' | ✅ |
| 7 | Downside protection and tail-risk management | Notebook 03 (VaR, ES, EVT, GARCH); D2; D9 alert | ✅ |
| 8 | Robustness under stress scenarios | Notebook 05: within the 25% budget in every required crisis; only a combined severe stagflation breaks it | ✅ |
| 9 | Optional: other macro, industry or market risks | Report section 8; app 'Regimes, overlay, copula, FX'; notebook 01 §8 | ✅ |

## 3. What the committee requires managers to demonstrate (p. 4)

| # | Requirement | Where it is met | Status |
|---|---|---|---|
| 1 | **Diversification benefits** | Notebook 03 §8 (G27); app 'Risk and confidence' → 'Diversification' (bad-day saving in dollars, each crisis fund by fund vs together, correlations by crisis) | 🟡 app done 2026-10-29; notebook to be re-derived by the owner |
| 2 | Robust risk measurement | Notebook 03; notebook 04 (champion GJR conditional EVT; H3 partly supported) | ✅ |
| 3 | Tail-risk awareness | Notebook 03 §3 (EVT, once-in-a-decade range) | ✅ |
| 4 | Practical stress testing | Notebook 05 (validated factor mapping, liquidity day, reverse stress) | ✅ |
| 5 | Portfolio resilience during crises | Crisis replays; D2 budget; report section 8; memo | ✅ |
| — | Explain what can go wrong / how bad / how confident | Memo sections of the same names; limitations page; report sections 5, 6 and 8 | ✅ written; 🟡 Q&A rehearsal open |

## 4. Investable universe (p. 5)

| Requirement | Where it is met | Status |
|---|---|---|
| Only SPY, EFA, EEM, AGG, GLD, XLE, XLK | `config.yaml → universe`; no other asset in any portfolio (cash only as a labelled sensitivity) | ✅ |

## 5. Technology and the Streamlit app (pp. 5–6)

| # | Requirement | Where it is met | Status |
|---|---|---|---|
| — | Python for all analysis; Streamlit interface; free-tier toolkit | Repo; MiroFish (paid LLM) removed | ✅ |
| 1 | Sidebar: confidence 90/95/99%, VaR methodology, backtest date range | `app/components/controls.py` (shown on 'Risk and confidence', only where each control changes the view) | ✅ 2008–2026 |
| 2 | Portfolio panel: weights, cumulative return, drawdown chart | App 'Our recommendation' (weights) and 'Compare portfolios' (growth and falls from the peak, against 60/40) | ✅ |
| 3 | Risk dashboard: VaR, ES and EVT side by side at the same confidence | App 'Risk and confidence' → 'A bad day' | ✅ |
| 4 | Backtesting panel: Kupiec/Christoffersen and a traffic light | App 'Risk and confidence' → 'Is the model right?' (2008–2026, one-shot test marked, pass/fail per test) | ✅ |
| 5 | Stress-test panel: impact under each crisis scenario | App 'What can go wrong' (every crisis in dollars, scenario builder whose parts add up to the total, plausibility, reverse stress) | ✅ |
| 6 | "Assumptions & Limitations" page, plain language (graded) | App 'Assumptions & Limitations' | ✅ |

## 6. Deliverables (p. 6)

| # | Requirement | Where it is met | Status |
|---|---|---|---|
| 1 | Public/judge-accessible GitHub repo, clean code, README on how to run | README written for judges, with screenshots | 🟡 README done; work must be pushed to the public repository |
| 2 | App deployed, or runnable locally with one command | `make run` / `.\make.ps1 run` build the environment on first use; `deploy/` installs it on a server | ✅ one command; ✅ live at https://quantedge.gmora.dev |
| 3 | 7–15-page report: methodology, data and cleaning, results, assumptions and limitations | `reports/QuantEdge_Technical_Report.pdf` (13 pages, a test enforces the limit) | 🟡 complete draft; the team reviews and rewrites it |
| 4 | One-page executive tear sheet | `reports/Executive_Tear_Sheet.pdf`, from `decision_numbers.json` | ✅ one A4 page, a test enforces it |
| 5 | Finalists: 10–12-minute pitch and deck; Q&A as the committee | — | ⬜ |

## 7. Technical layers (pp. 6–7)

| Layer | Requirement | Where it is met | Status |
|---|---|---|---|
| 1 | Markowitz mean-variance and CAPM; KPIs: Sharpe, Sortino, Treynor, Jensen's alpha, Information Ratio, max drawdown, Calmar, with interpretation | `portfolio/metrics.py`, `capm.py`; notebook 02 §1, §4; app 'Compare portfolios' → 'The scorecard' (since 2008 or 2023 onwards) | ✅ |
| 2 | Historical, parametric and Monte Carlo VaR at 95% and 99% on the same portfolio; discuss where and why they disagree; evaluate assumptions | `risk/var.py`, `montecarlo.py`; notebook 03 §1; app 'Why the models disagree' | ✅ |
| 3 | ES with a rationale for using it alongside VaR | Notebook 03 §2 (tail severity, subadditivity) | ✅ |
| 4 | EVT; **how different approaches perform under stressed conditions**; limitations of conventional measures; justified threshold | `risk/evt.py`; notebook 03 §3 (threshold justified); notebook 04 §5 (six models in the GFC, COVID and 2022 windows, G28) | ✅ |
| 5 | Out-of-sample backtest with Kupiec, Christoffersen and Basel traffic light | `backtest/coverage.py`, `engine.py`; notebook 04; report section 6 | ✅ validation and the one-shot test |

## 8. From metrics to decisions (p. 8)

| Requirement | Where it is met | Status |
|---|---|---|
| Risk budgeting and position sizing with each position's marginal VaR/ES contribution | `risk/contributions.py`; notebook 03 §6; D8 (40% cap); app 'Our recommendation' → 'Where the risk comes from' (money, bad-day ES and scenario shares) | ✅ D8 applied at the decision date |
| Historical crisis paths (2008, March 2020, 2022) plus one team-designed hypothetical | `stress/historical.py` (window start fixed, G14), `hypothetical.py`; notebook 05 | ✅ (D5 sizes agreed) |
| One-page plain-English memo: accept / adjust the risk limit / reject | `reports/committee_memo_draft.md` (`reports/final.py`); D10 | 🟡 draft with final numbers; the team reviews and rewrites it |

## 9. Use of AI (pp. 8–9)

| Requirement | Where it is met | Status |
|---|---|---|
| Disclose tools, purpose, human validation, material AI components | `AI_DISCLOSURE.md` | 🟡 team confirmation and reviewer sign-offs pending |
| The team can explain any part of the code, method, analysis or recommendation | Notebook owners re-derive their layer (D6) | ⬜ owners to assign |
| Recommendations developed and defended by the team | Decisions signed by the team; human-written memo | 🟡 |

## 10. Data sources and governance (p. 9)

| Requirement | Where it is met | Status |
|---|---|---|
| Approved sources only: Yahoo (yfinance), FRED, World Bank/IMF | `data/download.py`; manifest; Sri Lanka CPI is World Bank data via FRED; the ERP is a disclosed assumption (D4), not data | ✅ |
| Adjusted close prices | Notebook 01 §2 (verified against close + dividends) | ✅ |
| Align trading calendars and document holiday handling | `data/cleaning.py` log; notebook 01 §1 | ✅ |
| Log returns for statistical work; state where simple returns are used and why | Report section 3; AGENTS.md convention | ✅ |
| Flag, don't delete, suspected errors; document outlier handling | `data/quality.py`; notebook 01 §4–6 | ✅ |
| Stationarity check (e.g. ADF) on modelled returns | `data/stats.py`; notebook 01 §7 | ✅ |
| Every cleaning step reproducible from code | Pipeline; reproducibility check on a second machine passed | ✅ |

## 11. Rubric (p. 10)

| Criterion | Weight | Our main evidence | Biggest open item |
|---|---|---|---|
| Investment decision-making (incl. optional items) | 30% | ACCEPT at 35% from a pre-fixed rule, return objective CPI + 3.5%, macro/regime analysis | The team's rewrite of the memo |
| Technical rigour and correctness | 25% | Independent audit, validation ladder, one-shot test, reconciled notebooks | Each owner re-deriving their layer |
| Software and interface quality | 15% | Mandatory app items, one-command run, tests, reproducibility | — |
| Innovation and ambition | 15% | Regime-conditioned risk (tested), EVT threshold rules, risk overlay and trigger (validated, including a negative result) | Pitch deck |
| Communication and defence | 15% | Memo, tear sheet, report, decision-defence document | Owners (D6), deck, Q&A rehearsal |
