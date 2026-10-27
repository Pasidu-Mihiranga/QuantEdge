"""Strictly out-of-sample walk-forward VaR/ES forecasts (Step 11 §3.1).

For each forecast day t:
    weights  w = w_tau(t-1), the point-in-time weights held during day t (Step 22 §3.2)
    window   asset returns dated in [t-W, t-1], valued at w (pro-forma history of today's book)
    model    refitted every `refit_every` days or whenever w changes; otherwise models with an
             `update` method roll their filter forward one day (GARCH recursion, no refit)
    loss     l_t = -w' R_t;  hit_a = 1{l_t > VaR_t(a)}
An assertion checks on every day that the fit window ends strictly before t.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ModelSpec:
    name: str
    factory: Callable[[], object]
    refit_every: int = 1


def walk_forward_var(spec: ModelSpec, returns: pd.DataFrame, wpath: pd.DataFrame, window: int,
                     alphas=(0.95, 0.975, 0.99), start=None, end=None) -> pd.DataFrame:
    cols = list(wpath.columns)
    R = returns[cols]
    W_held = wpath.reindex(R.index).shift(1)          # weights held during each day
    idx = R.index
    lo = max(window, int(idx.searchsorted(pd.Timestamp(start)))) if start is not None else window
    hi = int(idx.searchsorted(pd.Timestamp(end), side="right")) if end is not None else len(idx)
    Rv = R.to_numpy()
    Wv = W_held.to_numpy()

    rows = []
    model, last_fit, last_w = None, -10**9, None
    for i in range(lo, hi):
        w = Wv[i]
        if np.isnan(w).any():
            continue
        changed = last_w is None or not np.allclose(w, last_w)
        if model is None or changed or (i - last_fit) >= spec.refit_every:
            hist = pd.Series(Rv[i - window:i] @ w, index=idx[i - window:i])
            assert hist.index.max() < idx[i], "look-ahead: fit window reaches the forecast day"
            model = spec.factory().fit(hist)
            last_fit, last_w = i, w
        elif hasattr(model, "update"):
            model.update(float(Rv[i - 1] @ w))
        loss = float(-(Rv[i] @ w))
        row = {"date": idx[i], "loss": loss}
        for a in alphas:
            v, e = model.var(a), model.es(a)
            row[f"var_{a}"], row[f"es_{a}"], row[f"hit_{a}"] = v, e, int(loss > v)
        rows.append(row)
    return pd.DataFrame(rows).set_index("date")


def run_models(specs: list[ModelSpec], returns: pd.DataFrame, wpath: pd.DataFrame, window: int,
               alphas=(0.95, 0.975, 0.99), start=None, end=None) -> dict[str, pd.DataFrame]:
    return {s.name: walk_forward_var(s, returns, wpath, window, alphas, start, end) for s in specs}
