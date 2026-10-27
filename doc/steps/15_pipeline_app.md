# Step 15: Precompute Pipeline & Streamlit Application

**Owner:** D (pipeline) + C (UX) · **Week:** 3 (build), Week 4 (polish) · **Effort:** 4 days · **Depends on:** all quant steps · **Feeds:** 16, 17, 18

## 1. Target

- `python -m quantedge.pipeline` regenerates **every** artifact from the raw snapshot in one run (with a fixed seed), so the outputs are deterministic.
- A Streamlit app that a **non-technical investment committee** can use. It has the 6 mandatory components, 10 pages, interactions under 2 seconds, a plain-English explanation under every number, and consistent visual language.
- Starts with one command: `streamlit run app/Home.py`.

## 2. Why it matters

- Brief §6: Streamlit must "translate a technical analysis into something a non-technical investment committee could actually use, not … a notebook". It lists 6 minimum components.
- Rubric: software and interface quality (15%), i.e. usability, front-end design, code structure, documentation and reproducibility. Communication (15%) also benefits.

## 3. How to achieve it

### 3.1 Pipeline (`src/quantedge/pipeline.py`)

```
load_raw → build_clean_dataset → returns/rf → IPS → candidates (static + walk-forward)
→ select recommended → risk snapshot (all models × α × horizon) → EVT diagnostics
→ walk-forward backtests (models × W × α) → stress matrix + factor betas + reverse
→ innovation (regime, overlay, copula, macro) → Euler contributions → verdict + sensitivity
→ write data/artifacts/*.parquet + artifacts_manifest.json (hashes, config hash, git SHA)
```

- Steps are cached by input hash, so re-running skips unchanged stages (a simple joblib Memory, or a hash check).
- Expected runtime is about 10–20 minutes, dominated by GARCH/EVT refits and bootstraps. Use `joblib.Parallel` across models.

### 3.2 App architecture

- `app/Home.py` plus `app/pages/N_*.py` (Streamlit multipage).
- `app/components/`:
  - `sidebar.py`: one function that renders the controls and returns a `Controls` dataclass, stored in `st.session_state`.
  - `charts.py`: all Plotly figures, one function each, using a shared theme.
  - `cards.py`: KPI and metric cards with tooltips.
  - `explain.py`: plain-English text helpers ("What this means for the endowment").
  - `data.py`: `@st.cache_data` loaders for artifacts.
- **Live versus precomputed:** artifacts hold the expensive objects. Changing α, the date range, a portfolio selection or custom weights recomputes the cheap layers (HS/Normal/t/CF VaR and ES, KPIs, test statistics on stored exception series, stress replays) live. GARCH, EVT and copula results for custom weights are recomputed on demand behind a "Run" button with a spinner, then cached.

### 3.3 Sidebar (mandatory component M1)

| Control | Values |
|---|---|
| Confidence level | 90 / 95 / 99% (default 99) |
| VaR methodology | Historical, Normal, Student-t, Cornish-Fisher, Monte Carlo, GARCH-FHS, EVT, Conditional EVT |
| Backtest date range | Date slider within the OOS period |
| Estimation window | 250 / 500 / 1000 days |
| Portfolio | Recommended, any of the 6 other candidates, or Custom (weight inputs, normalised and IPS-checked) |
| Allow cash sleeve | Toggle (sensitivity) |
| NAV | $10,000,000 (editable) |
| Horizon | 1 day / 10 days |

### 3.4 Pages

