# Step 03: Data Cleaning, Quality Flags & Stationarity

**Owner:** D · **Week:** 1 (Days 2–3) · **Effort:** 1.5 days · **Depends on:** 02 · **Feeds:** 04

## 1. Target

- A clean, aligned daily panel of adjusted prices for the 7 ETFs, plus an aligned macro panel.
- A **CleaningLog**: an ordered, human-readable list of every transformation and every flag, shown on the Data & Quality page and printed in the report appendix.
- A stationarity table (ADF and KPSS) for prices and returns, per asset and for the portfolio.
- Suspect points are **flagged, never silently deleted**.

## 2. Why it matters

Brief §9.2 makes all of the following mandatory:
- adjusted close prices;
- calendar alignment, with documentation of how holidays were handled;
- log returns for statistics, with an explicit statement of where simple returns are used;
- flagging rather than deleting suspect data;
- an ADF test;
- every step reproducible in code.

Rubric: technical rigour (25%), plus "data sources and cleaning steps" is a required section of the report.

## 3. How to achieve it

### 3.1 Calendar alignment

- All 7 ETFs trade on US exchanges (NYSE Arca), so they share one calendar.
- Inner-join on dates where **all 7** have an `Adj Close`, and log the dates dropped for each ticker (there should be almost none).
- FRED series follow the Federal Reserve calendar, which differs on some holidays (e.g. Columbus Day). Align them to the ETF dates by forward-filling **at most 3 business days** and logging every fill.
- CPI is monthly: forward-fill to daily for display only. It is never used in daily risk models.

### 3.2 Quality flags (`quality.py`). Each flag records `{date, ticker, rule, value, threshold, action="flagged"}`

| Rule | Definition | Rationale |
|---|---|---|
| Stale price | Run of ≥ 5 consecutive identical `Adj Close` values | Feed outage or illiquidity |
| Jump | \|r_t\| > 6 × rolling 60-day σ computed on data up to t−1 | Implausible move with no look-ahead |
| Large negative | r_t < −20% in one day for an ETF | Possible split or data error |
| Non-positive price | price ≤ 0 | Invalid; the log is undefined |
| Adjustment break | Day-on-day change in `Adj/Close` ratio larger than 2%, not on an ex-dividend date | Bad dividend or split adjustment |
| Structural break | CUSUM test on returns (`statsmodels.stats.diagnostic.breaks_cusumolsresid`) per asset | Documents regime changes; informational only |

**Decision rule:** flags are kept in the data by default. Each flag is cross-checked against known market events (e.g. 2008-10, 2020-03); genuine crisis moves are **kept**, because removing them would understate tail risk. Only proven data errors may be corrected, and only in code with a log entry. Expect zero such errors on these liquid ETFs, and say so in the report.

### 3.3 Stationarity and stylised facts (`stats.py`)

- **ADF:** `adfuller(x, autolag="AIC")`. H0: unit root. Expect non-rejection for log prices and rejection for returns.
- **KPSS:** `kpss(x, regression="c", nlags="auto")`. H0: stationary. This is the complementary test; using both answers "ADF has low power".
- **Stylised facts** (they feed the VaR disagreement analysis in Step 08): skewness, excess kurtosis, Jarque-Bera, Ljung-Box on r (lag 10) and on r² (lag 10), and an ARCH-LM test.

## 4. Implementation plan

| # | Function | Output |
|---|---|---|
| 1 | `cleaning.py::CleaningLog` (dataclass list with `.add(step, detail, n_affected)` and `.to_frame()`) | Log object |
| 2 | `cleaning.py::align_calendar(prices, fred, log) -> (prices_aligned, macro_aligned)` | Aligned panels |
| 3 | `quality.py::run_quality_checks(prices, log) -> flags_df` | Flags table |
| 4 | `stats.py::stationarity_table(series_dict) -> DataFrame` with columns `adf_stat, adf_p, kpss_stat, kpss_p, verdict` | Table |
| 5 | `stats.py::stylised_facts(returns) -> DataFrame` | Table |
| 6 | `cleaning.py::build_clean_dataset(cfg) -> CleanData` (prices, macro, flags, log, stationarity, facts) | Single entry point used by the pipeline |
| 7 | Persist to `data/artifacts/clean_*.parquet` and `cleaning_log.csv` | Artifacts |

## 5. Acceptance tests

- Synthetic price series containing a planted stale run, jump, negative value and adjustment break: each rule fires exactly once and nothing is deleted.
- A random walk gives ADF non-rejection and its differences give rejection (p < 0.01).
- Forward-fill never exceeds 3 days (an assertion in code).
- Row count before and after alignment is logged, and the difference is fully explained by the log entries.

## 6. Pitfalls

- Deleting crisis days as "outliers", which destroys the tail you are asked to model.
- A jump rule that uses a rolling σ including day t (look-ahead) or centred windows.
- Forward-filling prices. Only macro series may be forward-filled, with a limit.
- Running ADF on prices, reporting "non-stationary" and stopping. You must test the **returns used for modelling**, i.e. the portfolio return series.

## 7. Defend it in Q&A

- *"Did you remove outliers?"* No. We flagged N points; each was checked against market events, all were genuine (or list exceptions), and they were kept because they *are* the tail risk.
- *"How did you handle holidays?"* All 7 funds share the US trading calendar, so we inner-joined. FRED holidays were forward-filled for at most 3 days, and every fill is logged.
- *"Are your returns stationary?"* ADF rejects the unit root and KPSS does not reject stationarity, for every asset and the portfolio (table X). But the returns are **not i.i.d.**: Ljung-Box on r² shows volatility clustering, which motivates GARCH (Step 08).
