"""Forecast scoring for champion-challenger comparisons (Step 22 M2 / §3.8).

Losses are positive (l = -R). VaR_a and ES_a are positive loss numbers at confidence a.

    pinball_a(l, q) = (a - 1{l < q}) (l - q)                       quantile (VaR) score
    FZ0 (Patton, Ziegel & Chen 2019), on returns y = -l with v = -VaR < 0, e = -ES < 0, tail p = 1 - a:
        L = -(1/(p e)) 1{y <= v} (v - y) + v/e + ln(-e) - 1
    FZ0 is strictly consistent for the (VaR, ES) pair: lower is better.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

ES_FLOOR = 1e-6


def pinball(losses, var, alpha: float) -> np.ndarray:
    loss, q = np.asarray(losses, float), np.asarray(var, float)
    return (alpha - (loss < q)) * (loss - q)


def fz0(losses, var, es, alpha: float) -> np.ndarray:
    """FZ0 joint VaR/ES loss per observation (conversion from loss to return sign done here)."""
    y = -np.asarray(losses, float)
    v = -np.asarray(var, float)
    e = -np.maximum(np.asarray(es, float), ES_FLOOR)  # numerical floor before the log term
    p = 1.0 - alpha
    hit = (y <= v).astype(float)
    return -(1.0 / (p * e)) * hit * (v - y) + v / e + np.log(-e) - 1.0


@dataclass(frozen=True)
class DMResult:
    stat: float
    pvalue: float
    mean_diff: float
    lags: int


def newey_west_lrv(d: np.ndarray, lags: int) -> float:
    d = d - d.mean()
    T = len(d)
    lrv = d @ d / T
    for k in range(1, lags + 1):
        w = 1.0 - k / (lags + 1.0)
        lrv += 2.0 * w * (d[k:] @ d[:-k]) / T
    return float(lrv)


def dm_test(loss_a, loss_b, lags: int | None = None) -> DMResult:
    """Diebold-Mariano with a Newey-West long-run variance. d = loss_a - loss_b;
    a negative statistic means model A has the lower (better) loss. Two-sided normal p-value."""
    d = np.asarray(loss_a, float) - np.asarray(loss_b, float)
    d = d[np.isfinite(d)]
    T = len(d)
    lags = int(math.floor(T ** (1 / 3))) if lags is None else lags
    lrv = newey_west_lrv(d, lags)
    if lrv <= 0:
        return DMResult(0.0, 1.0, float(d.mean()), lags)
    stat = d.mean() / math.sqrt(lrv / T)
    return DMResult(float(stat), float(2 * stats.norm.sf(abs(stat))), float(d.mean()), lags)


def holm(pvalues: dict[str, float]) -> dict[str, float]:
    """Holm step-down adjusted p-values (family-wise error control across challengers)."""
    items = sorted(pvalues.items(), key=lambda kv: kv[1])
    m = len(items)
    out, running = {}, 0.0
    for i, (name, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        out[name] = running
    return out


def model_confidence_set(losses: pd.DataFrame, size: float = 0.10, reps: int = 1000,
                         block_size: int | None = None, seed: int = 0) -> pd.DataFrame:
    """Hansen-Lunde-Nason MCS (arch.bootstrap.MCS, range statistic, stationary bootstrap).
    Returns each model's MCS p-value and whether it is in the (1 - size) set."""
    from arch.bootstrap import MCS

    data = losses.dropna()
    # Identical loss series (e.g. two ES variants sharing one VaR) break the range statistic:
    # compute on unique columns and copy the result to the duplicates.
    rep = {}
    for c in data.columns:
        rep[c] = next((u for u in rep.values() if data[u].equals(data[c])), c)
    unique = data[list(dict.fromkeys(rep.values()))]
    block = block_size or max(1, int(round(len(unique) ** (1 / 3))))
    if unique.shape[1] == 1:
        pv_u, included = pd.Series(1.0, index=unique.columns), list(unique.columns)
    else:
        mcs = MCS(unique, size=size, reps=reps, block_size=block, method="R", seed=seed)
        mcs.compute()
        pv_u, included = mcs.pvalues.iloc[:, 0], list(mcs.included)
    pv = pd.Series({c: float(pv_u[rep[c]]) for c in data.columns})
    return pd.DataFrame({"mcs_pvalue": pv, "in_mcs": [rep[c] in included for c in data.columns]},
                        index=data.columns)


def score_table(losses: pd.Series, forecasts: dict[str, pd.DataFrame], alpha: float = 0.99) -> pd.DataFrame:
    """Mean pinball and FZ0 per model; `forecasts[name]` has columns var and es aligned to losses."""
    rows = []
    for name, f in forecasts.items():
        df = pd.concat([losses.rename("loss"), f[["var", "es"]]], axis=1).dropna()
        rows.append({"model": name, "n": len(df),
                     "pinball": float(pinball(df.loss, df["var"], alpha).mean()),
                     "fz0": float(fz0(df.loss, df["var"], df["es"], alpha).mean())})
    return pd.DataFrame(rows).set_index("model")
