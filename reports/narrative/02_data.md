### Sources

All data come from the approved sources. Prices are Yahoo Finance adjusted closes for the seven ETFs, through `yfinance`. Rates, inflation expectations and stress factors are FRED series (10-year and 2-year Treasury, 10-year TIPS, breakeven inflation, 3-month T-bill, Baa spread, oil, dollar index, VIX, CPI). Sri Lankan inflation is World Bank data, used for context. The equity premium is a disclosed assumption, not data.

The raw download is frozen in `data/raw/` with a SHA-256 hash for every file, so the judges can rebuild every number from the repository.

### Cleaning

- **Period:** 18 November 2004, when GLD began trading, to 26 October 2026: 5,518 trading days.
- **Calendars:** all seven ETFs trade on US exchanges, so the inner join on trading dates dropped 0 days. FRED series have their own holidays and were carried forward by at most 3 business days.
- **Adjusted prices:** used throughout, so dividends and splits do not distort returns. We verified this against close prices plus dividends.
- **Log and simple returns:** log returns for statistics on one series; simple returns wherever assets are combined, because only simple returns add across assets.
- **Risk-free rate:** the 3-month T-bill, lagged one day, so no estimate uses information from the same day.
- **Partition:** development 2004–2018, validation 2019–2022, final test 2023–2026. Every selection used data to 2022 only.

### Quality flags

Suspect points are flagged and kept, never deleted. Every one matches a real event, such as the AGG fall of 10 October 2008 and the COVID crash, and none is a data error. Deleting them would remove the crises the fund must survive.

{{flags}}

### Statistical properties

ADF and KPSS agree: log prices have a unit root and log returns are stationary. Returns have fat tails and volatility clustering in every series (Jarque-Bera and ARCH-LM p ≈ 0). This is why a normal model is not enough, and why GARCH and EVT are in the study. AGG has the fattest tails of all, because bonds are usually calm and occasionally are not.

{{facts}}

The sample excludes the 2000–02 technology crash and the 1970s inflation, a limitation we return to in section 10.
