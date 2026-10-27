"""Data-quality flags (Step 03 §3.2). Suspect points are flagged and logged, never deleted.

Each flag is a row {date, ticker, rule, value, threshold, action="flagged"}.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from statsmodels.stats.diagnostic import breaks_cusumolsresid

from quantedge.config import CleaningCfg

FLAG_COLUMNS = ["date", "ticker", "rule", "value", "threshold", "action"]
FLAG_DTYPES = {"date": "datetime64[ns]", "ticker": "str", "rule": "str",
               "value": "float64", "threshold": "float64", "action": "str"}


def _flag(date, ticker, rule, value, threshold) -> dict:
    return {"date": pd.Timestamp(date), "ticker": ticker, "rule": rule,
            "value": float(value), "threshold": float(threshold), "action": "flagged"}


def stale_runs(prices: pd.DataFrame, min_run: int) -> list[dict]:
    """One flag per run of >= `min_run` consecutive identical prices, dated at the run start."""
    flags = []
    for t in prices.columns:
        s = prices[t].dropna()
        new_run = s.ne(s.shift())
        run_id = new_run.cumsum()
        lengths = s.groupby(run_id).transform("size")
        starts = s.index[new_run & (lengths >= min_run)]
        flags += [_flag(d, t, "stale_price", lengths.loc[d], min_run) for d in starts]
    return flags


def jumps(returns: pd.DataFrame, n_sigma: float, window: int) -> list[dict]:
    """|r_t| > n_sigma x trailing sigma, where sigma uses returns up to t-1 only (no look-ahead)."""
    sigma = returns.rolling(window, min_periods=window).std().shift(1)
    hit = returns.abs() > n_sigma * sigma
    flags = []
    for t in returns.columns:
        for d in returns.index[hit[t].fillna(False).to_numpy()]:
            flags.append(_flag(d, t, "jump", returns.at[d, t], n_sigma * sigma.at[d, t]))
    return flags


def large_negatives(returns: pd.DataFrame, threshold: float) -> list[dict]:
    return [_flag(d, t, "large_negative", returns.at[d, t], threshold)
            for t in returns.columns
            for d in returns.index[(returns[t] < threshold).to_numpy()]]


def non_positive(prices: pd.DataFrame) -> list[dict]:
    return [_flag(d, t, "non_positive_price", prices.at[d, t], 0.0)
            for t in prices.columns
            for d in prices.index[(prices[t] <= 0).to_numpy()]]


def adjustment_breaks(adj_close: pd.DataFrame, close: pd.DataFrame, dividends: pd.DataFrame,
                      splits: pd.DataFrame, threshold: float) -> list[dict]:
    """Day-on-day change in Adj/Close above `threshold` that is not explained by an action date."""
    ratio = adj_close / close
    change = ratio.pct_change(fill_method=None).abs()
    explained = (dividends.reindex_like(ratio).fillna(0) != 0) | (splits.reindex_like(ratio).fillna(0) != 0)
    hit = (change > threshold) & ~explained
    return [_flag(d, t, "adjustment_break", change.at[d, t], threshold)
            for t in ratio.columns
            for d in ratio.index[hit[t].fillna(False).to_numpy()]]


def structural_breaks(returns: pd.DataFrame, alpha: float = 0.05) -> list[dict]:
    """CUSUM test on OLS residuals of returns on a constant (informational only).

    A flag is dated at the maximum of the absolute cumulative residual sum, the most likely break.
    """
    flags = []
    for t in returns.columns:
        r = returns[t].dropna()
        if len(r) < 30:
            continue
        resid = (r - r.mean()).to_numpy()
        _, pvalue, _ = breaks_cusumolsresid(resid, ddof=1)
        if pvalue < alpha:
            d = r.index[int(np.argmax(np.abs(np.cumsum(resid))))]
            flags.append(_flag(d, t, "structural_break", pvalue, alpha))
    return flags


def run_quality_checks(adj_close: pd.DataFrame, close: pd.DataFrame, dividends: pd.DataFrame,
                       splits: pd.DataFrame, cfg: CleaningCfg) -> pd.DataFrame:
    returns = adj_close.pct_change(fill_method=None).iloc[1:]
    flags = (
        stale_runs(adj_close, cfg.stale_run)
        + jumps(returns, cfg.jump_sigma, cfg.jump_window)
        + large_negatives(returns, cfg.large_negative)
        + non_positive(adj_close)
        + adjustment_breaks(adj_close, close, dividends, splits, cfg.adj_break)
        + structural_breaks(returns)
    )
    out = pd.DataFrame(flags, columns=FLAG_COLUMNS).astype(FLAG_DTYPES)  # same schema with or without flags
    return out.sort_values(["date", "ticker", "rule"]).reset_index(drop=True)
