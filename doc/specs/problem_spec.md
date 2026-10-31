# 01 · Problem specification

**Status:** v3: team-agreed; decision values D1–D5, D8–D10 agreed 2026-10-28 and recorded in `doc/decisions/inputs_lock.md` (D6, D7 open); booklet traceability check added (§9, `doc/brief_traceability.md`) · **Date:** 2026-10-28
Items marked **[TEAM]** are judgements the team must make, date and own (brief §8.7). Proposed values are labelled assumptions, not facts about the client.
**Change rule:** after the hard freeze date (D7), this spec is not reopened unless a test fails. Any change is logged in the IPS change log (§4.1).

## 1. The decision

> **Which allocation of the seven permitted ETFs, and which risk limits, should the Serendib University Endowment Fund's investment committee adopt, so that the fund can sustain its spending with a downside it has measured, tested and accepts?**

The output is one of **accept the mandate as proposed / adjust the risk limit / reject** (brief §8.6), with:
- **one recommended portfolio**;
- two alternatives, with their dollar trade-offs;
- the limits;
- the evidence;
- what would change our mind.

## 2. Client and stakeholders

| Stakeholder | What they need from us | Where we answer it |
|---|---|---|
| Investment committee (non-technical) | A clear recommendation, what risk buys what return and income, losses in dollars, what can go wrong | Memo, tear sheet, app Home |
| University (scholarships, research, faculty, capital projects) | Stable, sustainable distributions | Income measure (§3.4), spending simulation (§3.2) |
| Judges acting as the committee | Defensible assumptions, honest limitations | Report, Assumptions & Limitations page |

Committee beliefs (brief p. 3): *"Avoiding large losses is more important than maximizing gains"*; *"a good decision is one whose downside you have measured, tested, and can defend."*
Objective wording (brief p. 3): *"balance capital preservation, **income generation**, and sustainable real growth, with particular emphasis on resilience during periods of market stress."*

**Base currency:** the mandate is stated in **USD**. The fund is measured, and its spending and real value are defined, in USD and US CPI. This is an assumption, stated as such. One sensitivity line shows results in LKR terms, and one paragraph uses Sri Lanka CPI (World Bank/IMF) for context.

## 3. Objectives

### 3.1 Return objective and expected returns: forward-looking, inputs locked

**Return objective (agreed): US CPI + 3.5% a year, net of costs, over a 10-year rolling horizon** = 3.0% spending + 0.5% real growth. The booklet (p. 3) asks the endowment to "preserve **and grow**" its capital, so the objective includes a real-growth margin; it leaves the return objective to the team (p. 4, responsibility 2).

**Required return (compound):** R_req = (1 + s)(1 + g)(1 + π) − 1, compared with the **net** expected return (costs are deducted from the expected return, not added here).

| Input | Agreed | Range shown | Rule | Status |
|---|---|---|---|---|
| s, spending rate | **3.0%** of the 12-quarter average value | 2.5 / 3.0 / 3.5% | Below the sustainable real return, so the fund can grow; NACUBO FY2025 average 4.9% shown as the peer comparison | **D1 agreed** |
| g, real growth | **0.5%** a year | 0 / 0.5 / 1.0% | "Preserve and grow" (booklet p. 3) | agreed with D1 |
| π, inflation | 10-year breakeven **T10YIE** at the decision date, lagged one day | ± 1 pp | Market-based and forward-looking. If CPI is used anywhere, month m is used only from the 15th of month m+1 (publication lag) | locked rule |
| costs (on the expected-return side) | ETF expense ratios + trading + **exact withholding drag** (15% of equity distributions, computed from dividend data) | AGG taxed / exempt | US–Sri Lanka treaty rate; treaty eligibility is a stated limitation | locked rule |

**Expected return (geometric), built from components:**

| Sleeve | Arithmetic estimate | Notes |
|---|---|---|
| AGG | **DGS10 + s_AGG** (documented spread, e.g. 0.3–0.6 pp; DGS7 acceptable to match duration ≈ 6) | Starting yield: the standard medium-term bond forecast (cited from the literature, not re-validated on our short sample) |
| Equity ETFs | **DGS10 + β_i × ERP** (β against SPY on the estimation window) | Term-matched base; the T-bill is **not** used |
| GLD | Expected inflation π | No yield; long-run real return ≈ 0 |

