# AI Assistance Log

Running record for the AI disclosure (brief §8.7, Step 17 §3.4). One row per module or document. The reviewer column names the team member who checked, tested and signed it off.

| Date | Module / document | What the AI produced | Reviewed by | Changes after review |
|---|---|---|---|---|
| 2026-10-27 | Project setup (Step 01): `pyproject.toml`, `config.yaml`, `config.py`, `make.ps1`, CI | Initial implementation to the Step 01 spec | _pending_ | |
| 2026-10-27 | Data acquisition, cleaning, quality flags, stationarity (Steps 02–03) | Implementation to spec, tests with planted errors (flag-table schema fixed for pandas 3; KPSS test judged over 20 draws) | _pending_ | |
| 2026-10-27 | Returns, IPS, KPIs/CAPM, optimisers, walk-forward, point-in-time weights (Steps 04–07, Step 22 M1) | Implementation to spec, closed-form and leakage tests (found that the 60/40 benchmark breaches the IPS) | _pending_ | |
| 2026-10-27 | VaR/ES models, diagnostics, subadditivity demo, EVT (Steps 08–10) | Implementation to spec, recovery and property tests (Cornish-Fisher monotonicity flag; t(4) tail test checks range and stability) | _pending_ | |
| 2026-10-27 | Features, scoring and coverage tests (Step 22 M1–M2) | Implementation to spec, hand-calculated and textbook tests | _pending_ | |
| 2026-10-28 | Independent audit and Phase 0 fixes (gaps G6, G13, G14, G15): scope removal, scorecard Sharpe, crisis-window start, drawdown from the initial $1, C7 removed | Audit by re-derivation with separate scripts (outside the repo), a second AI reviewer, then the code changes and regression tests on branch `phase0-prune-fix` | _pending_ | |
| 2026-10-28 | Notebooks: `01_eda_detective.ipynb` (complete template), skeletons 02–06, `scripts/run_notebooks.py`, `make notebooks` | Notebook 01 code, charts and draft findings (each finding checked against its executed output; three corrected, including the rejected CPI > 3% regime); question lists for 02–06 | _pending_ | |
| 2026-10-28 | `download --add` mode (+2 tests); new series DGS2, DFII10, T10YIE, Sri Lanka CPI (`ctx_`), S&P 500 1989–2004 (`ext_`); notebook 01 formal tests and hedge-regime validation (§8b–8f); validation requirements in skeletons 02–06 | Code, tests and the validation analysis; findings written only after reading the executed outputs (H1 moderate, H2 not supported) | _pending_ | |
