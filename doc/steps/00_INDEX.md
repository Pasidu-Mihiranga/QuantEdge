# QuantEdge 1.0: Step-by-Step Expert Plans (Index)

This folder breaks the master plan (`../QuantEdge_Implementation_Plan.md`) into 18 steps. Each step file uses the same template:

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

| 21 | [★ Research paper track: BeST protocol + StressReplay-20](21_research_paper_track.md) | V + all | hooks in Weeks 1–4; paper in Weeks 5–14 | 19, 20 | preprint and publication |

### MiroFish in one paragraph

MiroFish (an open-source AI multi-agent simulator, AGPL-3.0) is added as an **exploratory behavioural scenario-design layer** next to our hypothetical stress test (Step 12). It **never** replaces VaR, ES, EVT or backtesting. Agent narratives are coded by two humans and translated into shocks through **historical factor quantiles and estimated betas**, so the LLM never chooses the magnitudes. MiroFish runs as a separate local service on a free LLM and its outputs are cached, so the submitted app makes no LLM calls. Step 20 then scores **with vs without MiroFish out of 100**, using a pre-registered metric score (MVS) and a blind review on the official rubric weights (BRS). A pre-declared rule decides whether MiroFish's scenario is adopted, kept as a hybrid, or reported as an appendix.

## Critical path

```
01 → 02 → 03 → 04 → 07 → 08 → (09, 10) → 11 → 13 → 15 → 17 → 18
                ↘ 05 ↗        ↘ 12 ────────────↗
                ↘ 06 ↗
                                 12 → 19 (MiroFish runs) → 20 (A/B score) → 13
```

## Week-by-week gates

The team does not move to the next week until every item in the current gate is satisfied.

| Gate | End of | Must be true |
|---|---|---|
| G1 | Week 1 | Snapshot committed with manifest; cleaning log renders; KPIs and 6 baseline optimisers pass their tests; IPS v1 drafted |
| G2 | Week 2 | All VaR/ES models share one interface and pass the closed-form tests; EVT threshold chosen with diagnostics; recommended portfolio selected walk-forward; IPS limits calibrated; **MiroFish feasibility gate passed or MiroFish dropped (Step 19 §5); Step 20 scorecard frozen and hashed** |
| G3 | Week 3 | Backtests and stress tests precomputed; all 11 app pages work; decision engine outputs a verdict; innovation items done or explicitly cut; **MiroFish runs cached and the with/without scorecard computed, with the adoption decision recorded** |
| G4 | Week 4 | Report, tear sheet and deck final; cold-clone reproducibility passes; deployed URL works; two full Q&A rehearsals |

## Cut order if time runs short

Cut from the bottom of this list first. Never cut a mandatory layer.

MiroFish (Steps 19–20) has its **own kill switch**: the Week 2 feasibility gate. If it fails, MiroFish is dropped and the attempt is documented. If it passes but Week 3 slips, reduce the replicates from K = 5 to K = 3 and the replays from 4 to 2 before cutting anything else in this list.

1. Keep: everything mandatory (Layers 1–5, stress tests, the 6 UI items, Assumptions & Limitations)
2. Keep: GARCH-FHS and conditional EVT (they are what make the backtest pass)
3. Cut 4th: Acerbi-Szekely ES backtest
4. Cut 3rd: volatility-target overlay
5. Cut 2nd: Markov regime model
6. Cut 1st: t-copula Monte Carlo
