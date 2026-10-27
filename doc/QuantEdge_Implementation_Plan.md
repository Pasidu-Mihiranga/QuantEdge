# QuantEdge 1.0 Final Challenge — Expert Implementation Plan

## Context

The team is competing in QuantEdge 1.0 (brief: `Quant edge 1.0 Final Challenge 1.pdf`, Oct 2026). Acting as an asset manager's quant division, it must recommend how **The Serendib University Endowment Fund** should invest **USD 10M**. The client is conservative: "avoiding large losses is more important than maximizing gains."

The deliverable is a reproducible **Python + Streamlit** app that has to:
1. build a portfolio from 7 ETFs (SPY, EFA, EEM, AGG, GLD, XLE, XLK);
2. measure risk with VaR, ES and EVT;
3. backtest the VaR out-of-sample with Kupiec, Christoffersen and the Basel traffic light;
4. stress-test it (2008 GFC, March 2020 COVID, the 2022 rate shock, and one hypothetical scenario of our own);
5. produce an **accept / adjust risk limit / reject** recommendation.

The other deliverables are a 7–15 page report, a one-page tear sheet, a 10–12 minute pitch and an AI disclosure.

Rubric weights:

| Criterion | Weight |
|---|---|
| Investment decision-making | 30% |
| Technical rigour | 25% |
| Software & interface | 15% |
| Innovation | 15% |
| Communication | 15% |

The two lecture decks (`Advanced_Risk_Management_English_final.pptx`, `EDGEFORGE_..._2026.pptx`) set the standard the judges expect:
- Basel traffic light is calibrated for 99% VaR over 250 observations.
- Rolling VaR may only use data from before each forecast date.
- Log returns don't aggregate across assets.
- Don't average models that disagree.
- Mean-variance optimisation needs shrinkage and robust constraints.
- Correlations rise in a crisis, so tail dependence and copulas matter.
- The EVT threshold must be chosen by diagnostics.
- The investment committee wants six panels: Allocation, Performance, Loss limit, Tail robustness, Model trust, Governance.

**Decisions confirmed with the user:**
- About 4 weeks to the deadline, so this is the full plan.
- Claude builds module by module with tests; the team reviews every module so it can defend it in Q&A. AI use is disclosed.
- Cash: the default is **fully invested in the 7 ETFs**. A sidebar toggle adds a **T-bill cash sleeve** (earning DTB3) as a sensitivity. The team should confirm with the organisers which is allowed.

