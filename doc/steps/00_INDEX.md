# QuantEdge 1.0: Step-by-Step Expert Plans (Index)

This folder breaks the master plan (`../QuantEdge_Implementation_Plan.md`) into 23 steps. Each step file uses the same template:

1. **Target**: what "done" means
2. **Why it matters**: which brief requirement and rubric criterion it serves
3. **How to achieve it**: methods, formulas and key decisions
4. **Implementation plan**: files, functions and an ordered task list
5. **Acceptance tests**: how we prove it is correct
6. **Pitfalls**: mistakes that cost marks
7. **Defend it in Q&A**: questions the judges are likely to ask, with answer pointers

## Team roles

| Code | Role | Primary steps |
|---|---|---|
| **D** | Data & Engineering Lead | 01, 02, 03, 15, 16 |
| **P** | Portfolio Quant | 04, 05, 06, 07, 13 |
| **R** | Risk Quant | 08, 09, 10, 14 |
| **V** | Validation & Stress Quant | 11, 12, 14 |
| **C** | Product & Communications Lead | 15, 17, 18 |

Claude implements each module and the named owner **reviews, tests and signs it off**. Every member must be able to explain every step, because the brief (§8.7) allows disqualification for submissions the team cannot defend.

## Step map and dependencies

| # | Step | Owner | Week | Depends on | Feeds |
|---|---|---|---|---|---|
| 01 | [Project setup & reproducibility](01_project_setup.md) | D | 1 | none | all |
| 02 | [Data acquisition & snapshot](02_data_acquisition.md) | D | 1 | 01 | 03 |
| 03 | [Data cleaning, quality & stationarity](03_data_cleaning.md) | D | 1 | 02 | 04 |
| 04 | [Returns & portfolio accounting](04_returns_accounting.md) | P | 1 | 03 | 06–14 |
| 05 | [Investment Policy Statement (IPS)](05_ips.md) | P | 1 | 03 | 07, 13 |
| 06 | [Performance KPIs & CAPM](06_kpis_capm.md) | P | 1 | 04 | 07, 15 |
| 07 | [Portfolio construction & selection](07_portfolio_construction.md) | P | 1–2 | 04, 05, 06 | 08–13 |
| 08 | [Value-at-Risk (Layer 2)](08_var.md) | R | 2 | 04, 07 | 09–11 |
| 09 | [Expected Shortfall (Layer 3)](09_expected_shortfall.md) | R | 2 | 08 | 11, 13 |
| 10 | [Extreme Value Theory (Layer 4)](10_evt.md) | R | 2 | 08 | 11, 13 |
| 11 | [Backtesting (Layer 5)](11_backtesting.md) | V | 3 | 08–10 | 13 |
| 12 | [Stress testing](12_stress_testing.md) | V | 3 | 04, 07 | 13 |
| 13 | [Risk budgeting & decision engine](13_decision_engine.md) | P | 3 | 05, 08–12 | 15, 17 |
| 14 | [Innovation extensions](14_innovation.md) | R + V | 3 | 08–12 | 13, 15 |
| 15 | [Pipeline & Streamlit app](15_pipeline_app.md) | D + C | 3 | all quant steps | 16, 17 |
| 16 | [Testing, QA & deployment](16_testing_deployment.md) | D | 1–4 | all | submission |
| 17 | [Report, tear sheet & AI disclosure](17_report_tearsheet.md) | C | 4 | 13, 15 | submission |
| 18 | [Pitch & Q&A defence](18_pitch_defence.md) | C + all | 4 | 17 | final |
| 19 | [MiroFish Behavioural Stress Lab](19_mirofish_behavioral_stress.md) | V + D + R | 2 (gate) → 3 → 4 | 03, 07, 12 | 13, 15, 17, 20 |
| 20 | [With vs without MiroFish: A/B evaluation, scored /100](20_with_vs_without_mirofish_evaluation.md) | V + P + C | 2 (freeze) → 3 | 12, 19 | 13, 15, 17, 18 |
| 21 | [★ Research paper track: Paper A (MiroFish/BeST) + Paper B (ML tail-risk forecasting)](21_research_paper_track.md) | V + R + all | hooks in Weeks 1–4; papers in Weeks 5–14 | 19, 20, 22, 23 | preprints and publication |
| 22 | [Leakage-safe data partition & ML challengers (LightGBM, linear QR)](22_ml_challenger_and_data_partition.md) | R + D + V | 2 (M1–M2) → 3 → G3 freeze → 4 (final test) | 04, 07, 08, 11 | 13, 15, 17, 18, 21, 23 |
| 23 | [LSTM deep challenger (joint VaR/ES network)](23_lstm_deep_challenger.md) | R + D | 3, Days 1–4 (time-boxed) | 22 | 22 (arena), 15, 17, 21 |

### Validation design in one paragraph