- Portfolio geometric return ≈ arithmetic − σ²/2.
- **ERP (D4, agreed): 4.5% arithmetic** (range 3.5–5.5%); **AGG spread 0.5%** (range 0.3–0.9%). Stated as a **disclosed assumption**, anchored on approved data and only cross-checked against published estimates: the booklet (p. 9) treats undisclosed or proprietary data sources as a rubric violation.
- The memo states the **break-even ERP** at which the verdict would flip.
- The realised historical CAGR is shown as context only, labelled "historical, not a forecast".

### 3.2 Horizons: three, each with its own question

| Horizon | Question | Measure | Role |
|---|---|---|---|
| 1 / 10 days | How bad is a bad day or fortnight? | VaR, ES, EVT at 90/95/99% | Limits and monitoring |
| 1 year | How deep could a drawdown go before we next meet? | Stress losses (historical + hypothetical), maximum drawdown | **Primary budget (D_max)** |
| 10 years | Will the fund keep its purchasing power while spending? | P(real value < 80% of start), median real value | **Context only, not binding** |

**10-year simulation design (fixed before running):**
- monthly data;
- stationary bootstrap with a mean block of 12 months, with a sensitivity row for 1 / 12 / 36;
- asset means re-centred to the §3.1 forward estimates;
- CPI resampled jointly with returns;
- spending smoothing modelled (4% of the 36-month average).

Report the uncertainty plainly: the sample holds fewer than two independent 10-year paths.

### 3.3 Risk tolerance: one primary budget, the rest calibrated from it

1. **Primary [TEAM] D2:** the maximum stress loss **D_max**, applied to **max(historical replays, hypothetical scenario)**. Proposed range: 20–25%.
2. **Calibrated, not derived by formula:** read the volatility and 99% 1-day ES of the frontier point whose dev-data stress loss equals D_max. Those become the volatility and ES limits. Dev data reference (fixed 60/25/15 SPY/EFA/EEM equity sleeve, 10% GLD):

   | Equity share | GFC drawdown | Vol | ES99 | ES99 / daily σ |
   |---|---|---|---|---|
   | 15% | −16.2% | 5.1% | 1.22% | 3.78 |
   | 25% | −19.3% | 6.3% | 1.56% | 3.96 |
   | 35% | −23.0% | 7.9% | 2.03% | 4.10 |
   | 50% | −30.4% | 10.6% | 2.78% | 4.15 |