**Environment facts:**
- `C:\Users\PMIHIR\Desktop\QuantEdge` sits inside a git repo rooted at `C:\Users\PMIHIR`, with remote `neurox-1-0/vendrai`. **Never commit there.** Create a standalone repo at `Desktop\QuantEdge\quantedge\`.
- Local Python is 3.14. Pin **Python 3.12** in a venv (via `uv` or `py -3.12`) for reliable `arch`/`statsmodels` wheels and parity with Streamlit Community Cloud.

---

## 1. Investment framework (the 30% criterion)

### 1.1 Investment Policy Statement (`config.yaml` → IPS page)

- **Horizon:** strategic 3–5 years, with an annual review and quarterly rebalancing. Risk horizon is 1 day (backtested), with 10-day and 1-year figures reported and caveated.
- **Return objective:** spending rate (4%) + US CPI (from FRED CPIAUCSL, about 2.5%) + costs, giving a **required nominal return of about 6.5%**. Set against the conservative risk tolerance, this produces the core trade-off chart: the frontier with the required-return line, and the extra drawdown and ES each additional 1% of return costs.
- **Risk limits** start as hypotheses and are calibrated in Week 2 from the data. Each one gets a written justification.

| Limit | Initial value |
|---|---|
| Annualised volatility | ≤ 8% |
| Worst historical-stress drawdown | ≤ 20% |
| 99% 1-day ES | ≤ 1.5% of NAV |
| Single asset weight | ≤ 40% |
| XLE, XLK, EEM | ≤ 10% each |
| Equities in total | ≤ 50% |
| Gold | ≤ 20% |

- **Policy benchmark:** 60/40 SPY/AGG. It is used for the Information Ratio, beta and alpha comparisons, and to answer "what does the quant work add?"
- **Market proxy for CAPM:** SPY, with the US-equity bias of that choice noted as a limitation.

### 1.2 Portfolio candidates

All candidates are evaluated with the same walk-forward test: quarterly rebalance, 5 bps per side in costs, and estimation using only past data.

| # | Candidate | Method |
|---|---|---|
| 1 | Equal weight | 1/7 each |
| 2 | 60/40 benchmark | Fixed |
| 3 | Global min-variance | `cvxpy` QP, Ledoit-Wolf Σ |
| 4 | Constrained max-Sharpe | Tangency portfolio under IPS bounds |
| 5 | Risk parity (ERC) | Equal risk contribution, solved with `scipy.optimize` |
| 6 | Minimum CVaR | Rockafellar-Uryasev linear program in `cvxpy` |
| 7 | **Recommended: Robust Mean-ES** | Black-Litterman / CAPM-equilibrium μ, Ledoit-Wolf Σ, IPS bounds, max return subject to 99% ES ≤ budget |

- Show the Markowitz frontier with the capital market line, the 7 candidates and the required-return line.
- Show weight stability through bootstrap-resampled weights (200 resamples).
- Select the recommended portfolio on **out-of-sample** results (ES, max drawdown, Calmar, stress loss), not on in-sample Sharpe.

### 1.3 From numbers to decisions

- **Euler risk budget:** component VaR and ES for each asset.
  - Parametric: `w_i·(Σw)_i/σ_p · z`.
  - Simulation: `E[−w_i r_i | L ≥ VaR]`.
  - Check that the components add up to the total.
  - Plot capital weight against risk share, and suggest resizing when an asset's risk share is more than 1.5× its capital weight.
- **Rule engine** (`decision/rules.py`), written in code so it can be audited:
  - **ACCEPT:** every IPS limit is met, the chosen model is green in the backtest, and Kupiec and Christoffersen are not rejected at 5%.
  - **ADJUST:** limits are breached but can be repaired by resizing. The engine outputs the adjusted weights and the new limit.
  - **REJECT:** otherwise.
- **Innovation extras:**
  - Regime-conditioned VaR/ES: a 2-state Markov-switching model (`statsmodels.MarkovRegression`) checked against VIX bands.
  - Volatility-target overlay: when the GARCH forecast of σ exceeds a threshold, shift weight from equities to AGG/GLD (or cash, if enabled). Backtested with costs.
  - t-copula Monte Carlo, showing joint-crash probability versus a Gaussian copula.
  - Macro and FX section:
    - Rolling stock-bond correlation regime, to explain 2022.
    - Inflation sensitivity.
    - **USD/LKR risk** if the university spends in rupees (World Bank/IMF data, memo context only).

---

## 2. Quant engine specifications (the 25% criterion)

### 2.1 Data (`data/`)

- **Prices:** yfinance with `auto_adjust=True` (adjusted Close). The common sample starts at GLD's inception (Nov 2004) and runs to the snapshot date, which covers all three historical crises with real ETF data.
- **FRED:** downloaded directly via `https://fred.stlouisfed.org/graph/fredgraph.csv?id=…` (no API key needed). Series: DTB3 (risk-free rate), DGS10, VIXCLS, CPIAUCSL, DCOILWTICO, BAMLH0A0HYM2, DTWEXBGS.
- **Snapshot:** saved to `data/raw/*.parquet` with `manifest.json` (UTC timestamp, rows, date range, SHA-256). The app always reads the snapshot; `python -m quantedge.data.download --refresh` refreshes it.
- **Cleaning** (`cleaning.py`). Every step appends to a `CleaningLog` that the app displays:
  - Inner-join on trading dates and report any dates that were dropped.
  - Forward-fill FRED gaps of up to 3 days, and log each fill.
  - Flag, without deleting:
    - stale prices (5 or more identical closes);
    - |r| > 6 × rolling 60-day σ;
    - level breaks (CUSUM);
    - negative or zero prices.
- **Returns:**
  - Simple returns for portfolio aggregation (`R_p = Σ w_i R_i`).
  - Log returns `ln(1+R)` for statistical tests and model fitting.
  - Loss `L = −R_p · NAV`.
  - DTB3 is quoted on a bank-discount basis: convert it to the bond-equivalent yield, then to a daily rate (`(1+y)^(1/252) − 1`).
  - Expense ratios are already reflected in prices; don't subtract them again.