History is split **chronologically**: development 2004-11-18 → 2018-12-31, validation 2019-01-01 → 2022-12-31, and a **locked final test** 2023-01-01 → snapshot. Walk-forward forecasting runs *inside* each period, so every forecast stays out-of-sample; the partition only decides which decisions may look at which period. Every selection (IPS calibration, portfolio scorecard, EVT threshold rule, champion model, ML hyperparameters) uses data up to 2022 only. The test period is locked in code until the git tag `methodology-freeze-v1` exists, and is then evaluated once. The best conventional model (champion) faces three challengers: LightGBM quantile VaR, an LSTM joint VaR/ES network, and a linear quantile-regression baseline. A pre-declared rule with one primary metric (99% pinball loss) decides adoption.

**Priority order:** financial engine (Steps 01–13) → leakage foundations (Step 22 M1–M2) → ML validation (Steps 22–23) → MiroFish (Steps 19–20, optional).

### MiroFish in one paragraph

MiroFish (an open-source AI multi-agent simulator, AGPL-3.0) is added as an **exploratory behavioural scenario-design layer** next to our hypothetical stress test (Step 12). It **never** replaces VaR, ES, EVT or backtesting. Agent narratives are coded by two humans and translated into shocks through **historical factor quantiles and estimated betas**, so the LLM never chooses the magnitudes. MiroFish runs as a separate local service on a free LLM and its outputs are cached, so the submitted app makes no LLM calls. Step 20 then scores **with vs without MiroFish out of 100**, using a pre-registered metric score (MVS) and a blind review on the official rubric weights (BRS). A pre-declared rule decides whether MiroFish's scenario is adopted, kept as a hybrid, or reported as an appendix.

## Critical path

```
01 → 02 → 03 → 04 → 07 → 08 → (09, 10) → 11 → 13 → 15 → 17 → 18
                ↘ 05 ↗        ↘ 12 ────────────↗
                ↘ 06 ↗
                                 12 → 19 (MiroFish runs) → 20 (A/B score) → 13
          07 → 22 (M1: partition, weights path, features, leakage tests; M2: scoring)
                → 08–11 → 22 (LightGBM, linear QR) + 23 (LSTM) → arena → freeze tag → 13
```

**Next engineering milestone after the core data steps:** Step 22 M1 (`partition.py`, `weights_path.py`, `features.py` and the leakage tests). No model is trained until M1 passes.

## Week-by-week gates

The team does not move to the next week until every item in the current gate is satisfied.

| Gate | End of | Must be true |
|---|---|---|
| G1 | Week 1 | Snapshot committed with manifest; cleaning log renders; KPIs and 6 baseline optimisers pass their tests; IPS v1 drafted |
| G2 | Week 2 | All VaR/ES models share one interface and pass the closed-form tests; EVT threshold chosen with diagnostics; recommended portfolio selected walk-forward; IPS limits calibrated (all selections on data ≤ 2022); **Step 22 M1–M2 done: partition guard, point-in-time weights, features, leakage tests and scoring all pass**; **MiroFish feasibility gate passed or MiroFish dropped (Step 19 §5); Step 20 scorecard frozen and hashed** |
| G3 | Week 3 | Backtests and stress tests precomputed; all 11 app pages work; decision engine outputs a verdict; innovation items done or explicitly cut; **MiroFish runs cached and the with/without scorecard computed, with the adoption decision recorded**; **ML arena evaluated on validation (champion vs LightGBM, LSTM, linear QR), adoption decision recorded, freeze record committed and tag `methodology-freeze-v1` created** |
| G4 | Week 4 | **Final test run exactly once (Day 1) and reported as-is**; report, tear sheet and deck final; cold-clone reproducibility passes; deployed URL works; two full Q&A rehearsals |

## Cut order if time runs short

Cut from the bottom of this list first. Never cut a mandatory layer.

**Scope priority:** the financial engine and the ML validation come before MiroFish. If time runs short:
1. The **LSTM (Step 23)** moves to post-competition first (it is finished in Weeks 5–8 for Paper B).
2. Then **MiroFish (Steps 19–20)** is dropped, using its kill switch.
3. Then cut from the list below.

Step 22 itself is protected: reduce it to 99% only and 8 features before cutting it. The partition, the freeze tag and the leakage tests are never cut, because they protect every other result.

MiroFish (Steps 19–20) has its **own kill switch**: the Week 2 feasibility gate. If it fails, MiroFish is dropped and the attempt is documented. If it passes but Week 3 slips, reduce the replicates from K = 5 to K = 3 and the replays from 4 to 2 before cutting anything else in this list.

1. Keep: everything mandatory (Layers 1–5, stress tests, the 6 UI items, Assumptions & Limitations)
2. Keep: GARCH-FHS and conditional EVT (they are what make the backtest pass)
3. Cut 4th: Acerbi-Szekely ES backtest
4. Cut 3rd: volatility-target overlay
5. Cut 2nd: Markov regime model
6. Cut 1st: t-copula Monte Carlo
