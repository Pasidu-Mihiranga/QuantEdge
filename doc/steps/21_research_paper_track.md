# Step 21: Research Paper Track (Paper A: MiroFish/BeST · Paper B: ML Tail-Risk Forecasting)

This step now covers **two independent papers**:
- **Paper A** (sections ★ to 9 below) studies MiroFish multi-agent stress scenarios.
- **Paper B** (§10 at the end) is a pre-registered champion–challenger study of econometric vs gradient-boosting vs LSTM tail-risk forecasts.

Paper B does not depend on MiroFish, so it is the **more reliable route to publication**: if MiroFish is dropped at its kill switch, Paper B still stands.

**Owner:** V (lead author candidate), R (methods), P (finance case study), D (reproducibility package), C (writing and figures); authorship agreed in Week 1 · **When:** hooks during competition Weeks 1–4 (about 1 day); the paper itself in post-competition Weeks 5–14 · **Depends on:** 12, 19, 20 · **Feeds:** preprint plus workshop or conference submission

---

## ★ The special point: what makes this publishable

The competition analysis (portfolio optimisation, VaR, ES, EVT, backtests) is **standard methodology**, so it is *not* the paper's contribution. It becomes the **application case study**.

The paper's contribution is a **new, reusable evaluation method plus an empirical answer** to an open question:

> **Do LLM-based multi-agent behavioural simulations improve financial stress-scenario design, and is it the *multi-agent interaction* that helps, or just the LLM?**

The paper makes three named contributions:

| # | Contribution | Why reviewers care |
|---|---|---|
| **C1** | **The BeST protocol (Behavioural Scenario Translation & Testing):** a reusable pipeline: approved-data seed → multi-agent simulation → fixed questionnaire → double human coding (κ) → **data-anchored translation** (historical factor quantiles and estimated betas, so the LLM never chooses magnitudes) → stress engine | It turns uncalibrated LLM narratives into auditable, testable numbers. Most LLM-in-finance work stops at narratives or lets the LLM output numbers directly |
| **C2** | **The StressReplay-20 benchmark:** about 20 anonymised historical stress episodes (2006–2025), detected by an objective rule, with seed documents, realised ETF outcomes and contamination probes; code released openly | Benchmarks are highly valued and reusable by others |
| **C3** | **A pre-registered, contamination-controlled, blind comparison** of multi-agent simulation vs a single LLM vs human analysts vs non-AI baselines | It answers the "is it just hype?" question with statistics; a negative result is still publishable |

Working title options:
- *"Do LLM Agent Swarms Design Better Stress Tests? A Pre-Registered Evaluation of Multi-Agent Behavioural Simulation for Portfolio Risk"*
- *"From Narratives to Shocks: The BeST Protocol for Evaluating LLM Multi-Agent Stress Scenarios"*

**Novelty must be confirmed by a literature review** (Week 5) covering:
- LLM agent-based market simulation;
- generative and AI scenario design for stress testing;
- look-ahead and memorisation bias in LLMs for finance;
- classical stress-testing and EVT literature.

Do not claim "first" until this review is done.

---

## 1. Target

1. A **pre-registered** study, filed on OSF or AsPredicted (free) before the extended experiments run.
2. An extended experiment beyond the competition: about 20 episodes, 6 conditions, 2 LLMs, with contamination controls.
3. An 8–10 page paper (workshop format) plus an appendix, with a **reproducibility package**: a GitHub release with a Zenodo DOI, cached runs, prompts, schemas and mapping tables.
4. An arXiv/SSRN preprint, then a submission to a peer-reviewed venue.

## 2. Why it matters

- Academic output for the team (CVs, graduate applications) and a credibility boost in the competition pitch ("our method is being written up as research").
- Honest scientific evidence in an area full of untested claims about LLM "prediction engines".

## 3. Study design

### 3.1 Hypotheses (pre-registered)

