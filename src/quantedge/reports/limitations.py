"""Assumptions & Limitations: one list shared by the app (page 8) and the report (section 8)."""

LIMITATIONS: dict[str, list[tuple[str, str, str]]] = {
    "Data": [
        ("History is representative of the future", "Models fitted on 2004–2022 may miss new regimes",
         "Stress tests, EVT and a locked out-of-sample test period"),
        ("One frozen snapshot (to 2026-10-26)", "Numbers change with new data", "Hashed manifest; refresh is explicit and logged"),
        ("ETF prices proxy the investable portfolio", "Tracking error and fees are inside the ETF prices",
         "Expense ratios are not deducted twice"),
        ("FRED keeps only 3 years of the ICE high-yield spread", "Credit stress needs long history",
         "Moody's Baa–Treasury spread (BAA10Y) used instead"),
    ],
    "Models": [
        ("Volatility is time-varying", "Unconditional models lag in crises", "GARCH-FHS and conditional EVT, backtested"),
        ("GARCH parameters are uncertain", "Recent fits sit near the persistence boundary (α + β ≈ 1), which inflates "
         "multi-day forecasts", "Disclosed; 10-day figures shown with historical and √h comparisons"),
        ("EVT rests on few extreme points", "Wide confidence intervals at 99.9%", "Profile and bootstrap intervals; two threshold rules"),
        ("Few tail observations to validate 99% VaR", "About 10 exceptions expected in 4 years; low test power",
         "Confidence intervals, power figures and 95% results"),
        ("Normal model shown as a benchmark only", "It understates fat tails", "Never used for decisions"),
        ("Exceptions still cluster in 2008–2018", "Independence is rejected on that period", "Disclosed; validation 2019–2022 used for selection"),
    ],
    "Portfolio": [
        ("Expected returns are estimates (CAPM, MRP 5%)", "Optimisers are sensitive to μ", "Ledoit-Wolf Σ, CAPM prior, bootstrap stability"),
        ("Costs approximated at 5 bps per side", "No market impact in a crisis", "Quarterly rebalancing keeps turnover low"),
        ("Fully invested (cash only as a sensitivity)", "No liquidity buffer by default", "T-bill sleeve toggle"),
    ],
    "Stress": [
        ("Historical paths may not repeat", "The next crisis may differ", "Factor-driven hypothetical and reverse stress"),
        ("Factor betas are unstable across regimes", "Scenario impacts are estimates", "Full-sample and stress-sample betas, SE bands"),
        ("The hypothetical scenario is one of many", "Shock sizes and horizon are judgement",
         "Anchored on historical extremes; horizon and credit measure to be fixed before the freeze"),
    ],
    "Decision": [
        ("Results are provisional until the methodology freeze", "Champion and ML adoption need the final test",
         "Freeze checklist in doc/decisions"),
        ("Amended limits need client approval", "The minimum relaxation is a proposal, not a decision",
         "Explicit investment-committee approval required"),
        ("USD base while spending is in LKR", "FX risk is outside the model", "Disclosed; LKR scenario as an extension"),
        ("No derivatives, margin, ESG or tax modelling", "Out of scope for the universe", "Stated in the IPS"),
    ],
}
