"""Plain-language text for the committee pages, taken from doc/decisions/inputs_lock.md (locked 2026-10-29)."""

DECISIONS = [
    ("D1", "Spending rate and objective", "3.0% a year; objective US inflation + 3.5% (3% spending + 0.5% real growth)",
     "2.5–3.5%", "The fund must preserve and grow its capital. A conservative mix of these funds can sustain "
     "about 3% with real growth; peers' 4–5% would need far more equity risk."),
    ("D2", "Crisis budget", "Lose at most 25% in a crisis (historical replays and our scenario)", "20–30%",
     "The one preference that sets everything else: it allows about 36% equity, and the volatility and tail-loss limits are "
     "read from it, so the limits cannot contradict each other."),
    ("D3", "Caps", "AGG ≤ 65%; EEM, XLE, XLK ≤ 10% each; gold ≤ 15%; any equity fund ≤ 40%; equity ≤ 50%", "AGG 60–70%",
     "Concentration limits. Moving the AGG cap between 60% and 70% changes the mix, not the risk."),
    ("D4", "Return assumptions", "Equity risk premium 4.5%; AGG yields 0.5% over Treasuries", "3.5–5.5%; 0.3–0.9%",
     "Disclosed assumptions, not data. The verdict needs a premium of at least 4.15% (see 'What do we recommend?')."),
    ("D5", "Our crisis scenario", "'Hormuz stagflation 2027': 10-year yield +250 bp, oil +40%, VIX +25, dollar +8%, credit "
     "+150 bp over three quarters, plus one panic day on AGG", "a severe case is shown separately",
     "The one crisis in which bonds fall with stocks. The most severe version still within history."),
    ("D6", "Ownership", "The team lead owns all six analysis notebooks; four reviewers", "—", "Governance."),
    ("D7", "Dates", "Methodology frozen 29 Oct 2026; decision date 26 Oct 2026; submission 9–13 Nov", "—",
     "The 2023–2026 test was run once, after the freeze."),
    ("D8", "Risk budget per fund", "No fund may carry more than 40% of the portfolio's tail risk", "35–50%",
     "Sizes each position by how much it adds to the losses on the worst days."),
    ("D9", "Monitoring", "When the model's daily risk forecast stays above the limit for 5 days, the committee meets; no "
     "automatic trading", "—", "An automatic selling rule was tested and made losses worse in recent years."),
    ("D10", "Verdict rule", "ACCEPT if a portfolio meets the objective inside every limit; ADJUST if it would with the crisis "
     "budget at most 5 points looser; otherwise REJECT, with the sustainable spending rate as advice", "—",
     "Fixed before the final test, so the answer could not be tuned to the data."),
]

NOT_CAPTURED = [
    ("Crises unlike any in our data", "The data start in November 2004, so the 2000–02 technology crash and the 1970s "
     "inflation are not in them. The scenario and the reverse stress test reach beyond the record, but no model can price "
     "a crisis nobody has seen."),
    ("Sudden switches from calm to panic", "The risk model needs a few days to react. Six of its fourteen breaches in "
     "2019–2022 were the first days of a new crisis (COVID, the 2021 bond tantrum). That is why the fund also has a loss "
     "budget and stress tests, not only a daily risk number."),
    ("Selling in a panic", "Prices are closing prices. In a crisis a bond fund can trade below the value of its bonds "
     "(AGG: −6.8% on 10 October 2008). The scenario adds one such day; a forced seller could do worse."),
    ("Expected returns are estimates", "They are built from today's yields plus an assumed equity premium (4.5%). The "
     "verdict is ACCEPT, but it would be REJECT below a premium of 4.15%."),
    ("Taxes and costs", "Fund fees and US withholding tax on dividends (15%) are included; whether AGG's interest is "
     "exempt needs a tax adviser and changes the verdict in some cases."),
    ("Currency", "Everything is in US dollars against US inflation, but scholarships are paid in rupees. The rupee fell "
     "from about 103 to 323 per dollar since 2005, so the fund's purchasing power in Sri Lanka depends on the exchange "
     "rate as much as on the portfolio."),
    ("Only seven funds", "No cash, derivatives, leverage, private assets or ESG screens, as the mandate requires."),
    ("A limited test", "The risk model was chosen on 2019–2022, so it naturally looks good there. The 2023–2026 test is the "
     "fair one, but four years can only show the model is not badly wrong, not that it is perfect."),
]

# Every 99% VaR breach of the champion on validation (2019–2022), with its verified cause (doc/decisions/exception_log.md)
EXCEPTION_CAUSES = {
    "2019-05-13": "US–China trade war: China retaliates with tariffs",
    "2019-10-02": "Growth scare: US manufacturing at its weakest since 2009",
    "2020-01-27": "First COVID scare",
    "2020-02-24": "COVID spreads in Italy",
    "2020-02-27": "COVID sell-off",
    "2020-03-09": "COVID and the oil price war",
    "2020-03-12": "COVID: US travel ban; even bonds sold",
    "2020-06-11": "Second-wave fears and a gloomy Fed outlook",
    "2020-10-28": "COVID surge; new lockdowns in Europe",
    "2021-01-27": "Fed statement; hedge funds de-risk in the GameStop squeeze",
    "2021-02-25": "Bond tantrum: record-weak Treasury auction",
    "2021-11-10": "US inflation 6.2%, highest since 1990",
    "2022-03-07": "Russia–Ukraine: oil near $130",
    "2022-06-13": "US inflation surprise; a 0.75-point Fed hike expected",
}