| ID | Hypothesis | Test |
|---|---|---|
| **H1** | Multi-agent scenarios (B) have higher historical fidelity than naive (N) and random-plausible (R) baselines | Paired, one-sided |
| **H2 (central)** | Multi-agent simulation (B) beats a **single LLM given the same seed and questionnaire** (S) | Paired, two-sided |
| **H3** | B is **non-inferior** to human analysts (A), within a margin δ = 0.05 on the fidelity score | Non-inferiority test |
| **H4** | B's scenarios are more novel (Mahalanobis distance from known crises) at equal plausibility | Paired |
| **H5** | Performance does not drop on **post-cutoff and counterfactual** episodes; a drop would indicate memorisation | Interaction test |

### 3.2 Conditions (every condition goes through the *same* BeST translation and stress engine)

| Code | Condition | Description |
|---|---|---|
| **B** | Multi-agent (MiroFish) | 5 investor archetypes, ≤ 40 rounds, K = 3 replicates |
| **S** | Single LLM (key ablation) | Same model, seed and questionnaire; one call, no agents, K = 3 |
| **A** | Human analysts | 2 analysts, blind; the same questionnaire |
| **H** | Historical analogue (strong non-AI baseline) | The nearest past episode by macro state (k-NN on the FRED factor levels at the as-of date), using its realised factor moves |
| **N** | Naive average | Mean of prior crisis factor vectors |
| **R** | Random plausible | A draw from the stressed-Σ distribution, scaled to a median-crisis loss (the floor) |

**Ablations (secondary), on a 6-episode subset:**
- number of agents (≈30 vs ≈150);
- rounds (10 vs 40);
- persona diversity (5 archetypes vs 1 homogeneous archetype);
- temperature (0.2 vs 0.8).

### 3.3 StressReplay-20 episode set

**Objective detection rule** (in code, so there is no cherry-picking): an episode is any period where SPY falls ≥ 8% peak-to-trough **or** VIX closes > 30, merged if less than 20 trading days apart. The as-of date is 5 trading days before the peak.

Expected matches (the final list is whatever the rule outputs):

| # | Episode | # | Episode |
|---|---|---|---|
| 1 | May–Jun 2006 EM sell-off | 11 | Jun 2016 Brexit |
| 2 | Feb–Mar 2007 China shock | 12 | Feb 2018 volatility spike |
| 3 | Jul–Aug 2007 subprime onset | 13 | Q4 2018 sell-off |
| 4 | Sep–Nov 2008 Lehman phase | 14 | May/Aug 2019 trade war |
| 5 | Apr–Jul 2010 flash crash / euro debt | 15 | Feb–Mar 2020 COVID |
| 6 | Jul–Oct 2011 US downgrade | 16 | Sep 2020 tech correction |
| 7 | May–Jun 2013 taper tantrum | 17 | 2022 rate shock |
| 8 | Late-2014 oil collapse | 18 | Mar 2023 regional banks (SVB) |
| 9 | Aug 2015 China devaluation | 19 | Jul–Aug 2024 yen carry unwind |
| 10 | Jan–Feb 2016 oil / China | 20 | Apr 2025 tariff shock |

### 3.4 Contamination controls (the most important part for credibility)

1. **Anonymisation:** no dates, tickers, institutions or country names in seeds ("Central bank of Country A", "broad domestic equity fund").
2. **Memory probes:** before each run, ask the model to identify the episode from the anonymised seed. If it does, label the episode **"recognised"** and report the results split by recognised and unrecognised.
3. **Post-cutoff episodes:** episodes after each LLM's documented training cutoff are scored separately.
4. **Counterfactual twins:** for 5 episodes, alter the trigger (e.g. flip the rate surprise from hawkish to dovish). A model that follows the seed changes its answer; a model that recites memory does not.
5. **Humans are contaminated too.** Analysts complete a recognition questionnaire, and this is disclosed symmetrically.

### 3.5 Models

- Two open-weights instruct models from different families, run locally via Ollama. This is free and allows exact model files (digest hashes) to be named.
- Record the model name, weight digest, quantisation, context length, temperature and seed for every call.

### 3.6 Outcomes and statistics

