"""Point-in-time weight path (Step 22 §3.2): the single source of weights for every risk target.

    w_tau(t) = target weights set at the latest rebalance tau <= t, where each rebalance used
               only data dated <= tau. Before the first rebalance: pre-declared warm-up weights.
    Realised risk-series return on day t uses the weights held over the day: w_tau(t-1).
    ML target: l_{t+1} = -w_tau(t)' R_{t+1}.
"""

from __future__ import annotations

import pandas as pd


def point_in_time_weights(weights_history: pd.DataFrame, dates: pd.DatetimeIndex,
                          warmup_weights: dict[str, float]) -> pd.DataFrame:
    """Weights known at the close of each date in `dates` (forward-filled from rebalance dates)."""
    cols = weights_history.columns
    warm = pd.Series(warmup_weights, dtype=float).reindex(cols, fill_value=0.0)
    if abs(warm.sum() - 1.0) > 1e-9:
        raise ValueError("warm-up weights must sum to 1")
    path = weights_history.reindex(dates.union(weights_history.index)).ffill().reindex(dates)
    before_first = dates < weights_history.index.min()
    path.loc[before_first] = warm.to_numpy()
    return path


def pit_risk_returns(returns: pd.DataFrame, wpath: pd.DataFrame) -> pd.Series:
    """R_t = w_tau(t-1)' R_t: the return of the book actually held during day t."""
    held = wpath.reindex(returns.index).shift(1)
    out = (returns[wpath.columns] * held).sum(axis=1, min_count=1)
    return out.iloc[1:].rename("portfolio")


def pit_loss_target(returns: pd.DataFrame, wpath: pd.DataFrame) -> pd.Series:
    """ML target aligned at the forecast origin t: l_{t+1} = -w_tau(t)' R_{t+1}."""
    return (-pit_risk_returns(returns, wpath)).shift(-1).dropna().rename("loss_next")
