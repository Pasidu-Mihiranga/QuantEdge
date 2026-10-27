"""Investment Policy Statement: return objective, risk limits and optimiser constraints (Step 05).

Limits come from the client's tolerance (spending impact, committee beliefs), never from what a
chosen portfolio happens to achieve. Calibration uses data up to the end of validation only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import linprog

from quantedge.portfolio.returns import CASH


def required_return(cpi: pd.Series, spending_rate: float, cost_drag: float, years: int = 10,
                    as_of: pd.Timestamp | None = None) -> dict[str, float]:
    """Required nominal return = spending rate + expected inflation + costs.

    Expected inflation is the average year-on-year CPI change over the last `years` years of
    monthly CPIAUCSL observations available at `as_of`.
    """
    s = cpi.dropna()
    if as_of is not None:
        s = s.loc[:as_of]
    monthly = s.resample("ME").last().dropna()
    yoy = monthly.pct_change(12).dropna()
    window = yoy.iloc[-12 * years:]
    inflation = float(window.mean())
    return {
        "spending_rate": spending_rate,
        "inflation": inflation,
        "cost_drag": cost_drag,
        "required_return": spending_rate + inflation + cost_drag,
        "cpi_window_start": str(window.index.min().date()),
        "cpi_window_end": str(window.index.max().date()),
    }


@dataclass(frozen=True)
class LimitCheck:
    name: str
    value: float
    limit: float
    kind: str          # "max" or "min"
    passed: bool
    margin: float      # positive = headroom, negative = breach


@dataclass(frozen=True)
class IPSLimits:
    vol_ann_max: float
    stress_drawdown_max: float
    es99_1d_max: float
    es99_10d_max: float
    single_asset_max: float
    asset_caps: dict[str, float] = field(default_factory=dict)
    asset_floors: dict[str, float] = field(default_factory=dict)
    equity_group: tuple[str, ...] = ()
    equity_max: float = 1.0
    cash_max: float = 0.0

    def cap(self, ticker: str) -> float:
        """Upper weight bound: an asset-specific cap replaces the general single-asset cap
        (so AGG can be allowed above 40% while XLE/XLK/EEM/GLD keep their tighter caps)."""
        if ticker == CASH:
            return self.cash_max
        return self.asset_caps.get(ticker, self.single_asset_max)

    @classmethod
    def from_config(cls, ips: dict[str, Any], variant: str | None = None) -> IPSLimits:
        """Limits from `config.yaml -> ips`; `variant` applies an `ips_variants` override (sensitivity)."""
        lim = {k: (dict(v) if isinstance(v, dict) else v) for k, v in ips["limits"].items()}
        if variant is not None:
            for k, v in ips["variants"][variant].items():
                lim[k] = {**lim.get(k, {}), **v} if isinstance(v, dict) else v
        lim["equity_group"] = tuple(lim.get("equity_group", ()))
        return cls(**lim)

    def check(self, metrics: dict[str, Any], tol: float = 1e-9) -> list[LimitCheck]:
        """Check risk metrics and weights against every limit; equality counts as a pass.

        `metrics` may contain vol_ann, stress_drawdown (positive fraction), es99_1d, es99_10d and
        weights (a Series indexed by ticker). Missing metrics are skipped.
        """
        out: list[LimitCheck] = []

        def add(name, value, limit, kind):
            margin = (limit - value) if kind == "max" else (value - limit)
            out.append(LimitCheck(name, float(value), float(limit), kind, margin >= -tol, float(margin)))

        for key, limit in [("vol_ann", self.vol_ann_max),
                           ("stress_drawdown", self.stress_drawdown_max),
                           ("es99_1d", self.es99_1d_max),
                           ("es99_10d", self.es99_10d_max)]:
            if key in metrics and metrics[key] is not None:
                add(key, metrics[key], limit, "max")
        w = metrics.get("weights")
        if w is not None:
            w = pd.Series(w, dtype=float)
            for t, x in w.items():
                if t == CASH:
                    add(f"weight {t}", x, self.cash_max, "max")
                    continue
                add(f"weight {t}", x, self.cap(t), "max")
                if t in self.asset_floors:
                    add(f"weight {t} floor", x, self.asset_floors[t], "min")
            equity = w.reindex(list(self.equity_group), fill_value=0.0).sum()
            add("equity total", equity, self.equity_max, "max")
        return out


@dataclass(frozen=True)
class OptimizerConstraints:
    tickers: tuple[str, ...]
    lower: np.ndarray
    upper: np.ndarray
    A_ub: np.ndarray       # A_ub @ w <= b_ub
    b_ub: np.ndarray
    feasible_point: np.ndarray


def constraints_for_optimizer(limits: IPSLimits, tickers: list[str] | tuple[str, ...]) -> OptimizerConstraints:
    """Convert the IPS into long-only box bounds, group caps and sum(w) = 1.

    Raises ValueError if no fully invested portfolio satisfies the limits.
    """
    tickers = tuple(tickers)
    n = len(tickers)
    lower = np.array([limits.asset_floors.get(t, 0.0) for t in tickers])
    upper = np.array([
        limits.cap(t)
        for t in tickers
    ])
    rows, rhs = [], []
    equity = np.array([1.0 if t in limits.equity_group else 0.0 for t in tickers])
    if equity.any():
        rows.append(equity)
        rhs.append(limits.equity_max)
    A_ub = np.array(rows) if rows else np.zeros((0, n))
    b_ub = np.array(rhs)

    # Feasibility LP (zero objective): any point satisfying bounds, group caps and full investment.
    res = linprog(c=np.zeros(n), A_ub=A_ub if rows else None, b_ub=b_ub if rows else None,
                  A_eq=np.ones((1, n)), b_eq=[1.0], bounds=list(zip(lower, upper, strict=True)),
                  method="highs")
    if not res.success:
        raise ValueError(f"IPS constraints are infeasible for {tickers}: {res.message}")
    return OptimizerConstraints(tickers, lower, upper, A_ub, b_ub, res.x)
