"""Offline access to the frozen raw snapshot (Step 02). Never touches the network."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from quantedge.data.manifest import verify_manifest
from quantedge.paths import MANIFEST, RAW


@dataclass(frozen=True)
class RawData:
    """Wide (date x ticker) price panels plus the raw FRED series, exactly as downloaded."""

    adj_close: pd.DataFrame
    close: pd.DataFrame
    volume: pd.DataFrame
    dividends: pd.DataFrame
    splits: pd.DataFrame
    fred: dict[str, pd.Series]


def _wide(prices: pd.DataFrame, field: str) -> pd.DataFrame:
    out = prices.pivot(index="date", columns="ticker", values=field).sort_index()
    out.columns.name = None
    out.index = pd.DatetimeIndex(out.index, name="date")
    return out


def load_raw(raw_dir: Path = RAW, manifest: Path = MANIFEST, verify: bool = True) -> RawData:
    """Load the snapshot; by default verify every file against the manifest first."""
    entries = verify_manifest(manifest, raw_dir) if verify else None
    prices = pd.read_parquet(raw_dir / "prices.parquet")
    fred_files = (
        [e.file for e in entries if e.file.startswith("fred_")]
        if entries is not None
        else sorted(p.name for p in raw_dir.glob("fred_*.parquet"))
    )
    fred = {}
    for f in fred_files:
        frame = pd.read_parquet(raw_dir / f)
        fred[frame.columns[0]] = frame.iloc[:, 0]
    return RawData(
        adj_close=_wide(prices, "adj_close"),
        close=_wide(prices, "close"),
        volume=_wide(prices, "volume"),
        dividends=_wide(prices, "dividends").fillna(0.0),
        splits=_wide(prices, "stock_splits").fillna(0.0),
        fred=fred,
    )
