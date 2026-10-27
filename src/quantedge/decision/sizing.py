"""Position sizing from the risk budget (Step 13 §3.2).

risk-to-capital RC_i = (% of ES) / w_i: above 1.5 an asset takes more than 1.5x its capital share
of tail risk. The marginal move that cuts ES most per unit of expected return given up is to sell
the asset with the highest marginal ES / mu_i and buy the one with the lowest (within IPS bounds).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from quantedge.risk.contributions import euler_simulation_es
from quantedge.risk.es import sample_es


def concentration_flags(contrib: pd.DataFrame, rc_flag: float = 1.5) -> pd.DataFrame:
    out = contrib[["weight", "pct_contribution", "risk_to_capital"]].copy()
    out["flag"] = out["risk_to_capital"] > rc_flag
    return out.sort_values("risk_to_capital", ascending=False)


def marginal_swap(contrib: pd.DataFrame, mu: pd.Series) -> tuple[str, str]:
    """(asset to cut, asset to add) by marginal ES per unit of expected return."""
    held = contrib[contrib["weight"] > 1e-6]
    ratio = held["marginal"] / mu.reindex(held.index).clip(lower=1e-6)
    return str(ratio.idxmax()), str((contrib["marginal"] / mu.reindex(contrib.index).clip(lower=1e-6)).idxmin())


def before_after(w_old: pd.Series, w_new: pd.Series, scenarios: pd.DataFrame, mu: pd.Series,
                 sigma: pd.DataFrame, alpha: float = 0.99) -> pd.DataFrame:
    """Weights, expected return, volatility, VaR and ES before and after a proposed re-sizing."""
    rows = {}
    for label, w in (("before", w_old), ("after", w_new)):
        wv = w.reindex(scenarios.columns, fill_value=0.0)
        loss = -(scenarios.to_numpy() @ wv.to_numpy())
        rows[label] = {
            **wv.to_dict(),
            "expected_return": float(mu.reindex(wv.index).fillna(0) @ wv),
            "volatility": float(np.sqrt(wv @ sigma.reindex(index=wv.index, columns=wv.index) @ wv)),
            "var": float(np.quantile(loss, alpha, method="higher")),
            "es": sample_es(loss, alpha),
            "max_risk_to_capital": float(euler_simulation_es(wv, scenarios, alpha)["risk_to_capital"].max()),
        }
    return pd.DataFrame(rows)
