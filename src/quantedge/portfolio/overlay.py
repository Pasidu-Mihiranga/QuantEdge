"""Volatility-target risk overlay (Step 14 B), backtested walk-forward with costs.

At the end of each week, with sigma_hat the one-step GARCH forecast of the strategic portfolio's
volatility (known at that date), scale the risky sleeve by s = min(1, target / sigma_hat) and move
the difference into the safe asset (AGG, or a T-bill CASH sleeve). Target changes are limited by a
monthly one-way turnover cap. With target = infinity the overlay reproduces the static portfolio.

The overlay is tactical: it may hold the safe asset above its strategic IPS cap while de-risking.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from quantedge.portfolio import metrics
from quantedge.portfolio.walkforward import historical_es, simulate, worst_window_drawdown
from quantedge.portfolio.weights_path import point_in_time_weights


@dataclass(frozen=True)
class OverlayResult:
    perf: pd.Series
    weights_history: pd.DataFrame
    turnover: pd.Series
    scale: pd.Series            # risky-sleeve scale applied at each decision date


def overlay_weights(base_wh: pd.DataFrame, sigma_daily: pd.Series, dates: pd.DatetimeIndex, target_ann: float,
                    safe: str = "AGG", turnover_cap: float = 0.20, warmup: dict | None = None) -> tuple[pd.DataFrame, pd.Series]:
    """Target-weight history of the overlay (base rebalances plus weekly changes) and the scales."""
    cols = base_wh.columns
    base_path = point_in_time_weights(base_wh, dates, warmup or {cols[0]: 1.0})
    week_end = pd.Series(dates, index=dates).groupby(dates.to_period("W-FRI")).max()
    decisions = sorted(set(week_end[week_end >= base_wh.index[0]]) | set(base_wh.index))
    risky = [c for c in cols if c != safe]
    current = base_wh.iloc[0].to_numpy(float)
    rows, scales, used, month = {base_wh.index[0]: current.copy()}, {}, 0.0, None
    for d in decisions:
        if d not in base_path.index:
            continue
        base = base_path.loc[d].to_numpy(float)
        sig = float(sigma_daily.get(d, np.nan)) * np.sqrt(252)
        s = 1.0 if not np.isfinite(sig) or sig <= 0 else min(1.0, target_ann / sig)
        want = base.copy()
        idx = [cols.get_loc(c) for c in risky]
        moved = (1.0 - s) * base[idx].sum()
        want[idx] *= s
        want[cols.get_loc(safe)] += moved
        if d.to_period("M") != month:
            month, used = d.to_period("M"), 0.0
        change = 0.5 * np.abs(want - current).sum()
        if d in base_wh.index:                       # strategic rebalances are always applied
            new = want
        elif change <= 1e-9:
            scales[d] = s
            continue
        else:
            frac = min(1.0, max(0.0, turnover_cap - used) / change)
            new = current + frac * (want - current)
        used += 0.5 * np.abs(new - current).sum()
        if np.abs(new - current).sum() > 1e-9 or d in base_wh.index:
            rows[d] = new
            current = new
        scales[d] = s
    wh = pd.DataFrame(rows, index=cols).T.sort_index()
    return wh, pd.Series(scales, name="scale")


def vol_target_backtest(returns: pd.DataFrame, base_wh: pd.DataFrame, sigma_daily: pd.Series, target_ann: float,
                        safe: str = "AGG", turnover_cap: float = 0.20, cost_bps: float = 5.0) -> OverlayResult:
    wh, scale = overlay_weights(base_wh, sigma_daily, returns.index, target_ann, safe, turnover_cap)
    perf, turnover = simulate(returns[wh.columns], wh, cost_bps)
    return OverlayResult(perf, wh, turnover, scale)


def compare(results: dict[str, pd.Series], windows: dict[str, tuple[str, str]], turnovers: dict[str, pd.Series]) -> pd.DataFrame:
    rows = []
    for name, r in results.items():
        r = r.dropna()
        crisis = {f"dd {k}": -metrics.max_drawdown(r.loc[a:b]) for k, (a, b) in windows.items() if len(r.loc[a:b]) > 5}
        rows.append({"strategy": name, "cagr": metrics.cagr(r), "volatility": metrics.volatility(r),
                     "max_drawdown": -metrics.max_drawdown(r), "es99": historical_es(r),
                     "calmar": metrics.calmar(r), "worst_crisis_dd": worst_window_drawdown(r, windows)[0],
                     "turnover_ann": float(turnovers[name].iloc[1:].sum() / (len(r) / 252)), **crisis})
    return pd.DataFrame(rows).set_index("strategy")
