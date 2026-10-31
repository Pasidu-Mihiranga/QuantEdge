"""Historical crisis replays on actual ETF paths (Step 12 §3.1).

Buy-and-hold inside the window from the target weights (the portfolio drifts during a crisis):
    V_t = sum_i w_i prod_{s<=t} (1 + R_i,s);  contribution_i = w_i (prod (1 + R_i) - 1), summing to the total.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from quantedge.portfolio import metrics


@dataclass(frozen=True)
class ScenarioResult:
    name: str
    total_return: float
    loss_usd: float
    max_drawdown: float
    worst_day: float
    vol_window: float
    vol_normal: float
    days_to_recover: int | None
    contributions: pd.Series
    path: pd.Series


def replay(returns: pd.DataFrame, weights: pd.Series, start: str, end: str, nav: float,
           name: str = "") -> ScenarioResult:
    w = weights.reindex(returns.columns, fill_value=0.0)
    # The window runs from the peak close (`start`) to the trough close (`end`); the return dated
    # `start` happened before the peak, so the path begins with the next day's return.
    seg = returns.loc[(returns.index > pd.Timestamp(start)) & (returns.index <= pd.Timestamp(end))]
    growth = (1 + seg).cumprod()
    path = (growth * w).sum(axis=1)
    total = float(path.iloc[-1] - 1)
    contrib = w * (growth.iloc[-1] - 1)
    daily = path.pct_change()
    daily.iloc[0] = path.iloc[0] - 1
    # Recovery: keep holding after the window until the value is back to the starting value (1.0).
    after = returns.loc[returns.index > seg.index[-1]]
    positions_end = w * growth.iloc[-1]
    later = ((1 + after).cumprod() * positions_end).sum(axis=1)
    back = later[later >= 1.0]
    if total >= 0:
        days = 0
    elif len(back):
        days = int(returns.index.get_loc(back.index[0]) - returns.index.get_loc(seg.index[-1]))
    else:
        days = None  # not recovered within the available data
    normal = (returns * w).sum(axis=1)
    return ScenarioResult(
        name=name, total_return=total, loss_usd=float(-total * nav),
        max_drawdown=float(-metrics.max_drawdown(daily)), worst_day=float(daily.min()),
        vol_window=float(daily.std() * np.sqrt(252)), vol_normal=float(normal.std() * np.sqrt(252)),
        days_to_recover=days, contributions=contrib.rename("contribution"), path=path.rename(name),
    )


def stress_matrix(candidates: dict[str, pd.Series], returns: pd.DataFrame,
                  windows: dict[str, tuple[str, str]], nav: float) -> pd.DataFrame:
    """Cumulative return of every candidate (rows) in every historical window (columns)."""
    rows = {}
    for cname, w in candidates.items():
        rows[cname] = {s: replay(returns, w, a, b, nav, s).total_return for s, (a, b) in windows.items()}
    return pd.DataFrame(rows).T
