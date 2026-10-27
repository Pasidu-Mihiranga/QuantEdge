"""Download the raw data snapshot (Step 02). Run explicitly; the app and pipeline never call this.

    python -m quantedge.data.download --refresh

Sources (brief §9.1 approved list): Yahoo Finance via yfinance, and FRED's public CSV endpoint.
"""

from __future__ import annotations

import argparse
import io
import time
from collections.abc import Callable
from datetime import UTC, datetime
from importlib.metadata import version

import pandas as pd
import requests

from quantedge.config import Config, load_config
from quantedge.data.manifest import ManifestEntry, sha256_file, write_manifest
from quantedge.paths import RAW

FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
PRICE_FIELDS = ["Open", "High", "Low", "Close", "Adj Close", "Volume", "Dividends", "Stock Splits"]


def _retry(fn: Callable, attempts: int = 3, base_delay: float = 2.0):
    for i in range(attempts):
        try:
            return fn()
        except Exception:
            if i == attempts - 1:
                raise
            time.sleep(base_delay * 2**i)


def _naive_dates(index: pd.Index) -> pd.DatetimeIndex:
    idx = pd.DatetimeIndex(index)
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    return idx.normalize()


def download_prices(tickers: list[str], start: str, end: str | None) -> pd.DataFrame:
    """Daily OHLC, Close, Adj Close, Volume and actions in long format (date, ticker, fields).

    `auto_adjust=False` keeps both Close and Adj Close so the adjustment factor can be audited.
    Downloads one ticker at a time (threads off) to avoid Yahoo rate limits.
    """
    import yfinance as yf

    frames = []
    for t in tickers:
        def fetch(t=t):
            df = yf.download(t, start=start, end=end, auto_adjust=False, actions=True,
                             progress=False, threads=False, multi_level_index=False)
            if df is None or df.empty:
                raise RuntimeError(f"yfinance returned no rows for {t}")
            return df

        df = _retry(fetch)
        df = df.reindex(columns=PRICE_FIELDS)
        df.index = _naive_dates(df.index)
        df.index.name = "date"
        df.columns = [c.lower().replace(" ", "_") for c in df.columns]
        frames.append(df.assign(ticker=t).reset_index())
    out = pd.concat(frames, ignore_index=True)
    return out.sort_values(["ticker", "date"]).reset_index(drop=True)


def parse_fred_csv(text: str, series_id: str) -> pd.Series:
    """Parse a FRED CSV. Handles both date-column names and the '.' missing-value marker."""
    df = pd.read_csv(io.StringIO(text), na_values=["."])
    date_col = "observation_date" if "observation_date" in df.columns else "DATE"
    s = pd.Series(pd.to_numeric(df[series_id], errors="coerce").to_numpy(dtype=float),
                  index=pd.DatetimeIndex(pd.to_datetime(df[date_col]), name="date"),
                  name=series_id)
    return s.sort_index()


def download_fred(series_id: str, timeout: float = 60.0) -> pd.Series:
    url = FRED_URL.format(series=series_id)

    def fetch():
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return r.text

    return parse_fred_csv(_retry(fetch), series_id)


def _entry(file: str, source: str, call: str, frame: pd.DataFrame, dates: pd.Series) -> ManifestEntry:
    libs = {}
    for lib in ("yfinance", "pandas", "pyarrow", "requests"):
        try:
            libs[lib] = version(lib)
        except Exception:
            libs[lib] = "n/a"
    return ManifestEntry(
        file=file, source=source, url_or_call=call,
        downloaded_utc=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        rows=len(frame), first_date=str(dates.min().date()), last_date=str(dates.max().date()),
        sha256=sha256_file(RAW / file), library_versions=libs,
    )


def main(cfg: Config, refresh: bool) -> None:
    if not refresh:
        print("Nothing to do: pass --refresh to download a new snapshot (this overwrites data/raw).")
        return
    RAW.mkdir(parents=True, exist_ok=True)
    start = cfg.data.start.strftime("%Y-%m-%d")
    end = None if cfg.data.end is None else (cfg.data.end + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    entries = []

    prices = download_prices(list(cfg.universe), start, end)
    prices.to_parquet(RAW / "prices.parquet", index=False)
    entries.append(_entry("prices.parquet", "Yahoo Finance (yfinance)",
                          f"yf.download({list(cfg.universe)}, start={start}, end={end}, "
                          "auto_adjust=False, actions=True, threads=False)",
                          prices, prices["date"]))

    for sid in cfg.data.fred_series:
        s = download_fred(sid)
        frame = s.to_frame()
        frame.to_parquet(RAW / f"fred_{sid}.parquet")
        entries.append(_entry(f"fred_{sid}.parquet", "FRED (St. Louis Fed)",
                              FRED_URL.format(series=sid), frame, s.index.to_series()))

    for e in fx_entries(cfg):
        entries.append(e)
    write_manifest(entries)
    _sanity_report(prices, entries)


def download_fx(ticker: str, start: str, end: str | None) -> pd.Series:
    """Daily FX close from Yahoo Finance (e.g. LKR=X: Sri Lankan rupees per US dollar)."""
    import yfinance as yf

    def fetch():
        df = yf.download(ticker, start=start, end=end, auto_adjust=False, progress=False, threads=False,
                         multi_level_index=False)
        if df is None or df.empty:
            raise RuntimeError(f"yfinance returned no rows for {ticker}")
        return df

    df = _retry(fetch)
    s = df["Close"].copy()
    s.index = _naive_dates(s.index)
    s.index.name = "date"
    return s.rename(ticker)


def fx_entries(cfg: Config) -> list[ManifestEntry]:
    """Download the configured FX series (memo context only; never used in USD risk models)."""
    start = cfg.data.start.strftime("%Y-%m-%d")
    end = None if cfg.data.end is None else (cfg.data.end + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    out = []
    for t in cfg.data.fx:
        s = download_fx(t, start, end)
        name = f"fx_{t.replace('=', '_')}.parquet"
        s.to_frame().to_parquet(RAW / name)
        out.append(_entry(name, "Yahoo Finance (yfinance)", f"yf.download({t!r}, start={start}, end={end})",
                          s.to_frame(), s.index.to_series()))
    return out


def _sanity_report(prices: pd.DataFrame, entries: list[ManifestEntry]) -> None:
    print("\nFirst / last valid Adj Close per ticker:")
    for t, g in prices.dropna(subset=["adj_close"]).groupby("ticker"):
        print(f"  {t:4s} {g['date'].min().date()} -> {g['date'].max().date()}  rows={len(g)}")
    print("\nFRED series:")
    for e in entries:
        if e.file.startswith("fred_"):
            print(f"  {e.file:28s} {e.first_date} -> {e.last_date}  rows={e.rows}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download the QuantEdge raw data snapshot.")
    parser.add_argument("--refresh", action="store_true", help="download and overwrite data/raw")
    args = parser.parse_args()
    main(load_config(), refresh=args.refresh)
