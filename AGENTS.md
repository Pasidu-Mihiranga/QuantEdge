# AGENTS.md: rules for anyone (human or AI agent) writing code in this repo

QuantEdge 1.0 is a Python + Streamlit application that recommends and risk-checks a USD 10M conservative endowment portfolio over 7 ETFs (SPY, EFA, EEM, AGG, GLD, XLE, XLK). The full specification is in `doc/`; progress is tracked in `TODO.md`.

## Read first

1. `TODO.md`: what is done, what is next. Work top to bottom.
2. `doc/steps/00_INDEX.md`: the step map, gates and cut order.
3. The step file for the item you are working on (`doc/steps/NN_*.md`). Each has a target, method, file list, acceptance tests and pitfalls. Build what it says; if you must deviate, record the deviation in `TODO.md` under "Deviations from the plan".

## Workflow

- Pick the first unchecked item in `TODO.md`, implement it, write its acceptance tests, run them, then tick the item and add a one-line note (what was built, test count).
- Never tick an item whose tests fail or were skipped; write "partial" and say why.
- Keep `TODO.md` current at the end of every work session.

## Layout

```
config.yaml                 single source of parameters (seed, dates, limits, model settings)
src/quantedge/              the package (no Streamlit imports here)
  config.py, paths.py
  data/                     download, manifest, load, cleaning, quality, stats, partition
  portfolio/                returns, metrics, optimize, walkforward, weights_path
  risk/                     VaR / ES / EVT / GARCH models (RiskModel protocol)
  backtest/                 walk-forward engine, coverage tests, scoring, arena
  stress/  decision/  ml/   stress engine, IPS + verdict, ML challengers
app/                        Streamlit multipage app (reads data/artifacts only)
tests/                      pytest; fixtures in tests/fixtures
data/raw/                   frozen download snapshot + manifest.json (committed)
data/artifacts/             pipeline outputs (committed for reproducibility)
scripts/                    one-off scripts (freeze record, window sensitivity)
doc/                        plans, decision records
```

Note: the original Step 01 plan put the repo in a `quantedge/` subfolder. The repo root is `Desktop/QuantEdge` itself, so the package lives at the root.

## Commands (Windows PowerShell; `make.ps1` mirrors the Makefile targets)

```
uv venv --python 3.12 .venv                 # Python 3.12 only (not the system 3.14)
.venv\Scripts\python -m pip install -r requirements.txt -e .     # or: uv pip install ...
.\make.ps1 test                             # pytest -m "not slow"
.\make.ps1 lint                             # ruff check
.\make.ps1 data                             # python -m quantedge.data.download --refresh (network; explicit only)
.\make.ps1 pipeline                         # precompute artifacts
.\make.ps1 run                              # streamlit run app/Home.py
```

## Non-negotiable conventions

- **Sign:** VaR and ES are **positive numbers meaning losses**. Loss fraction ℓ_t = −R_p,t.
- **Returns:** simple returns to aggregate across assets (R_p = Σ w_i R_i); log returns only for statistics on a single series. Never sum log returns across assets.
- **Two portfolio series:** the *performance* series (drifting weights, rebalancing, 5 bps costs) is for KPIs; the *risk* series (point-in-time weights) is for VaR/ES/EVT/backtests.
- **No look-ahead:** every estimate for day t uses data ≤ t−1. Rolling windows are trailing, never centred. Filtered (not smoothed) regime/GARCH estimates only. The risk-free rate is lagged one day.
- **Partition (Step 22):** dev 2004-11-18 → 2018-12-31, validation 2019-01-01 → 2022-12-31, test 2023-01-01 → snapshot. Every *selection* decision uses data ≤ 2022-12-31. Load data through `quantedge.data.partition.load_returns(split)`. Test data is locked (`TestLockedError`) until the git tag `methodology-freeze-v1` exists. Do not compute or plot statistics on 2023+ before the freeze.
- **Flag, don't delete:** suspect data is flagged and logged; crisis days are kept.
- **Randomness:** every random generator is `np.random.default_rng(cfg.seed)` (or a derived seed) passed explicitly.
- **Paths:** resolve from `quantedge.paths.ROOT`; no hard-coded absolute paths.
- **The app never downloads data and never calls an LLM or imports torch.** It reads `data/artifacts/`.
- Docstrings for risk functions include the formula. Public functions have type hints.

## Repository rules

- Never commit the competition source files (`*.pdf`, `*.pptx`), `.env`, API keys, or `.venv/`.
- MiroFish, LightGBM and the LSTM were removed on 2026-10-28 (paid LLM conflicted with the free-tier rule; deep models failed coverage). They are archived at the git tag `archive/mirofish-ml`; do not reintroduce them without a team decision.
- Commits and PRs carry **no AI co-author trailers or AI attribution lines**. AI assistance is disclosed in `AI_DISCLOSURE.md` / `doc/ai_log.md` instead.
- Never commit into the outer home-directory repository; run git with `-C` on this repo or from inside it.
