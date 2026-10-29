# Exception log: the champion's 99% VaR breaches on validation (2019–2022)

**Model:** GJR conditional EVT on the 35%-equity frontier portfolio, 500-day window (notebook 04 §6).
**Result:** 14 breaches against 10.1 expected (Kupiec p = 0.24, Christoffersen p = 0.53, Basel green).
**Method:** each breach is checked two ways. (1) Our own data: which holdings lost, how rates, the VIX and oil moved, and the loss against the model's own ES forecast (notebook 04, breach anatomy). (2) Contemporaneous news reports. Basel (1996) categories: a loss no larger than the forecast ES is **bad luck** (the size of 1-in-100 loss the model expected); a larger one means **the market moved more than forecast**; a data error would be **data integrity** (none found).
**Status:** drafted with AI assistance on 2026-10-29; causes verified against the sources below; **owner to review**.

| Date | Loss (% NAV) | VaR | Loss ÷ ES forecast | Stocks and bonds fell together | Category | Cause | Source |
|---|---|---|---|---|---|---|---|
| 2019-05-13 | 0.74% | 0.67% | 0.95 | no | bad luck | US–China trade war: China retaliates with tariffs on $60bn of US goods; S&P 500 −2.4%, VIX +28% | [CNN](https://edition.cnn.com/2019/05/13/investing/dow-stocks-today), [NPR](https://www.kut.org/2019-05-13/china-puts-new-tariffs-on-60-billion-of-u-s-goods-and-stock-prices-reel) |
| 2019-10-02 | 0.64% | 0.58% | 0.99 | no | bad luck | Growth scare: ISM manufacturing 47.8, lowest since June 2009 (released 1 Oct); S&P 500 −1.8% | [CNBC](https://www.cnbc.com/2019/10/02/the-dow-is-down-over-800-points-in-two-days-heres-whats-happening.html), [Fortune](https://www.fortune.com/2019/10/02/dow-down-manufacturing-growth-fears) |
| 2020-01-27 | 0.49% | 0.42% | 1.07 | no | market moved more | First COVID scare: Wuhan outbreak spreads, 81 deaths; S&P 500 −1.6% | [CNBC](https://www.cnbc.com/2020/01/27/what-happened-to-the-stock-market-monday-coronavirus-sends-stocks-plunging.html), [NBC](https://www.nbcnews.com/business/markets/dow-set-open-down-450-points-coronavirus-fears-rock-global-n1123681) |
| 2020-02-24 | 1.13% | 0.50% | 2.11 | no | market moved more | COVID spreads in Italy | (earlier log) |
| 2020-02-27 | 1.19% | 1.15% | 0.96 | no | bad luck | COVID sell-off | (earlier log) |
| 2020-03-09 | 2.90% | 1.60% | 1.43 | yes | market moved more | COVID and the Saudi–Russia oil price war (XLE −20%; outlier flag confirmed as a real move) | (earlier log) |
| 2020-03-12 | 6.33% | 4.23% | 1.19 | yes | market moved more | COVID: US travel ban; dash for cash hits bonds too (outlier flag confirmed as a real move) | (earlier log) |
| 2020-06-11 | 2.08% | 0.90% | 1.77 | yes | market moved more | Second-wave fears (Texas, Florida, Arizona) and a gloomy Fed outlook; S&P 500 −5.9% | [NPR](https://www.wbur.org/npr/874600108/stocks-tumble-as-the-fed-warns-of-a-long-recovery-coronavirus-cases-spike), [InvestmentNews](https://www.investmentnews.com/dow-drops-almost-7-on-economy-virus-fears-193959) |
| 2020-10-28 | 1.25% | 1.05% | 0.82 | yes | bad luck | COVID surge in the US and Europe, new lockdowns; S&P 500 −3.5% | [ABC News](https://abc7news.com/stocks-punge-dow-jones-stock-market/7421224/) |
| 2021-01-27 | 0.83% | 0.80% | 0.71 | no | bad luck | Fed statement; hedge funds de-risk during the GameStop squeeze; S&P 500 −2.6% | [AP via KSL](https://www.ksl.com/article/50095337/stocks-slump-to-worst-day-in-three-months-in-wake-of-fed-statement), [MarketBeat](https://www.marketbeat.com/articles/stocks-have-their-worst-day-since-october-as-big-tech-sinks-2021-01-27) |
| 2021-02-25 | 1.30% | 0.78% | 1.19 | yes | market moved more | Bond tantrum: record-weak 7-year auction, 10-year yield above 1.6%; Nasdaq-100 −3.5% | [FXStreet](https://www.fxstreet.com/news/forex-today-turmoil-in-bond-markets-202102251950), [City Index](https://www.cityindex.co.uk/market-analysis/7-year-auction-preview-will-it-be-as-bad-as-februarys-auction/) |
| 2021-11-10 | 0.78% | 0.72% | 0.68 | yes | bad luck | US CPI 6.2%, highest since 1990; stocks and Treasuries fall; S&P 500 −0.8% | [Bloomberg](https://www.bloomberg.com/news/articles/2021-11-10/inflation-builds-with-biggest-gain-in-consumer-prices-since-1990), [S&P Global](https://www.spglobal.com/market-intelligence/en/news-insights/research/daily-global-market-summary-10-november-2021) |
| 2022-03-07 | 1.42% | 1.24% | 0.78 | yes | bad luck | Russia–Ukraine: oil near $130 on talk of a ban on Russian oil; S&P 500 −3.0% | [Boston Globe](https://www.bostonglobe.com/2022/03/07/business/stocks-closed-sharply-down-monday-after-oil-prices-surged), [KPBS/NPR](https://www.kpbs.org/news/national/2022/03/07/it-keeps-getting-worse-for-stocks-dow-sinks-and-enters-whats-called-a-correction) |
| 2022-06-13 | 2.33% | 2.05% | 0.89 | yes | bad luck | US CPI surprise; a 75 bp Fed hike expected | (earlier log) |

## What the log shows (notebook 04)
- 14 of 14 breaches have a documented market cause; 0 data errors.
- 8 bad luck, 6 market moved more than forecast; the six are all sudden calm-to-stress switches.
- Loss ÷ ES forecast on breach days: mean 1.11, bootstrap 90% interval 0.95–1.29 (no evidence the ES is too low on average).
- 7 of 14 breaches in the lowest-VaR third of days (Fisher exact p = 0.25: right direction, not significant).
- Gaps between breaches: median 63 trading days vs 69 if independent (KS p = 0.18).
- Stocks and bonds fell together on 8 of 14 breach days, including every breach from February 2021 on (hypothesis H1, the rate-hiking regime).

## Data-quality flag checked against market events
- **2026-01-30, GLD −10.3%:** genuine. Spot gold fell about 9.5% (February futures −11.4%), widely reported as its largest one-day fall since 1983, after the nomination of a new Fed chair seen as less dovish and a stronger dollar ([The Peninsula](https://thepeninsulaqatar.com/article/31/01/2026/gold-prices-post-biggest-one-day-drop-in-four-decades), [WisdomTree](https://www.wisdomtree.com/investments/blog/2026/02/05/golds-violent-reset-a-correction-not-a-collapse)). Kept, as the data rules require. (A news check only; no statistic was computed on 2023+ data.)