- **Stationarity:** ADF and KPSS (`statsmodels`) on prices and on returns, per asset and for the portfolio. Results go in a table.

### 2.2 KPIs (`portfolio/metrics.py`)

| Group | Metrics |
|---|---|
| Return and risk | CAGR, annualised volatility |
| Risk-adjusted | Sharpe, Sortino, Treynor, Jensen's α (CAPM regression with t-stat), Information Ratio vs 60/40, Calmar, Omega |
| Drawdown | Max drawdown, drawdown duration, recovery time, Ulcer index |
| Distribution | Skew, kurtosis, hit rate, beta to SPY |

Each KPI gets a one-sentence plain-English interpretation in the app.

### 2.3 VaR and ES (`risk/var.py`, `risk/es.py`, `risk/montecarlo.py`, `risk/garch.py`)

All methods share one interface, `RiskModel.fit(returns_window) → .var(alpha), .es(alpha)`:

| Model | Details |
|---|---|
| Historical simulation | Windows of 250, 500 or 1000 days; ES = mean of losses ≥ VaR (quantile-integral definition) |
| Parametric Normal | wᵀΣw; closed-form ES = σ·φ(z)/(1−α) − μ |
| Parametric Student-t | Degrees of freedom by MLE; closed-form t ES |
| Cornish-Fisher | Modified VaR |
| Monte Carlo | Multivariate t (Ledoit-Wolf Σ, fitted ν), with an optional t-copula over empirical margins; N = 100k, fixed seed; report the Monte Carlo standard error |
| Filtered HS | GARCH(1,1) with t innovations (`arch`) on portfolio returns; scale standardised residuals by the forecast σ |

**Disagreement analysis** is generated automatically:
- Skew, excess kurtosis, Jarque-Bera, Ljung-Box on r², ARCH-LM.
- Ratios of historical to normal VaR and of ES to VaR.
- Each gap between models is explained by one of these statistics.

### 2.4 EVT (`risk/evt.py`)

- Fit a GPD by MLE (hand-rolled with `scipy.optimize`, cross-checked against `scipy.stats.genpareto` and `pyextremes`).
- **Threshold selection:**
  - Candidate thresholds from the 85th to the 97.5th percentile of losses.
  - Diagnostics for each candidate:
    - mean-excess plot;
    - stability of ξ and of the modified scale (β−ξu), with 95% confidence intervals;
    - number of exceedances N_u;
    - Anderson-Darling and Kolmogorov-Smirnov p-values;
    - QQ plot.
  - **Rule:** the lowest threshold in the stable ξ region with N_u ≥ 50.
  - **Alternative rule:** sequential Anderson-Darling ForwardStop (Bader et al. 2018). Compare the two in the app.
- **Formulas:**
  - `VaR_p = u + (β/ξ)[((n/N_u)(1−p))^(−ξ) − 1]`
  - `ES_p = VaR_p/(1−ξ) + (β−ξu)/(1−ξ)` (ξ < 1)
- Profile-likelihood confidence interval for ξ.
- **Conditional EVT** (McNeil-Frey): GPD fitted to GARCH-standardised residuals. This is used as the backtested EVT model, because returns are not i.i.d.

### 2.5 Backtesting (`backtest/`)

- **Walk-forward engine:** for each t in the selected out-of-sample range, fit on [t−W, t−1] and forecast VaR_t and ES_t. Exception indicator I_t = 1 if L_t > VaR_t.
- Heavy models (GARCH, EVT) are refitted every 5 days and **precomputed** by `pipeline.py` into `data/artifacts/`.
- **Kupiec POF:** `LR = −2ln[(1−p)^(T−x)p^x] + 2ln[(1−x/T)^(T−x)(x/T)^x]`, compared with χ²(1).
- **Christoffersen:**
  - Independence test from the n₀₀/n₀₁/n₁₀/n₁₁ transition counts, compared with χ²(1).
  - Conditional coverage `LR_cc = LR_pof + LR_ind`, compared with χ²(2).
  - Guard against log(0) when n₁₁ = 0.
- **Basel traffic light:**
  - At 99% over 250 days: green 0–4 exceptions, yellow 5–9, red ≥ 10.
  - Rolling traffic light over time.
  - At 90/95%, use binomial cumulative-probability zones (green < 95%, red ≥ 99.99%), labelled as a generalisation.
