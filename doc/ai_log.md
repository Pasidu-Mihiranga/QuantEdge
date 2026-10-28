# AI Assistance Log

Running record for the AI disclosure (brief §8.7, Step 17 §3.4). One row per module or document. The reviewer column names the team member who checked, tested and signed it off.

| Date | Module / document | What the AI produced | Reviewed by | Changes after review |
|---|---|---|---|---|
| 2026-10-27 | Project setup (Step 01): `pyproject.toml`, `config.yaml`, `config.py`, `make.ps1`, CI | Initial implementation to the Step 01 spec | _pending_ | |
| 2026-10-27 | Data acquisition, cleaning, quality flags, stationarity (Steps 02–03) | Implementation to spec, tests with planted errors (flag-table schema fixed for pandas 3; KPSS test judged over 20 draws) | _pending_ | |
| 2026-10-27 | Returns, IPS, KPIs/CAPM, optimisers, walk-forward, point-in-time weights (Steps 04–07, Step 22 M1) | Implementation to spec, closed-form and leakage tests (found that the 60/40 benchmark breaches the IPS) | _pending_ | |
| 2026-10-27 | VaR/ES models, diagnostics, subadditivity demo, EVT (Steps 08–10) | Implementation to spec, recovery and property tests (Cornish-Fisher monotonicity flag; t(4) tail test checks range and stability) | _pending_ | |
| 2026-10-27 | Features, scoring and coverage tests (Step 22 M1–M2) | Implementation to spec, hand-calculated and textbook tests | _pending_ | |
| 2026-10-28 | Backtesting, stress testing, decision engine, memo and tear sheet (Steps 11–13, 17) | Implementation to spec and the team decisions of 2026-10-28 (champion rule, minimum relaxation, client-approval condition) | _pending_ | |
| 2026-10-28 | ML challengers: linear QR, LightGBM, LSTM (Step 22 M3–M5, Step 23) | Implementation to spec, leakage-safe walk-forward, arena scoring | _pending_ | |
| 2026-10-28 | Innovation extras: regimes, vol-target overlay, t-copula, macro/FX (Step 14) | Implementation to spec, app page 11 | _pending_ | |
| 2026-10-28 | MiroFish layer (Steps 19–20): Vertex proxy, seed builder, questionnaire schema, translation layer, client, blinding guard, scorecard, runtime setup (`infra/mirofish/`) | Implementation to spec and the pre-registration; runtime fixes found at the feasibility gate (Gemini thinking off, English output, pinned code mounted on the published image, recommender model cached at a pinned revision) | _pending_ | |
| 2026-10-28 | IPS feasibility study across the frontier (Step 05 task 6) | `decision/feasibility.py`, pipeline stage, IPS page chart, decision-record section | _pending_ | |
| 2026-10-28 | LightGBM explainability: SHAP importance, crisis-day breakdown, ICE monotonicity (Step 22) | `scripts/run_ml_explain.py`, `ice_curves`, app Arena section, record in `ml_selection.md` | _pending_ | |
| 2026-10-28 | Custom-portfolio path (Step 15 task 6): `portfolio/custom.py`, sidebar Portfolio selector, live check on the Risk dashboard | Implementation to spec, unit and app tests | _pending_ | |
