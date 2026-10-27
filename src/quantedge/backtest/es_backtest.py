"""Acerbi-Szekely (2014) Z2 Expected Shortfall backtest (Step 11 §3.5).

    Z2 = 1 - sum_t l_t I_t / (T (1 - a) ES_t),   E[Z2] = 0 under H0; Z2 < 0 means ES is too low.

Acerbi and Szekely show that the Z2 critical values are stable across plausible return
distributions at a = 97.5%: about -0.70 at the 5% level and -1.80 at the 0.01% level. These fixed
thresholds are used instead of model-specific simulation (documented deviation from Step 11 §3.5).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

Z2_CRIT_5PCT = -0.70
Z2_CRIT_001PCT = -1.80


@dataclass(frozen=True)
class Z2Result:
    z2: float
    zone: str        # "green" (not rejected), "yellow" (rejected at 5%), "red" (rejected at 0.01%)
    T: int
    exceptions: int


def acerbi_szekely_z2(losses, var, es, alpha: float = 0.975) -> Z2Result:
    loss = np.asarray(losses, float)
    hits = loss > np.asarray(var, float)
    z2 = 1.0 - float(np.sum(loss * hits / np.asarray(es, float)) / (len(loss) * (1.0 - alpha)))
    zone = "green" if z2 > Z2_CRIT_5PCT else ("yellow" if z2 > Z2_CRIT_001PCT else "red")
    return Z2Result(z2, zone, len(loss), int(hits.sum()))
