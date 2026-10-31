All data come from approved sources: Yahoo Finance for the seven ETFs and FRED for rates, inflation and stress factors, with World Bank data for Sri Lanka CPI context. The snapshot is frozen and hashed, so results reproduce from the repository.

- **Period:** 18 November 2004, when the last fund (GLD) began trading, to 26 October 2026.
- **Prices:** adjusted close, aligned on days when all seven funds traded.
- **Returns:** log returns for single-series statistics; simple returns wherever assets are combined, because only simple returns add across assets.
- **Flags:** 25 suspect points were flagged and kept. Each was checked against market events; none was a data error.
- **Stationarity:** ADF and KPSS agree that prices are non-stationary and returns stationary.
- **Stylised facts:** fat tails and volatility clustering in every series, which is why GARCH and EVT are needed.

The sample excludes the 2000–02 technology crash and the 1970s inflation, a limitation we state.