| Page | Contents | Brief item |
|---|---|---|
| **Home: Executive Summary** | Verdict banner (ACCEPT / ADJUST / REJECT); 4 KPI cards (expected return, 99% ES $, worst stress loss, backtest zone); allocation donut; 5 "committee questions" answered in a sentence each; link to the memo PDF | §8.6 memo |
| 1 IPS | Client profile, return-objective derivation, limits table with rationale | §4 |
| 2 Data & Quality | Sources and manifest, cleaning log, flags table, price chart with flags marked, stationarity and stylised-facts tables | §9.2 |
| 3 Portfolio | **Weights** (bar and $ amounts), **cumulative return** (vs 60/40 and equal weight), **drawdown (underwater) chart**, KPI table, efficient frontier with CML and the required-return line, trade-off table, walk-forward scorecard, weight-stability boxplots | **M2** |
| 4 Risk Dashboard | **VaR, ES and EVT side by side at the selected α** (3 big cards plus a grouped bar chart, so the gap is obvious), loss distribution with VaR/ES/EVT lines, all-model comparison table, disagreement analysis, ES/VaR ratios, Euler contributions (capital vs risk), stressed-correlation VaR | **M3** |
| 5 Tail Risk (EVT) | Mean-excess, stability, Hill, QQ/PP plots; threshold rule comparison; return-level card ("once-in-10-years daily loss"); copula joint-crash panel | §8.4 |
| 6 Backtesting | VaR forecast vs realised loss chart with exceptions marked; **Kupiec and Christoffersen results table**; **traffic-light indicator** (big coloured badge) plus rolling traffic-light band; model-selection table; crisis breakdown; Z2 ES test | **M4** |
| 7 Stress Testing | Scenario × portfolio heatmap; per-scenario drawdown paths; asset contributions; hypothetical scenario with **sliders**; reverse stress result; regime and overlay panel | **M5** |
| 8 **Assumptions & Limitations** | Plain-language list grouped into Data, Models, Portfolio, Stress, Decision; each item gives what is assumed, why it matters, and how we mitigate it | **M6 (graded, non-negotiable)** |
| 9 Methodology & AI Disclosure | Formulas, conventions (returns, sign, horizon), references, AI disclosure table | §8.7 |
| 10 Behavioural Stress Lab (MiroFish) | Permanent "exploratory" banner; scenario B1–B3 narratives and behaviour gauges; provenance table from signal to coded value to rule to factor shock to ETF shock; weight sliders → impact; fan chart across replicates; comparison with historical, baseline and VaR/ES/EVT; **with vs without MiroFish scorecard (/100)** and the adoption badge. Reads `data/behavioral/` cache only, with **no LLM calls** | Innovation (Steps 19–20) |

### 3.5 Design rules

- **One colour per concept across all charts:** VaR blue, ES orange, EVT red, realised loss grey, recommended portfolio teal, benchmark slate. Traffic-light colours are reserved for status.
- Every number has **units, horizon and confidence** ("$184k · 1-day · 99%") and a hover tooltip with its definition.
- Under every chart, a one-line "**What this means:**" sentence in plain English.
- Mobile-safe: `st.columns` collapse; no horizontal scroll.
- Never show raw stack traces. Wrap pages in error boundaries with a friendly message and log the details.
- Theme in `.streamlit/config.toml`. Use Plotly's `template` with a shared layout (font, margins, gridlines).

## 4. Implementation plan

| # | Task | Owner |
|---|---|---|
| 1 | `pipeline.py` orchestrator, artifact manifest, stage caching | D |
| 2 | `components/data.py` loaders with `st.cache_data` | D |
| 3 | `components/sidebar.py` and the Controls dataclass | C |
| 4 | `components/charts.py`: about 20 chart functions (frontier, cumulative, underwater, VaR bars, distribution, exceptions, traffic band, heatmap, EVT plots, contributions, boxplots) | C |
| 5 | Pages in order: Home → 4 Risk → 3 Portfolio → 6 Backtesting → 7 Stress → 8 Limitations → 5 EVT → 2 Data → 1 IPS → 9 Methodology | C |
| 6 | Custom-portfolio path: IPS check, then live cheap recompute, then an optional heavy recompute | D |
| 7 | Usability test: a non-finance friend uses the app for 10 minutes with 5 tasks; fix the friction points | C |
| 8 | Performance profiling: each page renders in under 2 seconds warm and under 30 seconds cold on Streamlit Cloud | D |

## 5. Acceptance tests

- `streamlit.testing.v1.AppTest` smoke test: every page runs without exceptions under the default controls and under 3 alternative control sets.
- Changing α updates the VaR, ES and EVT cards consistently (ES ≥ VaR is asserted on the page data).
- The pipeline run twice produces identical artifact hashes.
- Checklist audit: M1–M6 each visibly present; screenshot each for the report appendix.

## 6. Pitfalls

- Recomputing heavy models on every widget change, which makes the app unusable.
- Jargon without explanation. The audience is non-technical by design.
- Inconsistent units or signs across pages.
- Hiding the Limitations page in a footer. It must be a top-level, clearly labelled page.
- Different numbers in the app and the report. Both read the same artifacts (Step 17).

## 7. Defend it in Q&A

- *"Can a committee member use this without you?"* Home answers the 5 committee questions in plain English, every metric has a "what this means" line, and the sidebar is limited to meaningful choices.
- *"Why precompute?"* Rolling GARCH and EVT refits over 4,500 days take minutes. Precomputing keeps the app responsive and the results reproducible; the cheap recomputations remain live and interactive.
