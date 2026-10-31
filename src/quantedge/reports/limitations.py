"""Assumptions & Limitations: one list shared by the app (Assumptions & Limitations) and the report (section 8).

Each entry is (assumption or limitation, what it can change, what we do about it). Updated after the freeze and the
decision-date run (2026-10-29); numbers that move with the data are stated in the app, not here.
"""

LIMITATIONS: dict[str, list[tuple[str, str, str]]] = {
    "Data": [
        ("History is representative of the future", "Models fitted on 2004–2018 and chosen on 2019–2022 may miss new "
         "regimes", "Stress tests, EVT and a one-shot test on 2023–2026"),
        ("One frozen snapshot (to 2026-10-26)", "Numbers change with new data", "Hashed manifest; refresh is explicit and logged"),
        ("ETF prices proxy the investable portfolio", "Tracking error and fees are inside the ETF prices",
         "Expense ratios are not deducted twice"),
        ("FRED keeps only 3 years of the ICE high-yield spread", "Credit stress needs long history",
         "Moody's Baa–Treasury spread (BAA10Y) used instead"),
    ],
    "Models": [
        ("Volatility is time-varying", "Unconditional models lag in crises",
         "GJR conditional EVT (the tested model) reacts to today's volatility"),
        ("GARCH parameters are uncertain", "Recent fits sit near the persistence boundary (α + β ≈ 1), which inflates "
         "multi-day forecasts", "Disclosed; 10-day figures shown with historical and √h comparisons"),
        ("EVT rests on few extreme points", "Wide confidence intervals at 99.9%", "Profile and bootstrap intervals; two threshold rules"),
        ("Few tail observations to validate 99% VaR", "About 10 exceptions expected in 4 years; low test power",
         "Confidence intervals, power figures and 95% results"),
        ("Exceptions cluster in 2008–2018", "Independence is rejected on that period; over 2008–2026 the joint test fails "
         "at 5%", "Disclosed on the Risk page; selection on 2019–2022, test on 2023–2026"),
        ("Normal and Cornish-Fisher are benchmarks only", "The first understates fat tails; the second is outside its valid "
         "range for tails this fat", "Never used for decisions; Cornish-Fisher carries a warning"),
    ],
    "Portfolio": [
        ("Expected returns are estimates (today's yields plus a 4.5% equity premium)", "The verdict turns on them",
         "18-case robustness grid and the what-if on the first page"),
        ("The bond fund's interest is assumed free of US withholding tax", "If it were taxed like dividends, the verdict "
         "would be REJECT", "A tax adviser must confirm before money is invested"),
        ("Costs approximated at 5 bps per side", "No market impact in a crisis", "Quarterly rebalancing keeps turnover low"),
        ("Fully invested (cash only as a sensitivity)", "No liquidity buffer by default", "T-bill sleeve sensitivity case"),
    ],
    "Stress": [
        ("Historical paths may not repeat", "The next crisis may differ", "Factor-driven hypothetical and reverse stress"),
        ("Factor betas are unstable across regimes", "Scenario impacts are estimates", "Stress-week betas, SE bands"),
        ("The hypothetical scenario is one of many", "Shock sizes and horizon are judgement",
         "Anchored on historical extremes; sizes, horizon and credit measure fixed before the freeze"),
        ("The scenario treats the fund as unrebalanced during the episode", "Each fund's scenario move is applied to its "
         "starting weight", "Corrected after the freeze so that fund moves are added as simple returns (0.04 points, logged)"),
        ("The bad-day risk budget does not see the stagflation scenario", "Bonds carry little bad-day risk but most of the "
         "scenario loss", "The crisis budget is checked separately, with the scenario included"),
    ],
    "Decision": [
        ("A narrow margin over the objective", "A small change in assumptions flips the verdict",
         "Shown on the first page; review every year"),
        ("The 10-year odds of meeting the objective are about even", "Spending may need to fall after bad years",
         "Spending is smoothed over 12 quarters; annual review"),
        ("USD base while spending is in LKR", "FX risk is outside the model", "Disclosed; LKR view on the innovation page"),
        ("No derivatives, margin or ESG screens", "Out of scope for the universe", "Stated in the IPS"),
    ],
}
