# Step 05: Investment Policy Statement (Client Framing & Risk Constraints)

**Owner:** P · **Week:** 1 draft, Week 2 calibration · **Effort:** 1.5 days · **Depends on:** 03 · **Feeds:** 07, 13, 17

## 1. Target

A written **Investment Policy Statement (IPS)** for the Serendib University Endowment, in CFA format, that fixes **before any optimisation**:
- the return objective;
- risk tolerance, both ability and willingness;
- horizon, liquidity, legal, tax and unique constraints;
- a numeric **risk-limit set**, each limit with a one-paragraph justification.

The IPS is stored in `config.yaml → ips:` and rendered on the IPS page. Every later number is judged against it.

## 2. Why it matters

- Brief §3–4 ("Manager's Responsibility"):
  - determine the horizon and allocation;
  - determine the return objective;
  - **define and justify risk constraints**;
  - show suitability for a conservative investor;
  - **quantify trade-offs**;
  - state assumptions.
- Rubric: Investment decision-making is **30%**, the largest weight. The IPS is the backbone of that score.
- The IPS turns "a set of numbers" into a decision, because every metric gets a pass or fail threshold.

## 3. How to achieve it

### 3.1 Client profile (from the brief)

- Perpetual endowment that funds scholarships, research, faculty and capital projects.
- Committee beliefs: "avoiding large losses is more important than maximising gains"; downside must be "measured, tested, defensible".
- Objective: preserve and grow capital in real terms, generate income, and be resilient in stress.

### 3.2 Return objective (derived, not assumed)

```
Required nominal return ≈ spending rate + expected inflation + costs
                       ≈ 4.0%        + CPI (FRED CPIAUCSL, 10y avg YoY) + ~0.2%
```

- Compute CPI live from the data; it is roughly 2.5–3%, giving a required return of roughly 6.5–7%.
- **Key insight to present:** for a conservative profile, this required return sits high on the efficient frontier. The trade-off chart (Step 07) shows the drawdown and ES "price" of each extra 1% of expected return.
- The recommendation may legitimately be to **adjust the spending rate**, or to accept a lower real-growth target. That is a valid "adjust" verdict.

### 3.3 Risk tolerance

- **Ability: moderate.** The horizon is perpetual, but spending is ongoing (about $400k a year), so there is a liquidity need, and a deep drawdown impairs scholarships.
- **Willingness: low.** This is explicit in the brief.
- **Overall: below average.** Where ability and willingness conflict, CFA practice takes the lower.

### 3.4 Constraints

| Constraint | Specification |
|---|---|
| Horizon | Strategic 3–5 years, reviewed annually; risk measured at 1 day (backtested) and 10 days and 1 year (reported) |
| Liquidity | About 4% of NAV a year in spending; all 7 ETFs are highly liquid, so this is not binding, but a stress-time forced sale is noted |
| Legal / regulatory | Fiduciary prudence; long-only; no leverage, shorting or derivatives |
| Taxes | Tax-exempt endowment (assumption) |
| Unique | USD-denominated mandate, but the university spends in LKR, so FX is a risk outside the model (Step 14) |
| Universe | 7 ETFs only; cash only if the organisers allow it (sensitivity toggle) |

### 3.5 Risk-limit set (v1 hypotheses, calibrated in Week 2)

| Limit | v1 value | Justification approach |
|---|---|---|
| Annualised volatility | ≤ 8% | Roughly the volatility of a 35/65 equity/bond policy; consistent with low willingness |
| Max drawdown in historical stress | ≤ 20% | With a 3-year smoothed spending rule, a 20% drawdown cuts spending by roughly 7% at most; tolerable versus scholarship commitments |
| 99% 1-day ES | ≤ 1.5% NAV ($150k) | Daily tail budget; about 1/13 of the drawdown limit |
| 99% 10-day ES (reported) | ≤ 5% NAV | Committee-meeting horizon |
| Single-asset weight | ≤ 40% | Concentration |
| XLE, XLK, EEM | ≤ 10% each | Sector or EM concentration and volatility |
| Total equity (SPY+EFA+EEM+XLE+XLK) | ≤ 50% | Conservative profile |
| GLD | ≤ 20% | No income; high standalone volatility |
| AGG | ≥ 25% | Income generation and capital preservation |
| Cash (if enabled) | ≤ 10% | Liquidity buffer only |

**Calibration rule (avoid circularity):** limits come from the **client's tolerance** (spending impact, committee beliefs), not from whatever our chosen portfolio happens to achieve. In Week 2 we test the limits for feasibility against the data. If none of the portfolios can meet both the return objective and the limits, that conflict is itself the key finding, and the verdict becomes "adjust".

### 3.6 Benchmark

- **Policy benchmark:** 60/40 SPY/AGG. It is the conventional institutional reference, it is used for the Information Ratio and alpha, and it answers "what does our quant work add?"
- Also show a conservative 40/60 version as a sensitivity.

## 4. Implementation plan

| # | Task | Output |
|---|---|---|
| 1 | `config.yaml → ips:` with `spending_rate`, `cost_drag`, `limits:` (as above), `benchmark` | Configuration |
| 2 | `decision/ips.py::required_return(cpi, spending, costs)`, which computes 10-year average YoY CPI | Number shown on the IPS page |
| 3 | `decision/ips.py::IPSLimits` dataclass plus `check(metrics) -> list[LimitCheck(name, value, limit, passed, margin)]` | Used by Steps 07 and 13 |
| 4 | `decision/ips.py::constraints_for_optimizer(limits, tickers) -> bounds, linear_constraints` | Converts limits into optimiser inputs |
| 5 | IPS page text: CFA structure, plain English, each limit with its "why" | `app/pages/1_IPS.py` |
| 6 | Week 2: feasibility study across the frontier; record the final limits and the reasoning in `doc/decisions/ips_calibration.md` | Decision record |

## 5. Acceptance tests

- `check()` returns pass or fail correctly on synthetic metrics at the boundary (equal to the limit counts as a pass).
- The optimiser constraint conversion yields a feasible set: the equal-weight-like starting point satisfies the bounds, or a clear error is raised.
- Changing a limit in YAML changes the verdict in the app with no code change.

## 6. Pitfalls

- Choosing limits after seeing results so the recommended portfolio "passes". Judges probe for this.
- A return objective with no derivation.
- Ignoring the spending need (liquidity) and the LKR spending currency.
- Too many limits to explain. Keep about 10, each with a one-line rationale.

## 7. Defend it in Q&A

- *"Why a 20% drawdown limit?"* Spending-impact arithmetic (3.5), plus the committee's belief that avoiding large losses is the priority.
- *"Your portfolio doesn't reach 6.5%. Isn't that a failure?"* No. We quantified the trade-off. Reaching 6.5% costs X% more drawdown and $Y more ES, which breaches the client's tolerance. Our recommendation is to accept the mandate with a revised return expectation, or a spending-rate review (the "adjust" verdict).
- *"Why 60/40 as benchmark?"* It is the industry-standard balanced policy portfolio and the simplest alternative the committee could choose without us.
