# Step 16: Testing, QA, Reproducibility & Deployment

**Owner:** D · **Week:** continuous from Week 1; hardening in Week 4 · **Effort:** about 3 days total · **Depends on:** all · **Feeds:** submission

## 1. Target

- A pytest suite that **proves the mathematics** (closed forms, simulations with known parameters, textbook examples) and **guards against leakage**.
- CI green on every push; lint clean.
- Cold-clone reproducibility: identical artifacts and numbers on a fresh machine.
- The app deployed on Streamlit Community Cloud with a stable URL, plus local one-command run.
- A clear README.

## 2. Why it matters

- Rubric: technical rigour (25%), i.e. "correct implementation". Tests are our evidence.
- Rubric: software quality (15%), i.e. documentation and reproducibility from the repo.
- Brief §7.1–7.2: reproducible code, a README, one-command run.
- Brief §8.7: the team must "independently review, test and validate any AI-assisted output". The test suite *is* that validation and is cited in the AI disclosure.

## 3. How to achieve it

### 3.1 Test pyramid

| Layer | Examples | Count (target) |
|---|---|---|
| Unit: closed form | Normal/t VaR and ES, GMV and max-Sharpe closed form, Euler sums, BEY conversion | about 40 |
| Unit: simulation recovery | GPD, GARCH, t-copula and Markov parameter recovery; MC convergence | about 10 (marked `slow`) |
| Unit: textbook | Kupiec and Christoffersen worked examples; Basel 250-day table | about 6 |
| Property-based (`hypothesis`) | ES ≥ VaR; VaR monotone in α; weights sum to 1 and respect bounds; contributions sum to total | about 8 |
| Leakage guards | Walk-forward fit window ends before t; filtered regime probabilities unchanged by truncating future data; rf lag; **Step 22 suite:**<br>• feature lag-shift invariance;<br>• point-in-time weight path unchanged by perturbing the future;<br>• `TestLockedError` without the freeze tag;<br>• no full-sample scaling;<br>• LSTM sequence/scaler invariance;<br>• the final-test script refuses to run without the tag;<br>• no `import torch` under `app/` | about 11 (run on **every push** in CI) |
| Integration | Pipeline on a 2-year fixture dataset runs end-to-end in under 60 seconds | 1 |
| App smoke | `streamlit.testing.v1.AppTest` on every page with several control sets | 10 |

Fixtures: a small committed dataset `tests/fixtures/mini_prices.parquet` (2 years, 7 tickers) so the tests run offline and fast.

### 3.2 Code quality

- `ruff` for lint and formatting; type hints on public functions; numpy-style docstrings with the **formula** in each risk function's docstring.
- No function longer than about 60 lines in the quant core; no Streamlit imports under `src/`.
- `pre-commit` hooks: ruff, end-of-file fixer, and a large-file guard (artifacts under 50 MB total).

### 3.3 CI (`.github/workflows/ci.yml`)

- Matrix: Python 3.12, Ubuntu and Windows.
- Steps: `pip install -r requirements.txt && pip install -e .` → `ruff check` → `pytest -m "not slow"` → (nightly or manual) `pytest -m slow`.
- Badge in the README.

### 3.4 Reproducibility protocol (run in Week 4, and before submission)

1. Fresh clone into a new folder on a **different machine** (a teammate's laptop).
2. `make setup && make pipeline`.
3. Compare `artifacts_manifest.json` hashes with the committed ones; they must be identical.
4. `make run` and visually compare the key numbers on Home against the tear sheet.
5. Record the result in `doc/reproducibility_log.md` (date, machine, OS, outcome).

If the hashes differ across operating systems because of floating-point or BLAS differences, compare numbers to a tolerance of 1e-8 instead, and document this.

### 3.5 Deployment (Streamlit Community Cloud)

- Public GitHub repository (or private with judge access); main file `app/Home.py`; Python 3.12 selected in the advanced settings.
- No secrets needed (no API keys). Data comes from the committed snapshot and artifacts.
- Keep the repo under 1 GB and artifacts under 50 MB (Parquet with zstd compression).
- Cold start under 30 seconds: lazy-load the heavy artifacts per page.
- Fallback: if the cloud is down during judging, the README gives exact local steps plus a short screen recording of the app.

### 3.6 README structure

1. One-paragraph purpose and verdict
2. Live app link and screenshot
3. Quick start (3 commands)
4. Repository map
5. Data sources and snapshot policy (refresh command)
6. Methodology summary, linking to the report
7. Testing
8. Assumptions and limitations (short, linking to the app page)
9. AI disclosure (link)
10. Team and licence

## 4. Implementation plan

| Week | Task |
|---|---|
| 1 | CI skeleton, fixtures, tests for Steps 02–06 alongside the code |
| 2 | Tests for Steps 07–10, including slow simulation-recovery tests |
| 3 | Tests for Steps 11–15, leakage guards, AppTest smoke tests |
| 4 | Coverage review (target ≥ 85% on `src/quantedge/risk`, `backtest` and `decision`); reproducibility protocol; deploy; README final; tag `v1.0-submission` |

## 5. Acceptance tests (for this step)

- CI green on main; coverage report attached.
- Reproducibility log shows a successful cold-clone run on a second machine.
- The deployed URL loads every page; the link is in the README and the report.
- `git log` shows no commits in the outer `C:\Users\PMIHIR` repository.

## 6. Pitfalls

- Tests that only check "runs without error". Every test must assert a **value**.
- Slow tests in the default run, so people stop running them.
- Committing large intermediate files that push the repo over Streamlit Cloud limits.
- Last-minute dependency upgrades. Freeze `requirements.txt` in Week 3.

## 7. Defend it in Q&A

- *"How do you know your VaR code is right?"* About 70 tests, including closed-form matches, parameter recovery on simulated data, and textbook examples for the backtests. Show the CI badge and coverage.
- *"How did you validate AI-generated code?"* Every module was reviewed by a named team member and validated against independent closed forms and simulations (see the AI disclosure).
