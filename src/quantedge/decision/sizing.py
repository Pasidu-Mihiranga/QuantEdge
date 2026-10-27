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


def propose_resize(w: pd.Series, scenarios: pd.DataFrame, mu: pd.Series, caps: dict[str, float],
                   rc_max: float = 2.0, step: float = 0.005, alpha: float = 0.99, max_steps: int = 200
                   ) -> tuple[pd.Series, list[dict], bool]:
    """Move weight in `step` increments from the held asset with the highest risk-to-capital to the
    held asset with spare cap room and the lowest marginal ES per unit of expected return.

    Stops when every held asset's risk-to-capital is at most `rc_max` (achieved = True), when no
    asset has room, or when a move no longer lowers the maximum ratio. Risk-to-capital equals
    marginal ES / portfolio ES, so cutting a small volatile sleeve can *raise* its ratio: the
    target is then reported as not achievable rather than forced. Returns (weights, log, achieved)."""
    w = w.reindex(scenarios.columns, fill_value=0.0).astype(float).copy()
    log: list[dict] = []
    best_w, best_rc = w.copy(), np.inf
    for _ in range(max_steps):
        c = euler_simulation_es(w, scenarios, alpha)
        rc = c["risk_to_capital"].dropna()
        if rc.max() < best_rc - 1e-9:
            best_w, best_rc = w.copy(), float(rc.max())
        elif log:
            break                                    # the last move did not help
        if rc.max() <= rc_max:
            return w, log, True
        sell = str(rc.idxmax())
        room = {t: caps.get(t, 1.0) - w[t] for t in w.index if t != sell and caps.get(t, 1.0) - w[t] > 1e-9}
        if not room:
            break
        held = [t for t in room if w[t] > 1e-4] or list(room)
        ratio = c.loc[held, "marginal"] / mu.reindex(held).clip(lower=1e-6)
        buy = str(ratio.idxmin())
        amt = min(step, w[sell], room[buy])
        w[sell] -= amt
        w[buy] += amt
        log.append({"sell": sell, "buy": buy, "amount": amt, "max_rc_before": float(rc.max())})
    return best_w, log, False