- **Primary outcome:** per-episode fidelity, the same D1 formula as Step 20 (sign hit rate, Spearman ρ, portfolio-loss error).
- **Secondary outcomes:**
  - plausibility (D3);
  - novelty (D2);
  - decision usefulness from blind reviewers (D4c);
  - stability (CV across replicates);
  - cost (tokens, wall time).
- **Analysis:**
  - Friedman test across conditions, followed by paired Wilcoxon signed-rank tests for the planned contrasts (H1–H4), with **Holm correction**.
  - Effect sizes (rank-biserial correlation).
  - **Hierarchical bootstrap** confidence intervals (resample episodes, then replicates).
  - H3 is a non-inferiority test with a pre-specified δ.
- **Power (honest):** with n ≈ 20 paired episodes, α = 0.05 and 80% power, only effects of about d ≥ 0.65 (medium to large) are detectable. State this in the pre-registration and in the limitations. Do not over-interpret null results.

### 3.7 Compute budget (local, free)

| Item | Runs | Approx. wall time |
|---|---|---|
| B on 20 episodes × 3 replicates × model 1 | 60 | ~45 h (overnight batches over about 1 week) |
| B on 10 episodes × 2 replicates × model 2 | 20 | ~15 h |
| S on 20 × 3 × 2 models | 120 | ~2 h |
| Ablations (6 episodes × 4 settings × 2 replicates) | 48 | ~30 h |
| Counterfactual twins (5 × 3) | 15 | ~11 h |

Re-measure these after the Week 2 benchmark run (Step 19) and scale K or the episode count to fit.

### 3.8 Threats to validity (must appear in the paper)

- **LLM memorisation:** mitigated by controls 1–5, not eliminated.
- **Small n:** limited power; report confidence intervals, not just p-values.
- **Translation-layer design choices:** run a sensitivity analysis with an alternative mapping (quantile bands 70/85/95/99).
- **ETF universe:** only 7 US-listed ETFs, so generalisation is limited.
- **Human-baseline quality:** student analysts, not professionals.
- **MiroFish version drift:** pinned commit.

## 4. Paper outline (workshop format, 8–10 pages plus appendix)

1. **Introduction:** stress testing needs plausible but novel scenarios; LLM agent swarms promise this but are untested. Contributions C1–C3.
2. **Related work:** LLM agents in markets; scenario generation for stress testing; look-ahead bias in LLMs; EVT/ES in risk management.
3. **The BeST protocol:** seed → simulate → questionnaire → double coding → data-anchored translation → stress engine (one diagram).
4. **StressReplay-20 and the experimental design:** episodes, conditions, contamination controls, metrics, pre-registration.
5. **Results:** main comparison table (B/S/A/H/N/R); H1–H5; ablations; contamination split; cost.
6. **Case study:** the Serendib endowment ($10M, 7 ETFs). How BeST scenarios change the stress results and the accept/adjust/reject decision, alongside VaR, ES and EVT.
7. **Discussion and threats to validity.**
8. **Conclusion:** when, if ever, multi-agent simulation is worth its cost.
- **Appendix:** prompts, JSON schema, mapping tables, the episode-detection rule, the full episode list, coding manual, AI-use statement, reproducibility checklist.

## 5. Implementation plan

### 5.1 Hooks during the competition (Weeks 1–4, about 1 day total, no extra competition risk)

| Hook | Where | Effort |
|---|---|---|
| `behavioral.condition: multi_agent \| single_llm` switch; `single_llm` runs the same seed and questionnaire in one call via the same OpenAI-compatible endpoint | Step 19 `client.py` | 2 h |
| An **episode registry** (`data/behavioral/episodes.yaml`) instead of hard-coded R1–R4, plus `detect_episodes()` implementing the objective rule | Step 19 `seed_builder.py` | 2 h |
| **LLM call log** (`llm_calls.jsonl`): model, digest, temperature, seed, prompt hash, tokens, latency | Step 19 `client.py` | 1 h |
| Memory-probe question added to each run | Step 19 questionnaire | 1 h |
| Generic anonymiser (dates, tickers, institutions, countries) with unit tests | Step 19 | 2 h |

### 5.2 Post-competition schedule

