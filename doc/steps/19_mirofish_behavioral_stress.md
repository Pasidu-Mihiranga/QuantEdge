# Step 19: MiroFish Behavioural Stress Lab (AI Multi-Agent Scenario Design)

**Owner:** V (lead), D (service infrastructure), R (translation review) · **Week:** 2 Days 4–5 (spike and gate) → Week 3 (runs) → Week 4 (app and report) · **Effort:** about 5 days · **Depends on:** 03, 07, 12 · **Feeds:** 20 (evaluation), 13, 15, 17, 18

## 1. Target

1. Add **MiroFish** ([666ghj/MiroFish](https://github.com/666ghj/MiroFish), AGPL-3.0) as an **exploratory scenario-design layer** alongside the quantitative engine. It must **never** replace VaR, ES, EVT or backtesting.
2. Run a small, fixed set of research scenarios with multi-agent investor simulations:
   - institutional investors;
   - retail investors;
   - bond investors;
   - speculative traders;
   - conservative investors.
3. Convert the qualitative agent behaviour into **explicit, testable factor and ETF shocks** through a documented, data-anchored **translation layer** that we build. We never use MiroFish numbers as returns.
4. Compute portfolio impact for all 7 candidates with the existing stress engine (Step 12).
5. Cache every run (seed document, prompt, configuration, raw report, normalised JSON, hashes), so the Streamlit app **never calls an LLM at runtime**. This keeps the submitted app free-tier and reproducible.
6. Feed the A/B evaluation in Step 20 ("with vs without MiroFish", scored out of 100).

Feature name in the app: **"Behavioural Stress Lab: AI-Driven Market Stress Scenarios"**.

## 2. Why it matters

- Rubric: innovation and ambition (15%). An AI multi-agent behavioural layer is a strong differentiator **if it is validated and justified**.
- Brief §8.6: the team must design **one hypothetical scenario**. MiroFish can inform that design by exploring how participants' reactions might amplify a shock (panic selling, flight to safety, contagion). Historical price paths cannot show this.
- Brief §8.7: the AI must not replace judgement. Using MiroFish only for *narrative generation*, with team-owned translation and validation, is exactly the compliant pattern.

### Compliance constraints (non-negotiable)

| Rule | Risk introduced by MiroFish | Our control |
|---|---|---|
| Free-tier toolkit (§6, a fairness rule) | MiroFish needs an LLM API (consumption is "high") and Zep Cloud | **Primary:** a local open-weights LLM via Ollama's OpenAI-compatible endpoint (free); Zep Cloud free quota. **Fallback:** a paid API only with written organiser approval and a hard budget cap. Email the organisers in Week 2 to confirm LLM use is allowed. |
| Approved data only (§9.1) | The LLM brings its own pretrained "knowledge"; the seed could include news | The seed document is generated **only** from Yahoo/FRED/World Bank artifacts plus team-written trigger text. LLM knowledge is disclosed as **non-data narrative input**, and no LLM output is used as data. |
| Reproducibility (§9.1) | LLM output is non-deterministic | Low temperature, recorded configuration, K = 5 replicates per scenario, every artifact cached and hashed; the app reads the cache only |
| AI disclosure (§8.7) | A material AI component | A dedicated row in AI_DISCLOSURE.md, plus the human coding and validation protocol below |
| AGPL-3.0 licence | Copying or modifying MiroFish into our repo, or serving a modified version | Run MiroFish **unmodified** as a separate local service in its own folder. Our repo contains only our client code and cached outputs. Any modification gets published (our repo is public anyway). |

## 3. How to achieve it

### 3.1 Architecture

```
┌────────────────────────── QuantEdge repo (ours) ──────────────────────────┐
│ data artifacts ─► behavioral/seed_builder.py ─► seed.md (approved data)   │
│                                    │                                       │
│                                    ▼                                       │
│                     behavioral/client.py ──HTTP──► MiroFish service        │
│                                    ▲               (separate folder,       │
│                                    │                Docker, unmodified)    │
│        raw_report.md + agent Q&A ◄─┘                                       │
│                 │                                                          │
│                 ▼                                                          │
│ behavioral/extract.py ─► questionnaire JSON ─► 2 human coders (kappa)      │
│                 │                                                          │
│                 ▼                                                          │
│ behavioral/translate.py ─► factor shocks (historical quantiles)            │
│                 │          ─► ETF shocks (Step 12 factor betas)            │
│                 │          ─► Σ blend calm→stress (contagion)              │
│                 ▼                                                          │
│ stress engine (Step 12) ─► portfolio losses, scenario VaR/ES, fan chart    │
│                 │                                                          │
│                 ▼                                                          │
│ data/behavioral/runs/... (cache) ─► Streamlit "Behavioural Stress Lab"     │
└────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 MiroFish service setup (D, Week 2 Day 4)

- Location: `Desktop/QuantEdge/mirofish-service/` (a **separate** clone pinned to a specific commit SHA recorded in `config.yaml`; never inside `quantedge/`).
- Run it with **Docker Desktop** (`docker compose up -d`; frontend :3000, backend :5001). This is the most reliable route on Windows. Native fallback: Python 3.11–3.12 with `uv`, plus Node ≥ 18 (`npm run setup:all && npm run dev`).
- `.env` settings:
  - `LLM_BASE_URL=http://host.docker.internal:11434/v1`, `LLM_MODEL_NAME=<open-weights instruct model pulled in Ollama>`, `LLM_API_KEY=ollama`;
  - `ZEP_API_KEY=<free tier>`.
  - **Never commit `.env`.**
- Hardware check: local LLM speed decides the feasible scale. Benchmark one 10-round, about 30-agent run first.
- **API discovery:** the README mentions a backend at :5001 but documents no endpoints. Read `backend/` route definitions to find the calls for graph build → environment → simulate → report → chat, and write `client.py` against them. If programmatic control is infeasible, use the **documented manual protocol** (§3.7) and still archive every artifact.

### 3.3 Scenario set (fixed in advance in `config.yaml → behavioral.scenarios`)

| ID | Trigger (team-written) | Purpose |
|---|---|---|
| B1 | Unexpected +75 bp Fed hike with hawkish guidance; equity panic risk | The paste's scenario; behavioural amplification of a rate shock |
| B2 | Stagflation: inflation re-accelerates, oil spike, renewed hiking | **Same trigger as the team's baseline hypothetical (Step 12)**, for a direct A/B comparison |
| B3 | EM contagion: strong USD, EM capital flight (relevant to the client's Sri Lankan context) | EM, USD and gold dynamics |
| R1–R4 | **Blind replays** (anonymised, information only up to the event): 2013 taper tantrum, Aug 2015 China devaluation, Q4 2018 sell-off, 2022 rate shock | Validation against realised ETF returns (Step 20, D1) |

- **Scale:** at most 40 rounds (MiroFish's own guidance) and about 50–150 agents, with **K = 5 replicates** per scenario (different seeds). That is about 35 runs in total, scheduled overnight.
- No large-scale or live runs during the presentation.

### 3.4 Seed document builder (`seed_builder.py`)

Generated automatically from approved-data artifacts. No hand edits.

1. Macro snapshot at the as-of date: 10-year yield, T-bill rate, CPI YoY, VIX, HY spread, USD index, WTI (FRED).
2. Universe description: the 7 ETFs' roles (from the brief) and their trailing 1-year return, volatility and correlations (Yahoo).
3. Participant roster: the 5 investor archetypes with team-written behavioural profiles (mandate, horizon, constraints, typical crisis behaviour), cited to the lecture decks.
4. Trigger text (team-written, from the table above).
5. **Replay mode:** dates and tickers anonymised ("Central bank of Country A", "Broad US equity fund"); data truncated at the as-of date.
6. **Output prompt:** based on the pasted prompt, plus an explicit instruction: "do not invent verified prices or unsupported probabilities; report alternative scenarios, assumptions and limitations".

### 3.5 Structured extraction (`extract.py` and the human coding protocol)

After each simulation, put a **fixed questionnaire** to MiroFish's ReportAgent (interaction step) and require JSON answers validated against our schema (`schema.py`, pydantic):

```json
{
  "factors": {
    "rates_10y":  {"direction": "+|0|-", "intensity": "low|medium|high|extreme", "confidence": "low|medium|high"},
    "oil":        {...}, "vix": {...}, "usd": {...}, "hy_spread": {...}
  },
  "behaviour": {
    "panic_selling": 0-3, "flight_to_safety": ["AGG","GLD","cash"], "contagion_breadth": 0-3,
    "herding": 0-3, "investor_disagreement": 0-3, "duration": "days|weeks|months"
  },
  "asset_directions": {"SPY": "+|0|-", "EFA": "...", "EEM": "...", "AGG": "...", "GLD": "...", "XLE": "...", "XLK": "..."},
  "narrative_summary": "...", "key_mechanisms": ["..."], "stated_limitations": ["..."]
}
```

- **Human validation:** two team members independently code the raw narrative into the same schema, without seeing the JSON. Compute **Cohen's κ** against the MiroFish JSON and between the coders.
- Disagreements are resolved by discussion and logged in `coding_log.csv`. The **final, human-approved coding** is what gets translated. This is the §8.7 "human validation" evidence.

### 3.6 Translation layer (`translate.py`): narrative to numbers, anchored in data

Magnitudes come **from historical data, not from the LLM**:

| Signal | Mapping rule |
|---|---|
| Factor intensity | Signed historical quantile of that factor's **h-day change** over 2004 to the snapshot date: low = 75th, medium = 90th, high = 97.5th, extreme = 99.5th percentile |
| Duration | Sets h: days = 5, weeks = 20, months = 60 trading days |
| Factor to ETF | ETF shock = B · f (Step 12 HAC factor betas, stress-sample version), with ± SE bands |
| Contagion breadth (0–3) | Correlation stress: Σ_λ = (1−λ)Σ_calm + λΣ_stress, with λ ∈ {0, 0.33, 0.67, 1} |
| Panic / herding (0–3) | Volatility multiplier for scenario-conditional Monte Carlo: σ × {1, 1.25, 1.5, 2} (anchored to the ratio of crisis to calm GARCH σ) |
| Flight to safety | Consistency check only: AGG and GLD directions must agree with the coded flight targets; otherwise flag the scenario |
| Asset directions (from the LLM) | **Not used for magnitudes.** Used only to test agreement with the translated shocks (consistency score) |

Outputs per run:
- the factor-shock vector and ETF-shock vector;
- portfolio loss in $ and % for every candidate;
- **scenario-conditional VaR/ES** (Monte Carlo with the shifted mean, Σ_λ and the σ multiplier);
- per-asset contributions.

Across the K = 5 replicates this gives a **fan of losses** (min, median, max), which honestly displays the model's instability.

**The same translation machinery is used for the baseline ("without MiroFish") design.** A team analyst completes the identical questionnaire for the same triggers *without* MiroFish, blind to its outputs. Only the *source of the questionnaire answers* differs, which makes Step 20's A/B comparison fair.

### 3.7 Manual fallback protocol (if the API cannot be scripted)

1. Upload the generated `seed.md` through the UI.
2. Paste the generated prompt from `prompt.txt` verbatim.
3. Record the configuration (model, rounds, agents).
4. Export or copy the full report into `raw_report.md`.
5. Ask the questionnaire verbatim and save `report_agent_answers.json`.
6. Run `python -m quantedge.behavioral.ingest <run_dir>`, which hashes and validates the files.

All steps are scripted except the UI clicks, and they are documented in `doc/behavioral_protocol.md`.

### 3.8 Cache layout

```
data/behavioral/
  scenarios.yaml                          # frozen scenario + scorecard config (hash recorded)
  runs/<scenario_id>/<run_k>/
    seed.md  prompt.txt  run_config.json  # model, temperature, rounds, agents, MiroFish commit, timestamps
    raw_report.md  report_agent_answers.json
    coding_A.json  coding_B.json  final_coding.json  coding_log.csv
    translated_shocks.parquet  portfolio_impact.parquet
    manifest.json                          # sha256 of all files
  summary/behavioral_results.parquet       # consumed by the app and Step 20
```

## 4. Implementation plan

| # | Task | File | Owner | When |
|---|---|---|---|---|
| 1 | Clone MiroFish into `mirofish-service/` at a pinned commit; Docker up; Ollama and Zep configured; organiser email about LLM use | (outside the repo) | D | W2 D4 |
| 2 | Benchmark one small run; read backend routes; **feasibility gate** (§5) | `doc/decisions/mirofish_gate.md` | D + V | W2 D5 |
| 3 | `behavioral/schema.py` (pydantic models) and `scenarios.yaml` | src | V | W2 D5 |
| 4 | `seed_builder.py` (normal and anonymised replay modes) | src | V | W3 D1 |
| 5 | `client.py` (API) **or** `ingest.py` plus the manual protocol | src | D | W3 D1 |
| 6 | Run B1–B3 and R1–R4 × 5 replicates (overnight batch) | cache | D | W3 D1–D2 |
| 7 | Team baseline questionnaires (blind) for the same triggers | `final_coding.json` (variant A) | P | W3 D1 |
| 8 | Human coding by 2 coders and κ; `extract.py` validators | src + cache | V + R | W3 D2–D3 |
| 9 | `translate.py` (quantile tables, betas, Σ_λ, σ multiplier), reusing `stress/factor.py` and `stress/stressed_cov.py` | src | R | W3 D2 |
| 10 | Portfolio impact, scenario Monte Carlo, fans; write `behavioral_results.parquet` | src | V | W3 D3 |
| 11 | Step 20 evaluation run | see Step 20 | V | W3 D4–D5 |
| 12 | App page "Behavioural Stress Lab" and report section | app, report | C | W4 |
| 13 | **Research hooks (Step 21 §5.1):** `condition: multi_agent \| single_llm` switch; episode registry plus `detect_episodes()`; `llm_calls.jsonl` log; memory-probe question; generic anonymiser | src | D + V | W3 (about 1 day) |

### App page contents (`app/pages/10_Behavioural_Stress_Lab.py`)

1. A banner that stays visible at all times: *"Exploratory. Narratives are AI-generated; all numbers come from our data-anchored translation, not from MiroFish."*
2. Scenario selector (B1–B3).
3. Narrative summary and key mechanisms, plus the agent-behaviour signal gauges (panic, contagion, flight to safety).
4. A **provenance table** for each shock: signal → coded value → mapping rule → factor shock → ETF shock.
5. ETF shock table with SE bands; an interactive **weight sliders → portfolio impact** widget (the paste's example, computed by our engine).
6. Fan chart of losses across replicates, with all 7 candidates.
7. Comparison against historical crises, the baseline hypothetical scenario and VaR/ES/EVT.
8. A link to the Step 20 scorecard (with vs without MiroFish).

## 5. Feasibility gate (end of Week 2), with explicit kill criteria

Proceed only if **all** of the following hold. Otherwise drop MiroFish, document the attempt in the report (an honest negative result still earns innovation credit) and keep the baseline.

- [ ] One complete end-to-end run finishes in under 45 minutes on our hardware with the free configuration.
- [ ] The organisers confirm (or do not object to) LLM use under the free-tier rule, or the free local LLM path works.
- [ ] The ReportAgent questionnaire returns schema-valid JSON in at least 4 of 5 attempts.
- [ ] The total projected time for all runs fits within Week 3 Days 1–2 (overnight batches allowed).

## 6. Acceptance tests

- `seed_builder` output contains only values traceable to manifest-listed artifacts (a test parses every number in `seed.md` and matches it to its artifact source).
- Replay seeds contain no dates after the as-of date and no real tickers or institution names (a regex test).
- `translate.py`: intensity "medium" for VIX maps exactly to the 90th percentile of historical h-day VIX changes; λ = 0 gives Σ_calm; zero shocks give zero loss.
- Schema validation rejects malformed JSON; the ingest script refuses runs with missing files or hash mismatches.
- With the network disabled, the app page renders entirely from the cache.

## 7. Pitfalls

- Presenting MiroFish narratives as forecasts, or its numbers as returns. **Never.**
- Seed documents that include unapproved news text.
- Running a single replicate and reporting it as "the" result; this hides instability.
- Letting the LLM choose magnitudes. Magnitudes must come from historical quantiles and estimated betas.
- Committing API keys, or vendoring or modifying AGPL code inside our repo.
- A live MiroFish demo in the pitch (latency, cost, failure risk). Show cached results only.

## 8. Defend it in Q&A

- *"Isn't this just an LLM making things up?"* The LLM generates behavioural hypotheses only. Two team members code them independently (κ reported). Magnitudes come from historical factor quantiles and estimated betas. We validated the pipeline blind on four past episodes (Step 20).
- *"Why trust agent simulations?"* We don't treat them as calibrated. They are a structured way to explore *mechanisms* (contagion, flight to safety) that historical paths may not contain. Step 20 scores whether they add value over our baseline, and we report the answer either way.
- *"Is this free-tier and reproducible?"* It uses a local open-weights LLM and Zep's free tier. Every run is cached with hashes; the app never calls an LLM.
- *"Did the LLM know the 2022 outcome?"* Possibly; replays are anonymised, and contamination is a disclosed limitation that affects the human baseline equally (Step 20, D1 caveat).

Sources: [MiroFish repository](https://github.com/666ghj/MiroFish) (architecture, requirements, AGPL-3.0, cost guidance), [MiroFish overview, Emelia](https://emelia.io/hub/mirofish-ai-swarm-prediction), [YourStory: hype vs reality](https://yourstory.com/ai-story/mirofish-ai-explained-hype-vs-reality).
