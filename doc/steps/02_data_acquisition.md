# Step 02: Data Acquisition & Snapshot

**Owner:** D · **Week:** 1 (Days 1–2) · **Effort:** 1 day · **Depends on:** 01 · **Feeds:** 03

## 1. Target

- Daily price history for the 7 ETFs (adjusted and unadjusted close, plus volume) from **2004-11-18** (GLD inception) to the snapshot date.
- FRED macro series for the risk-free rate, CAPM inputs and stress factors.
- All raw data frozen in `data/raw/*.parquet`, with a `manifest.json` proving provenance (source, timestamp, rows, date range, SHA-256).
- The app and pipeline **only read the snapshot**. A refresh happens only when someone explicitly runs it.

## 2. Why it matters

- Brief §9.1: approved sources are Yahoo Finance (via `yfinance`), FRED, and World Bank/IMF. An undisclosed source is a rubric violation.
- Brief §9.1: reproducibility by the judges is graded. yfinance rate-limits, occasionally revises history and changes its API, so a live download at judging time could change the numbers or fail.

## 3. How to achieve it

### Yahoo Finance

- Call `yf.download(universe, start, end, auto_adjust=False, actions=True, progress=False, group_by="ticker", threads=False)`.
- Keep **both** `Close` and `Adj Close`. Use `Adj Close` for returns and keep `Close` so the adjustment factor (`Adj Close / Close`) can be audited for dividends and splits in Step 03.
- Retry with exponential backoff (3 attempts) and download per ticker if the batch call fails.

### FRED

Download via the public CSV endpoint `https://fred.stlouisfed.org/graph/fredgraph.csv?id=<SERIES>`. It needs no API key and avoids the poorly maintained `pandas-datareader`.

- Parse missing values: `"."` becomes NaN.
- The date column is `observation_date` (older files use `DATE`); handle both.

| Series | Use | Frequency |
|---|---|---|
| DTB3 | Risk-free rate (3-month T-bill, discount basis) | Daily |
| DGS10 | 10-year yield; rate-shock factor | Daily |
| VIXCLS | Volatility regime and stress factor | Daily |
| CPIAUCSL | Inflation, for the return objective | Monthly |
| DCOILWTICO | Oil factor for stress | Daily |
| BAMLH0A0HYM2 | High-yield credit spread factor | Daily |
| DTWEXBGS | Broad USD index factor | Daily (from 2006) |

### Optional (World Bank / IMF, memo context only)

- Sri Lanka CPI and the USD/LKR rate: World Bank indicator `PA.NUS.FCRF` (annual).
- Or `LKR=X` from yfinance; verify the history length before relying on it.

## 4. Implementation plan

| # | Function / file | Detail |
|---|---|---|
| 1 | `data/download.py::download_prices(tickers, start, end) -> pd.DataFrame` | MultiIndex columns (field, ticker); retry/backoff; raises if any ticker has 0 rows |
| 2 | `data/download.py::download_fred(series_id) -> pd.Series` | CSV fetch with timeout; NaN parsing; float dtype; name = series_id |
| 3 | `data/manifest.py::write_manifest(files) / verify_manifest()` | Records `{file, source, url_or_call, downloaded_utc, rows, first_date, last_date, sha256, library_versions}` |
| 4 | `data/download.py::main(refresh: bool)` | CLI: `python -m quantedge.data.download --refresh`; writes `data/raw/prices.parquet`, `data/raw/fred_<id>.parquet` and the manifest |
| 5 | `data/load.py::load_raw()` | Reads the snapshot and calls `verify_manifest()`; a hash mismatch raises a clear error |
| 6 | Sanity report | Prints first and last date per ticker and per FRED series, missing counts and the GLD start date |

## 5. Acceptance tests

- `tests/test_download.py` uses mocked HTTP responses for FRED, covering the `observation_date`/`DATE` variants and the `"."` NaN.
- Every ticker's first valid date is on or before 2004-11-18, except GLD, which starts exactly then.
- Manifest hashes match the files; editing one byte makes `verify_manifest()` fail.
- With network disabled, `load_raw()` still works, proving the app does not depend on the network.

## 6. Pitfalls

- Using `auto_adjust=True` and then being unable to show the adjustment audit. Keep both closes.
- The yfinance default `threads=True` causing rate-limit failures.
- Silently forward-filling FRED gaps at download time. Download raw data; clean in Step 03.
- A timezone-aware index from yfinance. Normalise to naive dates (`tz_localize(None)`).
- Committing data without the manifest, so the judges cannot verify provenance.

## 7. Defend it in Q&A

- *"Why start in November 2004?"* GLD is the youngest ETF. Using a common sample avoids mixing different histories in the covariance matrix, and this window still contains the GFC, COVID and 2022.
- *"Why not use proxies for a longer history?"* Proxies add basis error and are not the investable instruments. The 20-year window already covers three major crises.
- *"What if Yahoo revises the data?"* Our snapshot is frozen and hashed, and refreshing is an explicit, logged action.