| Week | Work | Output |
|---|---|---|
| 5 | Check the competition rules on publication and timing; agree authorship (CRediT roles); approach a faculty supervisor; literature review | `paper/related_work.md`, author agreement |
| 6 | Run episode detection, build StressReplay-20 seeds; finalise hypotheses and analysis code on synthetic data; **file the pre-registration** | OSF pre-registration (timestamped) |
| 7–9 | Run B, S, A, H, N and R; ablations; counterfactual twins; human coding (κ) | Cached runs + logs |
| 10–11 | Analysis exactly as pre-registered; exploratory analyses clearly labelled | Results tables and figures |
| 12–13 | Write the paper (LaTeX on Overleaf, free); internal review by the supervisor | Draft v1 → v2 |
| 14 | Reproducibility package: GitHub release, Zenodo DOI, README; **arXiv/SSRN preprint** | Public preprint |
| 15+ | Submit to the target venue (see §6); prepare the rebuttal | Submission |

## 6. Venue strategy (check current deadlines when Week 5 starts)

| Tier | Options | Fit |
|---|---|---|
| Immediate | arXiv (q-fin.RM / cs.AI / cs.MA), SSRN | Always; establishes priority |
| Primary target | Workshops on AI in finance or LLM agents attached to major conferences (e.g. ACM ICAIF, NeurIPS, ICML, ACL workshops) | Short papers; welcome negative or rigorous evaluation results |
| Local / regional | Sri Lankan university research symposia; IEEE-sponsored conferences in Sri Lanka and South Asia | High acceptance; good first publication |
| Later | A journal in computational finance or risk management, after extending the experiments | Needs a larger n and more models |

## 7. Ethics, licensing and integrity

