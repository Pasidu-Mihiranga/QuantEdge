"""Live risk check for any portfolio (Step 15 §3.2 "live versus precomputed", task 6).

The app's precomputed artifacts cover the recommended portfolio. For another candidate or custom
weights the cheap layers are recomputed live on data up to the analysis end (never the locked test
period); GARCH-FHS and EVT are fitted only on request ("heavy").

- Weights are normalised to sum to 1 and checked against every IPS weight limit.
- Window risk: each model fitted to the last `window` days of fixed-weight portfolio returns
  R_p,t = sum_i w_i R_i,t (1-day VaR and ES as positive loss fractions).
- Full-sample IPS figures: annualised volatility, historical 99% 1-day ES and the worst drawdown in
  the historical stress windows, held fixed over the whole sample (as the feasibility study).
"""

from __future__ import annotations

from dataclasses import asdict

import pandas as pd

from quantedge.decision.feasibility import evaluate
from quantedge.decision.ips import IPSLimits
from quantedge.risk.var import CornishFisherModel, HistoricalModel, NormalModel, StudentTModel

CHEAP = {"Historical": HistoricalModel, "Normal": NormalModel, "Student-t": StudentTModel,
         "Cornish-Fisher": CornishFisherModel}


def normalise(weights: dict[str, float] | pd.Series, tickers: list[str]) -> pd.Series:
    """Long-only weights on `tickers`, rescaled to sum to 1 (negative inputs are an error)."""
    w = pd.Series(weights, dtype=float).reindex(tickers, fill_value=0.0)
    if (w < 0).any():
        raise ValueError("weights must be long-only (no negative weights)")
    if w.sum() <= 0:
        raise ValueError("weights must not all be zero")
    return w / w.sum()


def heavy_models(evt_threshold_q: float) -> dict:
    from quantedge.risk.evt import EVTModel
    from quantedge.risk.garch import GarchFHSModel

    return {"GARCH-FHS": GarchFHSModel(), "EVT": EVTModel(evt_threshold_q)}


def custom_check(weights: dict[str, float] | pd.Series, returns: pd.DataFrame, limits: IPSLimits,
                 windows: dict[str, tuple[str, str]], window: int = 500, alphas=(0.95, 0.99),
                 heavy: bool = False, evt_threshold_q: float = 0.90) -> dict:
    """IPS weight checks, window VaR/ES by model, and full-sample IPS risk checks for `weights`."""
    w = normalise(weights, list(returns.columns))
    weight_checks = pd.DataFrame([asdict(c) for c in limits.check({"weights": w})])
    port = returns.iloc[-window:] @ w
    models = {name: cls() for name, cls in CHEAP.items()}
    if heavy:
        models |= heavy_models(evt_threshold_q)
    rows = []
    for name, m in models.items():
        m.fit(port)
        rows += [{"model": name, "alpha": a, "var": m.var(a), "es": m.es(a)} for a in alphas]
    full = evaluate(w, returns, windows)
    risk_checks = pd.DataFrame([asdict(c) for c in limits.check(
        {"vol_ann": full["volatility"], "es99_1d": full["es99_1d"], "stress_drawdown": full["stress_drawdown"]})])
    return {"weights": w, "weight_checks": weight_checks, "risk": pd.DataFrame(rows),
            "full_sample": full, "risk_checks": risk_checks,
            "weights_ok": bool(weight_checks["passed"].all()), "risk_ok": bool(risk_checks["passed"].all()),
            "window": [str(port.index.min().date()), str(port.index.max().date())],
            "sample": [str(returns.index.min().date()), str(returns.index.max().date())]}
