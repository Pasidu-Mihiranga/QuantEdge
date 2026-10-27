"""Calendar alignment, cleaning log and the clean dataset (Step 03).

Mechanical cleaning (alignment, fills, flags) covers every date. Statistical *looks*
(stationarity, stylised facts) stop at the end of validation until the methodology freeze
(Step 22 §3.3).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from quantedge.config import Config
from quantedge.data.load import RawData, load_raw
from quantedge.data.partition import Partition
from quantedge.data.quality import run_quality_checks
from quantedge.data.stats import stationarity_table, stylised_facts
from quantedge.paths import ARTIFACTS

MONTHLY_SERIES = ("CPIAUCSL",)


@dataclass
class CleaningLog:
    """Ordered, human-readable record of every transformation (shown on the Data page)."""

    entries: list[dict] = field(default_factory=list)

    def add(self, step: str, detail: str, n_affected: int = 0) -> None:
        self.entries.append({"order": len(self.entries) + 1, "step": step,
                             "detail": detail, "n_affected": int(n_affected)})

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.entries, columns=["order", "step", "detail", "n_affected"])


def align_fred(s: pd.Series, dates: pd.DatetimeIndex, limit: int, log: CleaningLog) -> pd.Series:
    """Map a FRED series onto the ETF calendar, carrying a value forward at most `limit` business days.

    Each ETF date takes the latest FRED observation dated on or before it; if that observation is
    more than `limit` business days old the value is left missing. Every carried value is logged.
    """
    valid = s.dropna()
    if valid.empty:
        log.add("align_macro", f"{s.name}: no observations", len(dates))
        return pd.Series(np.nan, index=dates, name=s.name)
    values = valid.reindex(dates, method="ffill")
    obs_date = pd.Series(valid.index, index=valid.index).reindex(dates, method="ffill")
    known = obs_date.notna()
    gap = pd.Series(0, index=dates)
    gap[known] = np.busday_count(obs_date[known].to_numpy().astype("datetime64[D]"),
                                 dates[known.to_numpy()].to_numpy().astype("datetime64[D]"))
    too_old = known & (gap > limit)
    values[too_old] = np.nan
    filled = int(((gap > 0) & (gap <= limit)).sum())
    assert (gap[values.notna()] <= limit).all(), "forward-fill exceeded the configured limit"
    log.add("align_macro", f"{s.name}: carried forward {filled} days (limit {limit} business days); "
            f"{int(values.isna().sum())} days remain missing", filled)
    return values.rename(s.name)


def align_calendar(raw: RawData, cfg: Config, log: CleaningLog) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Inner-join the ETFs on dates where all have an Adj Close, then align the macro panel."""
    adj = raw.adj_close[list(cfg.universe)]
    adj = adj.loc[adj.index >= cfg.data.start]
    if cfg.data.end is not None:
        adj = adj.loc[adj.index <= cfg.data.end]
    log.add("load", f"Adj Close panel {adj.index.min().date()} to {adj.index.max().date()}, "
            f"{len(adj)} dates x {adj.shape[1]} tickers", len(adj))
    complete = adj.notna().all(axis=1)
    for t in adj.columns:
        n_missing = int((adj[t].isna() & adj.drop(columns=t).notna().any(axis=1)).sum())
        if n_missing:
            log.add("align_etf", f"{t}: {n_missing} dates missing while other tickers traded", n_missing)
    dropped = int((~complete).sum())
    prices = adj.loc[complete]
    log.add("align_etf", f"Inner join on dates where all {adj.shape[1]} ETFs trade: kept "
            f"{len(prices)}, dropped {dropped}", dropped)

    macro = {}
    for name, s in raw.fred.items():
        if name in MONTHLY_SERIES:
            macro[name] = s.dropna().reindex(prices.index, method="ffill")
            log.add("align_macro", f"{name}: monthly series carried forward for display only "
                    "(never used in daily risk models)", int(macro[name].notna().sum()))
        else:
            macro[name] = align_fred(s, prices.index, cfg.cleaning.ffill_limit_fred, log)
    return prices, pd.DataFrame(macro, index=prices.index)


@dataclass(frozen=True)
class CleanData:
    prices: pd.DataFrame
    close: pd.DataFrame
    dividends: pd.DataFrame
    splits: pd.DataFrame
    macro: pd.DataFrame
    flags: pd.DataFrame
    log: pd.DataFrame
    stationarity: pd.DataFrame
    facts: pd.DataFrame
    analysis_end: pd.Timestamp


def build_clean_dataset(cfg: Config, raw: RawData | None = None,
                        frozen: bool | None = None, write: bool = True) -> CleanData:
    """Single entry point for Step 03, used by the pipeline."""
    raw = raw if raw is not None else load_raw()
    log = CleaningLog()
    prices, macro = align_calendar(raw, cfg, log)
    close = raw.close.reindex(index=prices.index, columns=prices.columns)
    dividends = raw.dividends.reindex(index=prices.index, columns=prices.columns).fillna(0.0)
    splits = raw.splits.reindex(index=prices.index, columns=prices.columns).fillna(0.0)

    flags = run_quality_checks(prices, close, dividends, splits, cfg.cleaning)
    for rule, n in flags["rule"].value_counts().sort_index().items():
        log.add("quality_flag", f"{rule}: {n} points flagged and kept (no deletion)", n)

    part = Partition.from_config(cfg)
    end = part.visible_end(frozen)
    window = prices if end is None else prices.loc[:end]
    log.add("analysis_window", "Stationarity and stylised facts use data up to "
            f"{window.index.max().date()} (test period locked until the methodology freeze)",
            len(window))
    log_prices = np.log(window)
    log_returns = log_prices.diff().iloc[1:]
    simple = window.pct_change().iloc[1:]
    bench = sum(simple[t] * w for t, w in cfg.benchmark.items())
    series = {f"{t} log price": log_prices[t] for t in window.columns}
    series |= {f"{t} log return": log_returns[t] for t in window.columns}
    series["60/40 benchmark log return"] = np.log1p(bench)
    stationarity = stationarity_table(series)
    facts = stylised_facts(log_returns.assign(**{"60/40 benchmark": np.log1p(bench)}))

    out = CleanData(prices=prices, close=close, dividends=dividends, splits=splits, macro=macro,
                    flags=flags, log=log.to_frame(), stationarity=stationarity, facts=facts,
                    analysis_end=window.index.max())
    if write:
        write_clean(out)
    return out


def write_clean(data: CleanData) -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    data.prices.to_parquet(ARTIFACTS / "clean_prices.parquet")
    data.macro.to_parquet(ARTIFACTS / "clean_macro.parquet")
    data.dividends.to_parquet(ARTIFACTS / "clean_dividends.parquet")
    data.flags.to_parquet(ARTIFACTS / "quality_flags.parquet", index=False)
    data.stationarity.to_parquet(ARTIFACTS / "stationarity.parquet")
    data.facts.to_parquet(ARTIFACTS / "stylised_facts.parquet")
    data.log.to_csv(ARTIFACTS / "cleaning_log.csv", index=False)
