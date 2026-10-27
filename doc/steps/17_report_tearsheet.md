# Step 17: Technical Report, Executive Tear Sheet & AI Disclosure

**Owner:** C (editor) with all section owners · **Week:** 4 (outline from Week 2) · **Effort:** 4 days · **Depends on:** 13, 15 · **Feeds:** submission, 18

## 1. Target

- A **12–14 page technical report / investment memo** (the brief allows 7–15) covering methodology, data sources and cleaning, results, and **explicitly** assumptions and limitations.
- A **one-page executive tear sheet** that a real committee can read in under 5 minutes, **auto-generated from the pipeline artifacts**.
- A complete **AI disclosure** in the format of brief §8.7.
- Every number in the report, tear sheet, app and deck comes from the same artifacts (single source of truth).

## 2. Why it matters

- Brief §7.3–7.4 deliverables. Brief §8.6: the memo is a one-page plain-English recommendation. Brief §8.7: AI disclosure is mandatory.
- Rubric: communication and defence (15%), plus the written support for decision-making (30%).

## 3. How to achieve it

### 3.1 Report outline (page budget)

| § | Section | Pages | Owner |
|---|---|---|---|
| 0 | Executive summary: verdict, allocation, 5 key numbers | 1 | C |
| 1 | Client mandate and IPS: return derivation, risk tolerance, limits and why | 1.5 | P |
| 2 | Data: sources, snapshot, cleaning log summary, flags, stationarity, stylised facts | 1 | D |
| 3 | Portfolio construction: candidates, inputs (Ledoit-Wolf, CAPM/BL), frontier, trade-off table, walk-forward scorecard, stability | 2 | P |
| 4 | Risk measurement: VaR (6 models), disagreement analysis, ES rationale, EVT (threshold evidence, rule comparison, return level) | 2.5 | R |
| 5 | Model validation: partition × walk-forward design, Kupiec, Christoffersen, rolling-250 Basel, Z2, exception-rate CIs and the power caveat; model choice | 1.5 | V |
| 5b | **Champion–challenger and final test:** LightGBM, LSTM and linear QR vs the champion; primary metric and adoption decision; DM/MCS; the freeze record (tag, hashes); final-test result reported as-is | 0.5–1 | R |
| 6 | Stress testing: 3 historical, hypothetical (factor model), reverse, stressed correlation | 1.5 | V |
| 6b | Behavioural Stress Lab (MiroFish): design, compliance controls, translation layer, **with vs without scorecard (MVS and BRS out of 100)**, adoption decision | 1 | V |
| 7 | Risk budget and recommendation: Euler contributions, decision checks, verdict, sensitivity, governance triggers | 1 | P |
| 8 | **Assumptions and limitations** (explicit, plain language) | 1 | all |
| 9 | AI disclosure, references, appendix (formulas, app screenshots, reproducibility) | 1 | C |

**Writing rules:**
- Every number has units, horizon and confidence.
- Every chart has a takeaway title (e.g. "Normal VaR understates 99% risk by 18%", not "VaR comparison").
- Every method states its assumption, why it is appropriate and when it fails.
- Use "we" and the team's own judgement. No AI-written conclusions are pasted in unreviewed.

Tooling: Markdown sources in `reports/report/`, with figures exported from the same Plotly functions (`fig.write_image` via kaleido). Build to PDF via pandoc, or Word for final formatting.

### 3.2 Executive tear sheet (one A4 page; `reports/tearsheet.py`)

Layout (generated as HTML, then PDF):
- **Header:** "Serendib University Endowment: Recommended Portfolio", date, and the **verdict badge**.
- **Left column:** allocation donut and table (% and USD), expected return versus the required return, volatility.
- **Right column:** a risk table (1-day 95/99% VaR, ES and EVT in USD; 10-day 99% ES; once-in-10-years loss), the backtest traffic light and test results, and stress losses for the 3 crises plus the hypothetical scenario (USD and %).
- **Bottom:** three plain-English bullets ("What you get / What could go wrong / How we will monitor"), the top three limitations, and the governance triggers.
- **Auto-checks before export:** page count = 1; no NaN values; every number matches the artifacts.