- **Competition rules:** confirm with the organisers that publishing work derived from the competition is allowed, and whether it must wait until after judging. Acknowledge QuantEdge 1.0 in the paper.
- **Data licensing:** Yahoo Finance terms may restrict **redistribution of raw price data**. In the paper release, publish **download scripts plus hashes** (and derived statistics), not raw Yahoo files. FRED series are generally redistributable (check each series' notes).
- **Software licences:** MiroFish is AGPL-3.0. We run it unmodified; any patches we make are released. Our own code: MIT or Apache-2.0.
- **AI use:** follow each venue's AI policy. AI tools are not authors. Disclose that Claude assisted with implementation and the writing support, and that MiroFish is the object of study.
- **Integrity:** pre-registration, all conditions reported, no selective episodes, negative results reported.

## 8. Acceptance criteria

- [ ] The pre-registration is timestamped **before** the extended runs (the OSF link appears in the paper).
- [ ] Episode list produced by the objective rule (code plus output committed).
- [ ] All 6 conditions run on all episodes (or the deviations are documented).
- [ ] Analysis code reproduces every table and figure from cached runs with one command.
- [ ] Zenodo DOI minted; the paper links the code, cached outputs and pre-registration.
- [ ] Supervisor review completed; the preprint is public.

## 9. What would make it a *strong* paper (stretch goals)

- A third LLM, or a larger model through a free academic credit programme.
- Professional risk managers as the human baseline (even 3–5 people).
- Out-of-sample **prospective** scenarios: freeze BeST scenarios today, publish them, and evaluate them against what happens over the next 6–12 months. This is the gold standard against contamination.

---

## 10. ★ Paper B: ML tail-risk forecasting (Steps 22–23)

**Working title:** *"Do Machine-Learning Models Improve Tail-Risk Forecasts for a Conservative Multi-Asset Endowment? A Pre-Registered Champion–Challenger Study"*

### 10.1 The special point: what makes it publishable

| # | Contribution | Why reviewers care |
|---|---|---|
| **B1** | **Leakage-safe protocol:** point-in-time portfolio weights; a chronological partition combined with walk-forward; a test set locked in code and frozen by a hashed git tag | Many ML-for-finance results are inflated by leakage; a verifiable protocol is reusable |
| **B2** | **Joint VaR/ES forecasting and evaluation:** an LSTM trained directly on the FZ0 joint loss, compared with LightGBM quantile models (ratio-hybrid and quantile-integral ES), linear QR, GARCH-FHS and conditional EVT, all scored with FZ0, pinball, DM (Holm) and the Model Confidence Set | Most ML VaR studies ignore ES or evaluate it inconsistently |
| **B3** | **A pooled-power panel design:** 30 long-only portfolios evaluated jointly, giving about 30× the tail observations of a single portfolio | It fixes the "only 10 exceptions" problem that weakens single-portfolio studies |
| **B4** | **Regime and explainability analysis:** VIX ≤ 30 vs > 30, the crisis windows, SHAP attributions | It shows *when* ML helps, not just whether it does |

**Honest novelty statement:** ML-versus-GARCH VaR comparisons already exist in the literature. Our novelty is the protocol, joint ES training and evaluation, and the pooled-power design. Confirm with a literature review in Week 5 before claiming anything is new.

### 10.2 Design

- **Panel (30 portfolios, fixed before any result is seen):**
  - the 7 single ETFs;
  - 60/40, GMV, ERC and Robust Mean-ES (walk-forward, point-in-time weights);
  - 19 Dirichlet(1) long-only portfolios drawn with seed 20261027.
- **Models:**
  - HS, Student-t, GARCH-FHS and conditional EVT (econometric);
  - linear QR, LightGBM, and the LSTM (+ an MLP ablation).
  - The ML models are trained **pooled across the panel**, with portfolio descriptors (weights, ex-ante volatility) as extra features, which also eases the LSTM's data hunger.
- **Partition:** identical to Step 22: development ≤ 2018, validation 2019–2022, test 2023 onwards.
- **Hypotheses (pre-registered):**
  - H1: the best ML model has lower 99% pinball loss than GARCH-FHS on the test period.
  - H2: the FZ0-trained LSTM gives better joint VaR/ES (FZ0) than the ratio-hybrid ES.
  - H3: ML gains concentrate in high-VIX regimes.
  - H4: the trees and the LSTM beat linear QR on the same features (non-linearity matters).
- **Statistics:**
  - DM tests with Holm correction;
  - 90% MCS;
  - **date-clustered bootstrap** for pooled panel inference (portfolio exceptions are correlated on the same day);
  - pooled Kupiec/CC with cluster-robust standard errors;
  - all effect sizes with CIs.
- **Pre-registration:** OSF, filed **before** the `methodology-freeze-v1` tag; the tag SHA is quoted in the paper. A null result ("ML does not beat GARCH-FHS") is publishable because it is pre-registered.

### 10.3 Schedule (post-competition, in parallel with Paper A)

| Week | Work |
|---|---|
| 5 | Literature review; OSF pre-registration of the panel extension |
| 6–8 | Panel runs; LSTM finished if it was cut from the competition; MLP ablation |
| 9–10 | Analysis, figures, robustness (window lengths, a 97.5% ES level, an alternative test start date) |
| 11–12 | Writing; supervisor review |
| 13 | Reproducibility package (code, data recipe with download scripts and hashes, cached predictions); Zenodo DOI |
| 14 | arXiv q-fin.RM preprint; submit |

### 10.4 Candidate venues (check deadlines at Week 5)

| Tier | Options |
|---|---|
| Immediate | arXiv (q-fin.RM, q-fin.ST), SSRN |
| Primary | *Journal of Risk Model Validation*, *Risks* (MDPI), *Journal of Risk and Financial Management* (MDPI) |
| Stretch | *Finance Research Letters*; ACM ICAIF (full paper or workshop) |
| Local / regional | Sri Lankan university research symposia; IEEE-sponsored conferences in South Asia |

### 10.5 Acceptance criteria

- [ ] OSF pre-registration timestamped before the freeze tag.
- [ ] Panel list and seeds committed before any panel result is computed.
- [ ] Every model reported on every portfolio, including losers and failed configurations.
- [ ] One command reproduces every table and figure from cached predictions.
- [ ] Zenodo DOI minted; the preprint is public.

The same ethics, licensing and AI-use rules as §7 apply. AI tools are not authors, and the AI assistance is disclosed.