- **ES backtest** (Acerbi-Szekely Z2) as innovation.
- A comparison table across all models determines which model is "chosen".

### 2.6 Stress testing (`stress/`)

- **Historical windows**, using actual ETF return paths:

| Scenario | Dates (S&P 500 peak to trough) |
|---|---|
| GFC | 2007-10-09 → 2009-03-09 |
| COVID | 2020-02-19 → 2020-03-23 |
| 2022 rate shock | 2022-01-03 → 2022-10-12 |

  Report the $ loss, drawdown within the window, worst day, days to recover and per-asset contribution, for every candidate.
- **Hypothetical scenario, "Stagflation + correlation breakdown":**
  - Inputs: a macro shock vector (ΔDGS10 +150bp, oil +40%, VIX → 45, USD +8%).
  - Mapping: each ETF's return comes from OLS betas on FRED factor changes, estimated from data.
  - AGG cross-check: the duration approximation −D·Δy (D ≈ 6).
  - Shocks to the stress correlation matrix.
- **Reverse stress test:** the smallest scaled shock that breaches the drawdown limit.
- **Interactive scenario builder** with sliders for each factor.

---

## 3. Software architecture (the 15% criterion)

```
Desktop/QuantEdge/quantedge/          ← NEW standalone git repo
├─ pyproject.toml / requirements.txt   pinned; Python 3.12
├─ config.yaml                         tickers, dates, seed, NAV, IPS limits, windows, cash toggle default
├─ src/quantedge/                      pure functions — NO streamlit imports
│  ├─ config.py
│  ├─ data/        download.py, cleaning.py, quality.py, returns.py, manifest.py
│  ├─ portfolio/   optimize.py, metrics.py, capm.py, black_litterman.py, walkforward.py
│  ├─ risk/        base.py (RiskModel), var.py, es.py, montecarlo.py, garch.py, evt.py, contributions.py, regime.py
│  ├─ backtest/    engine.py, tests.py (kupiec, christoffersen, basel), es_backtest.py
│  ├─ stress/      historical.py, factor.py, hypothetical.py, reverse.py
│  ├─ decision/    rules.py, memo.py
│  └─ pipeline.py  one-shot: snapshot → clean → optimise → rolling backtests → data/artifacts/*.parquet
├─ app/
│  ├─ Home.py                          Executive Summary: verdict, KPI cards, traffic light
│  ├─ components/                      sidebar.py, charts.py (Plotly), cards.py, explain.py
│  └─ pages/ 1_IPS · 2_Data_Quality · 3_Portfolio · 4_Risk_Dashboard · 5_Tail_Risk_EVT
│             6_Backtesting · 7_Stress_Testing · 8_Assumptions_Limitations · 9_Methodology_AI
├─ reports/tearsheet.py                one-page PDF/HTML from the same artifacts
├─ data/raw/ + data/artifacts/         committed snapshot so judges reproduce identical numbers
├─ tests/                              pytest
├─ .streamlit/config.toml              theme
└─ README.md, AI_DISCLOSURE.md, Makefile (setup / pipeline / run / test)
```

**Mapping to the mandatory UI items:**

| Item | Where it lives |
|---|---|
| M1 Sidebar | Confidence 90/95/99, VaR method, backtest date range, estimation window, portfolio selector (recommended / candidates / custom weights), cash toggle, NAV |
| M2 Portfolio | Portfolio page: weights, cumulative return, drawdown |
| M3 Risk | Risk Dashboard: VaR, ES and EVT side by side, plus the disagreement analysis and risk contributions |
| M4 Backtesting | Backtesting page |
| M5 Stress | Stress Testing page |
| M6 Limitations | Assumptions & Limitations page, written in plain language |

**Engineering rules:**
- Cache data loads with `st.cache_data`.
- Cheap calculations run live; rolling GARCH/EVT backtests are read from precomputed artifacts. Interactions should take under 2 seconds.
- One command: `streamlit run app/Home.py`.
- Deploy on Streamlit Community Cloud (Python 3.12).

