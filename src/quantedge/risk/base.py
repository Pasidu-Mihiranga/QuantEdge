"""Common risk-model interface (Step 08 §3.1).

Every model is fitted only on the estimation window it is given, so the same object serves the
static snapshot and the walk-forward backtest (Step 11).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np
import pandas as pd


class RiskModel(Protocol):
    name: str

    def fit(self, returns: pd.DataFrame | pd.Series, weights: np.ndarray | None = None) -> RiskModel: ...

    def var(self, alpha: float) -> float: ...          # positive loss fraction, 1-day

    def es(self, alpha: float) -> float: ...

    def loss_sample(self) -> np.ndarray | None: ...


@dataclass(frozen=True)
class RiskResult:
    model: str
    alpha: float
    horizon: int
    var_pct: float
    es_pct: float
    var_usd: float
    es_usd: float
    se: float | None = None


def portfolio_returns(returns: pd.DataFrame | pd.Series, weights: np.ndarray | pd.Series | None
                      ) -> pd.Series:
    """Fixed-weight portfolio simple returns (or the series itself when already a portfolio)."""
    if isinstance(returns, pd.Series):
        return returns.dropna()
    if weights is None:
        raise ValueError("weights are required when returns has several columns")
    w = weights.reindex(returns.columns).to_numpy() if isinstance(weights, pd.Series) else np.asarray(weights)
    return pd.Series(returns.to_numpy() @ w, index=returns.index).dropna()


def evaluate(model: RiskModel, alphas, nav: float, horizon: int = 1) -> list[RiskResult]:
    out = []
    for a in alphas:
        v, e = model.var(a), model.es(a)
        se = getattr(model, "var_se", lambda _a: None)(a)
        out.append(RiskResult(model.name, a, horizon, v, e, v * nav, e * nav, se))
    return out