3. **The ES limit uses a through-the-cycle ES:** estimated on dev data that includes the GFC (the same idea as Basel's stressed VaR). It does not use a forecast for one particular date.
4. **The champion's conditional ES forecast is a monitoring trigger, not a limit.** Proposed **[TEAM] D9:** if the 99% ES forecast exceeds the limit for 10 consecutive trading days, move to the next-lower frontier point and notify the committee.
5. **Honest wording:** these limits are set **with knowledge of in-sample results**. The protection against data snooping is the locked 2023–26 test, run once, plus the sensitivity tables. It is not a claim that the limits were set blind.

### 3.4 Income

For every frontier point, report the trailing 12-month distribution yield **net of 15% withholding** on equity distributions, and the share of 4% spending covered by income versus asset sales.

### 3.5 Lookback period (a graded choice, brief p. 3)

- **Optimiser estimation window:** 756 days (3 years). Long enough for a stable covariance, short enough to reflect the current regime.
- **Risk-model window:** 500 days.
- **Justification:** the existing window-sensitivity table (250 / 500 / 1000), plus one paragraph on the stability versus responsiveness trade-off.

## 4. Constraints

| Constraint | Rule | Source |
|---|---|---|
| Universe | SPY, EFA, EEM, AGG, GLD, XLE, XLK only | Brief §5 |
| Positions | Long-only, fully invested; a T-bill sleeve only as a labelled sensitivity | Team assumption |
| Concentration caps | XLE, XLK, EEM ≤ 10%; GLD ≤ 15%; each equity ETF ≤ 40%; equity group ≤ 50%; **AGG ≤ 60–70% ([TEAM] D3)**, justified by **factor concentration**: AGG is internally diversified across issuers, not across rate and inflation risk. With AGG uncapped, minimum variance holds 84–91% AGG and lost 16% in 2022 | Review S7 |
| Cap governance | Prefer caps that **do not bind** at the recommended point. Report binding constraints and a ± 5 pp cap sensitivity | Audit G3 |
| Liquidity | All daily-liquid. ETF-discount risk in crises disclosed: AGG −6.8% on 10 Oct 2008 against a ≈ −0.25% move implied by the yield change | Audit G7 |
| Tax | US dividend withholding, 15% treaty rate, computed exactly | §3.1 |
| Legal | UPMIFA prudence as an analogy only; Sri Lankan law not researched | Limitation |
| Data | Yahoo, FRED, World Bank/IMF only | Brief §9.1 |
| Tooling | Free tier only; no LLM at runtime | Brief §6 |

### 4.1 IPS change log (kept in the report)

| Version | Change | Date | Trigger |
|---|---|---|---|
| v0 | AGG under the 40% single-asset cap | 2026-10-27 | Original design |
| v1 | AGG cap 65% | 2026-10-28 | No candidate passed under v0 (results-aware) |
| v1b | Champion rule changed to "lowest pinball among passing" | 2026-10-28 | After validation results (results-aware) |
| v2 | This spec: GLD ≤ 15%, AGG cap [D3], limits calibrated from D_max | [date] | Independent audit and review |

The recommendation is shown under every version.

## 5. Decision rule (pre-committed; locked with the inputs before the frontier is first computed)

1. **Lock the inputs** in a dated record: s, the π source, c, ERP, s_AGG, caps, D_max, simulation design, champion rule, trigger rule and the **regime definition** (proposed: 3-month T-bill up > 1 pp over 12 months, known at t−1).
   **Pre-registered hypotheses** (part of the input lock; each owner tests theirs with the validation ladder in the notebooks, and the evidence table reports strong / moderate / not supported):

   | # | Hypothesis (stated before testing) | Test | Owner notebook | Status so far |
   |---|---|---|---|---|
   | H1 | The SPY–AGG hedge weakens in rate-hiking cycles (3-month bill up > 1 pp over 12 months) | HAC interaction regression + block bootstrap; out of sample 1990–2004 | 01 §8, 05 | **Moderate** (in-sample p < 0.001; out of sample same sign, p = 0.18) |
   | H2 | The hedge weakens when lagged CPI > 3% | Same | 01 §8 | **Not supported** (p = 0.30–0.82) |
   | H3 | GARCH standardised residuals are free of autocorrelation and clustering | Ljung-Box on z and z² | 03 | To test |
   | H4 | The champion's 99% VaR has correct coverage and independent exceptions on 2023–26 | Kupiec, Christoffersen, Basel (run once after the freeze) | 04 | To test |
   | H5 | The recommended point's Jensen's alpha against an equal-equity SPY/AGG benchmark is not different from zero | HAC t-test | 02 | To test |
   | H6 | No frontier point has a Sharpe ratio significantly different from the minimum-variance point | Paired block-bootstrap SE | 02 | To test |

2. **Frontier:**
   - **minimum variance** (Ledoit-Wolf), at equity share x = 15, 20 … 50%, under the caps;
   - Min-CVaR at the same x, as a robustness check only;
   - the textbook Markowitz/CAPM frontier on the Portfolio page, with one sentence on why its corner solutions are not the recommendation (CAPM-only returns push it to almost all equity).
3. **Score each point:**
   - forward geometric return against R_req;
   - through-the-cycle ES99 ($);
   - worst stress loss;
   - income yield;
   - Euler ES shares;
   - binding constraints;
   - the 10-year simulation (context).
4. **Recommended point:** the **lowest-risk point that meets R_req and every risk limit**.
5. **Verdict:**
   - **ACCEPT:** such a point exists.
   - **ADJUST RISK LIMIT:** none exists, but the lowest-risk point meeting R_req would comply if D_max (and the limits calibrated from it) were loosened by **≤ 5 pp**. Recommend that point and the amended limit for explicit committee approval.
   - **REJECT:** neither holds, **or** no risk model is valid (step 7).
   - A **spending-rate change** is shown as **advice** ("at 3.5% spending, point X would meet R_req"), not as a verdict branch. The brief's options are about the risk limit.
6. **Present:** the recommended point plus two alternatives (one lower-risk, one higher-return), each with its dollar trade-off.
7. **Model validity (pre-committed for the 2023–26 test):**
   - The champion must pass Kupiec, Christoffersen and Basel.
   - If it fails Kupiec at 5% on the test, limits use the passing model with the **higher current ES**.
   - If no model passes: REJECT ("risk cannot be measured reliably").
   - Validation p-values are optimistic after choosing among 8 models × 3 windows; only the test period is clean.
8. **Risk budgeting action:** an Euler ES-share table for the recommended point. If any asset's ES share exceeds **X% ([TEAM] D8)**, cap it and restate the result. This replaces check C7.

## 6. Success criteria

| Rubric line | Weight | We succeed if |
|---|---|---|
| Investment decision | 30% | One recommended point with two alternatives and dollar trade-offs, following mechanically from §5, plus income, the break-even ERP and a sizing statement |
| Technical rigour | 25% | Every number reproduces from a clean clone; each layer has an owner who re-derived it; statistics are correct (paired Sharpe SE, honest trial register) |
| Software | 15% | Every mandatory app item; one-command run; risk shown as of October 2026 |
| Innovation | 15% | The **already-built, rubric-named** extensions: **regime-conditioned risk** (including a regime correlation table: normal / liquidity crisis / **rate-hiking cycle** (notebook 01 §8: the CPI > 3% definition was tested and rejected), which feeds the stagflation correlation flip), **alternative EVT threshold rules** (A / B ForwardStop / C), and the **volatility-target risk overlay**. Plus one "explored and rejected" paragraph (MiroFish, deep ML) |
| Communication | 15% | Human-written memo, tear sheet and Q&A bank; every member can defend their layer |

## 7. Out of scope

- Derivatives, overlays outside the universe, currency hedges.
- Paid data or LLMs.
- MiroFish, LSTM, LightGBM: **archived under a git tag** and removed from the build. One paragraph and one slide (linear QR matched the champion; deep models failed coverage).
- Research-paper track.
- Dot-com crash replay: described qualitatively only. EFA, EEM, AGG and GLD did not exist, so 4 of 7 assets would be proxies.
- Deflated Sharpe ratio and shadow prices: replaced by the trial register and the ± 5 pp cap sensitivity.

## 8. Decisions (agreed 2026-10-28; full records with evidence in `doc/decisions/inputs_lock.md`)

| # | Decision | Agreed value | Status |
|---|---|---|---|
| D1 | Spending rate | 3.0% (2.5–3.5%), objective CPI + 3.5% with 0.5% growth | agreed |
| D2 | Crisis budget D_max | 25% (20% shown as sensitivity) → volatility ≤ 8.4%, 99% ES ≤ 2.23% | agreed |
| D3 | Caps | AGG ≤ 65%; XLE/XLK/EEM ≤ 10%; GLD ≤ 15%; equity ETF ≤ 40%; equity ≤ 50% | agreed |
| D4 | ERP, AGG spread | 4.5% arithmetic (3.5–5.5%), 0.5% (0.3–0.9%); disclosed assumption | agreed |
| D5 | Shock horizon | cumulative peak-to-trough episode of about three quarters | agreed |
| D6 | Notebook owners | — | **open** |
| D7 | Hard freeze date | — | **open** |
| D8 | ES-share cap | 40% | agreed |
| D9 | Monitoring | alert only (5 days → convene the committee) | agreed |
| D10 | Verdict framing | ACCEPT with the CPI + 3.5% objective if met; otherwise ADJUST THE RISK LIMIT with the minimum change and its cost | agreed |

## 9. Booklet requirements that were missing or only implicit (found in the traceability check)

The full requirement-by-requirement map is `doc/brief_traceability.md` in the repo. Three items were not explicit in v2:

| # | Booklet requirement | What was missing | Where it is now met |
|---|---|---|---|
| G27 | p. 4: the committee requires managers to demonstrate **diversification benefits** | v2 only constrained concentration; notebook 02 found no extra *return* from diversification, so the benefit must be shown in **risk** terms | Notebook 03 §8: ES diversification saving in dollars, diversification ratio, crisis-loss reduction, and how the benefit shrinks in crises |
| G28 | p. 7, Layer 4: evaluate **how different modelling approaches perform under stressed market conditions** | no question in the notebook 04 plan | Notebook 04 §7: each model's exceptions and loss scores inside the GFC, COVID and 2022 windows |
| G29 | p. 4, responsibility 1: **determine and defend the investment horizon** | §3.2 had three horizons but no single defended statement | §3.2 statement below; inputs_lock "Investment horizon"; memo sentence |

**Horizon statement (G29):** the endowment is perpetual; the return objective is judged over a **10-year rolling horizon** (long enough to span a full market cycle, short enough to be monitored); risk is monitored at 1 and 10 days and budgeted per crisis episode.