**Libraries:** pandas, numpy, scipy, statsmodels, arch, cvxpy, scikit-learn (Ledoit-Wolf), pyextremes (cross-check), yfinance, plotly, streamlit, pyarrow, pyyaml, pytest. Optional: copulae, reportlab or weasyprint for the tear sheet.

---

## 4. Four-week schedule

Claude builds each module; one named team member reviews and signs it off.

| Week | Build | Team review owner |
|---|---|---|
| **1** | Repo, environment, config; data download, snapshot, manifest; cleaning log; ADF/KPSS; KPIs; CAPM; optimizers 1–6; walk-forward portfolio engine | Data lead, Portfolio quant |
| **2** | RiskModel interface; historical, parametric (N/t/Cornish-Fisher), Monte Carlo, GARCH-FHS VaR/ES; EVT with threshold diagnostics and conditional EVT; Euler contributions; recommended Robust Mean-ES portfolio; **calibrate the IPS limits** | Risk quant |
| **3** | Backtest engine and tests (Kupiec, Christoffersen, Basel, Acerbi-Szekely); stress engine (historical, factor, hypothetical, reverse); `pipeline.py` precompute; full Streamlit app (all pages); decision rule engine; regime and vol-target overlay; t-copula | Validation quant, Product lead |
| **4** | Tear sheet generator; report (12–14 pp); pitch deck; AI disclosure; README; Streamlit Cloud deployment; code freeze; Q&A drills | Whole team |

**Cut line if time runs short:** keep everything through Week 3's core. Drop items in this order: t-copula, regime model, Acerbi-Szekely, vol-target overlay.

**MiroFish additions to the schedule:**

| Week | Work |
|---|---|
| 2, Days 4–5 | Service set up, feasibility gate, scorecard frozen |
| 3 | Runs, human coding, translation, A/B scoring |
| 4 | App page 10, report §6b, pitch slide 9b |

MiroFish has its own kill switch (the feasibility gate). See the next section.

---

## 4b. MiroFish Behavioural Stress Lab + With vs Without evaluation

Details: `doc/steps/19_mirofish_behavioral_stress.md`, `doc/steps/20_with_vs_without_mirofish_evaluation.md`.