### 3.3 Assumptions & Limitations (shared with app page 8)

Grouped list. Each item gives the assumption, its consequence and our mitigation:
- **Data:** history may not represent the future; 20-year sample; one snapshot date; ETF tracking error; no intraday data.
- **Validation:** only about 10 expected 99% exceptions per 4-year period, so the tests have low power; the 2023+ test period contains no major crisis; ML models were trained on about 35 tail days in development.
- **Models:** volatility is time-varying (handled by GARCH, but parameters are uncertain); EVT is estimated from few points with wide confidence intervals; the copula is static; the Normal model is shown only as a benchmark; √t scaling is approximate.
- **Portfolio:** μ estimates are uncertain (CAPM/MRP assumption); rebalancing costs are approximated; no liquidity or market-impact modelling in a crisis; fully invested assumption (cash only as a sensitivity).
- **Stress:** historical paths may not repeat; factor betas are unstable across regimes; the hypothetical scenario is one of many possible.
- **Scope:** no derivatives or margin (universe rule); USD base while spending is in LKR; no ESG or tax modelling.

### 3.4 AI disclosure (`AI_DISCLOSURE.md`, the report appendix and app page 9)

| Item | Disclosure |
|---|---|
| AI tool(s) used | Claude (Anthropic) via Claude Code; **MiroFish** multi-agent simulator (666ghj/MiroFish, AGPL-3.0, pinned commit) with the named open-weights LLM via Ollama and Zep Cloud (free tier); list any others the team used (ChatGPT, Copilot) |
| Purpose | Code implementation of modules to the team's specification, test scaffolding, Streamlit layout, documentation drafting, debugging |
| Human validation | Each module reviewed and signed off by a named member; validated with closed-form, simulation-recovery and textbook tests (Step 16); results cross-checked with independent libraries (scipy, pyextremes, statsmodels); manual sanity checks against known market facts |
| Material AI-generated components | e.g. "Risk-model implementations, backtest engine and dashboard structure were AI-assisted; portfolio choice, IPS limits, threshold choice, stress-scenario design, interpretation and the final recommendation were made, tested and written by the team. MiroFish generated **behavioural narratives only**. They were coded independently by two team members (Cohen's κ reported) and converted to numbers by our data-anchored translation layer. Their value was tested in a pre-registered A/B evaluation (Step 20)." |

Keep a running `doc/ai_log.md` from Week 1: date, module, what the AI produced, who reviewed it, what changed.

## 4. Implementation plan

| Week | Task |
|---|---|
| 2 | Report outline and figure list agreed; `ai_log.md` running |
| 3 | Section owners draft §1–7 as their steps finish; figure export functions |
| 4, Days 1–2 | Full draft; tear sheet generator; Limitations text finalised in one place, rendered in both app and report |
| 4, Day 3 | Edit pass for plain English and consistency; number audit (script compares numbers in the report with the artifacts) |
| 4, Day 4 | PDF build; final proofreading; submission package |

## 5. Acceptance tests

- Report has 7–15 pages; the tear sheet is exactly 1 page.
- Number audit script: every numeric token tagged `{{artifact:key}}` in the Markdown resolves, with no stale values.
- A non-finance reader can state the verdict, the allocation and the worst-case loss after reading the tear sheet for 5 minutes (test with a friend).
- The AI disclosure covers all 4 required items.

## 6. Pitfalls

- A report that describes formulas but not **decisions and why**.
- Inconsistent numbers between app, report and deck.
- A Limitations section that is generic boilerplate. Make it specific to *our* portfolio and models.
- Undisclosed AI use, or AI-written conclusions presented as the team's own judgement.

## 7. Defend it in Q&A

- *"Summarise your recommendation in 30 seconds."* Read the tear sheet headline. Practise this.
- *"Which limitation worries you most?"* Pick one honestly (e.g. 2022-type stock-bond correlation) and state how the governance triggers mitigate it.
