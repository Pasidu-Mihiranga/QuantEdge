"""Teaching example for the Methodology page (Step 09 §3.5): VaR is not subadditive, ES is.

Two independent bonds. Each loses 100 with probability 4%, otherwise earns 5 (a loss of -5).
At 95%: each bond's VaR is -5 (the default sits beyond the 5% tail), but the pair defaults with
probability 7.84% > 5%, so VaR(A+B) = 95 > VaR(A) + VaR(B) = -10. ES stays subadditive.
Computed exactly from the discrete distributions, so there is no simulation noise.
"""

from __future__ import annotations

import numpy as np


def _discrete_var_es(values: np.ndarray, probs: np.ndarray, alpha: float) -> tuple[float, float]:
    """Quantile-integral VaR and ES of a discrete loss distribution."""
    order = np.argsort(values)[::-1]               # largest loss first
    v, p = values[order], probs[order]
    tail = 1.0 - alpha
    cum = np.cumsum(p)
    var = float(v[np.searchsorted(cum, tail - 1e-15, side="right")]) if cum[0] <= tail else float(v[0])
    taken, total = 0.0, 0.0
    for vi, pi in zip(v, p, strict=True):
        w = min(pi, tail - taken)
        if w <= 0:
            break
        total += w * vi
        taken += w
    return var, total / tail


def subadditivity_demo(p_default: float = 0.04, loss: float = 100.0, gain: float = 5.0,
                       alpha: float = 0.95) -> dict[str, float]:
    single_v = np.array([loss, -gain])
    single_p = np.array([p_default, 1 - p_default])
    pair_v = np.array([2 * loss, loss - gain, -2 * gain])
    pair_p = np.array([p_default**2, 2 * p_default * (1 - p_default), (1 - p_default) ** 2])
    var_a, es_a = _discrete_var_es(single_v, single_p, alpha)
    var_ab, es_ab = _discrete_var_es(pair_v, pair_p, alpha)
    return {"var_single": var_a, "var_sum_of_singles": 2 * var_a, "var_portfolio": var_ab,
            "es_single": es_a, "es_sum_of_singles": 2 * es_a, "es_portfolio": es_ab}