**Role**
- [MiroFish](https://github.com/666ghj/MiroFish) is an AI multi-agent social simulator (AGPL-3.0; Python/Node; needs an OpenAI-compatible LLM and Zep Cloud).
- It is used **only** as an exploratory scenario-design layer for the team-designed hypothetical stress scenario.
- It **never** replaces VaR, ES, EVT or backtesting.

**Compliance**
- MiroFish runs as a separate, unmodified local service (Docker) on a **free local LLM via Ollama** plus Zep's free tier. Confirm with the organisers that LLM use is allowed.
- Seed documents contain only data from approved sources plus team-written trigger text.
- Every run is cached and hashed; the Streamlit app never calls an LLM.

**Pipeline**
1. `seed_builder` (approved data) → MiroFish run (5 investor archetypes, ≤ 40 rounds, K = 5 replicates).
2. Fixed JSON questionnaire to the ReportAgent → **two human coders** (Cohen's κ).
3. `translate.py`: intensities become **signed historical factor quantiles**, then ETF shocks via Step 12 betas. Contagion becomes a calm-to-stress Σ blend; panic becomes a σ multiplier.
4. Stress engine → losses for all 7 candidates, scenario VaR/ES, a fan across replicates.

**Scenarios**
- B1: Fed hike panic.
- B2: stagflation (same trigger as the analyst baseline).
- B3: EM/USD contagion.
- R1–R4: blind anonymised replays (2013 taper tantrum, Aug 2015, Q4 2018, 2022) for validation.

**With vs Without MiroFish, scored /100 (pre-registered and hashed before the first run)**
- **Variants:** A = analyst-designed (without MiroFish); B = MiroFish-informed; N = naive historical average. All three use identical translation machinery.
- **MVS (metric score, /100):**

  | Dimension | Points |
  |---|---|
  | D1 Historical fidelity on blind replays | 20 |
  | D2 Tail informativeness / novelty | 15 |
  | D3 Plausibility and economic consistency | 15 |
  | D4 Decision usefulness (incl. reviewer ratings) | 20 |
  | D5 Reproducibility and stability | 15 |
  | D6 Cost, compliance and transparency | 15 |

  B is reported as mean ± bootstrap CI across replicates.
- **BRS (blind review, /100):** 3–5 reviewers score blinded packets X/Y with the official rubric weights (30/25/15/15/15).
- **Adoption rule:**

  | Outcome | Condition |
  |---|---|
  | REJECTED | Any compliance item fails |
  | **ADOPT** B as the official hypothetical | MVS_B − MVS_A ≥ 5, CI excludes 0, and BRS_B ≥ BRS_A |
  | HYBRID | Smaller or uncertain gain; A stays official, B shown as exploratory |
  | APPENDIX | B scores worse than A |

**★ Research paper track (Step 21, `doc/steps/21_research_paper_track.md`)**

The publishable contribution is **not** the standard VaR/ES/EVT analysis, which becomes the case study. It is:
- **C1 BeST protocol:** narratives become data-anchored shocks.
- **C2 StressReplay-20 benchmark:** about 20 anonymised stress episodes, selected by an objective rule.
- **C3 Pre-registered, contamination-controlled comparison:** multi-agent vs **single LLM** (the key ablation) vs human vs historical-analogue, naive and random baselines.

Hooks are built during the competition (about 1 day in Week 3). The paper follows in post-competition Weeks 5–14:
1. Pre-registration (OSF).
2. Extended runs.
3. Analysis.
4. arXiv preprint.
5. Workshop or conference submission.

**Kill switch (end of Week 2)**
- Drop MiroFish and document the attempt if:
  - one end-to-end run takes more than 45 minutes; or
  - the free LLM path fails; or
  - fewer than 4/5 questionnaire responses are schema-valid; or
  - the runs don't fit Week 3.

---

## 5. Deliverables content

- **Report:** IPS → Data and cleaning → Portfolio construction → VaR/ES/EVT and the disagreement analysis → Backtesting → Stress tests → Risk budget → Recommendation → Assumptions and limitations → AI disclosure.
- **Tear sheet:** generated automatically, so the app, report and deck always use the same numbers.
- **Pitch:** follows EDGEFORGE slide 79: Allocation → Performance → Loss limit → Tail robustness → Model trust → Governance → Verdict.
- **Assumptions & Limitations** (graded and non-negotiable):
  - History may not repeat.
  - No liquidity or market-impact modelling.
  - ETF tracking error.
  - Correlation instability.
  - EVT parameter uncertainty.
  - √t scaling caveats.
  - A single snapshot date.
  - USD base currency against LKR spending.
  - No derivatives or margin (out of scope for the universe).
  - The cash assumption.
- **Q&A bank of about 30 questions**, for example:
  - Why this EVT threshold?
  - Why does the normal model understate 99% VaR?
  - What happened to AGG in 2022?
  - Why not hold 60/40?
  - Why ES on top of VaR?
  - What if Christoffersen rejects your model?

---

## 6. Verification

1. **Unit tests** (`pytest tests/`):
   - Normal VaR/ES on 10⁶ simulated normal draws matches the closed form within tolerance.
   - Monte Carlo VaR matches parametric VaR under Gaussian inputs.
   - The GPD fit recovers known (ξ, β) from simulated data and agrees with `pyextremes`.
   - Euler contributions add up to the total VaR/ES.
   - ES ≥ VaR for every model and α.
   - Kupiec and Christoffersen match a textbook worked example (Jorion, Christoffersen).
   - Basel zones match the published 250-day table.
   - Optimizer weights sum to 1 and respect the bounds, with and without the cash sleeve.
   - The walk-forward engine has **no look-ahead**: an assertion that the fit window ends at t−1.
   - Cleaning flags fire on synthetic stale, jump and negative-price data.
2. **Reproducibility:** in a fresh clone, run `make setup && make pipeline && make run`. Artifacts are byte-identical to the committed ones (fixed seed, snapshot data).
3. **End-to-end UI check:** run the app locally and go through every page. Change confidence (90/95/99), VaR method, date range and the cash toggle; numbers update and nothing errors. Check that the VaR/ES/EVT cards line up and that the traffic light renders.
4. **Sanity checks against reality:**
   - SPY drawdown in 2008 is about −55%.
   - AGG's 2022 return is about −13%.
   - GFC/COVID stress losses rank as expected across candidates.
5. **Deployment:** the Streamlit Cloud URL loads cold in under 30 seconds.
