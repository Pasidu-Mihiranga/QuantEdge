# Step 08: Value-at-Risk (Layer 2)

**Owner:** R · **Week:** 2 (Days 1–3) · **Effort:** 3 days · **Depends on:** 04, 07 · **Feeds:** 09, 10, 11, 13

## 1. Target

- At least six VaR estimators behind **one common interface**:
  - Historical simulation (HS)
  - Parametric Normal
  - Parametric Student-t
  - Cornish-Fisher
  - Monte Carlo
  - GARCH filtered historical simulation (FHS)
- Results at **90/95/99%** for 1 day (plus 10 days), in % and in USD on $10M.
- An automatic **disagreement analysis** that explains, with statistics, where and why the methods differ.

## 2. Why it matters

- Brief §8.2: "implement and compare three VaR methodologies (Historical, Parametric, Monte Carlo) … at both 95% and 99% … **discuss where the three disagree and why** … evaluate and justify the assumptions rather than applying standard techniques without critical assessment."
- Brief §6: the sidebar must choose confidence 90/95/99 and the VaR methodology.
- Rubric: technical rigour (25%).
- Risk deck slide 12 and EDGEFORGE slide 61: VaR is a loss percentile, **not a worst loss**. That wording must appear in the app.

## 3. How to achieve it

### 3.1 Common interface (`risk/base.py`)

```python
class RiskModel(Protocol):
    name: str
    def fit(self, returns: pd.DataFrame | pd.Series, weights: np.ndarray | None) -> "RiskModel": ...
    def var(self, alpha: float) -> float     # positive loss fraction, 1-day
    def es(self, alpha: float) -> float      # Step 09
    def loss_sample(self) -> np.ndarray | None  # for charts and Euler contributions
```

All models take **only** the estimation window passed in, so the same object works for static reporting and for walk-forward backtesting (Step 11).

### 3.2 Estimators (ℓ = portfolio loss fraction; q_p = p-quantile)

| Model | VaR_α | Key assumption to critique |
|---|---|---|
| **Historical simulation** | Empirical (α)-quantile of ℓ over a window W ∈ {250, 500, 1000}; `np.quantile(..., method="higher")` (conservative; documented) | The past window is representative; reacts slowly after regime shifts; small-sample quantile noise at 99% (only 5 observations beyond VaR in 500 days) |
| **Parametric Normal** | −μ_p + z_α σ_p, with σ_p = √(wᵀΣw) | Normality: thin tails, no skew, constant volatility |
| **Parametric Student-t** | −μ_p + s·t_ν⁻¹(α), with s = σ_p√((ν−2)/ν) and ν by MLE (`scipy.stats.t.fit` on standardised ℓ) | Symmetric fat tails; still unconditional |
| **Cornish-Fisher** | −μ_p + z_cf σ_p, with z_cf = z + (z²−1)S/6 + (z³−3z)K/24 − (2z³−5z)S²/36 | Moment expansion; unreliable at extreme skew or kurtosis |
| **Monte Carlo** | Simulate N = 100,000 portfolio returns from a multivariate Student-t (Ledoit-Wolf Σ scaled to t, joint ν by MLE), with a seed; empirical quantile of the simulated losses | The distribution is assumed; correlation is fixed (no crisis correlation) |
| **GARCH-FHS** | GARCH(1,1) with t innovations on 100·r_p (`arch_model(..., mean="Constant", vol="GARCH", p=1, q=1, dist="t")`); standardised residuals z; VaR = −(μ + σ_{t+1|t}·q_{1−α}(z)) | Volatility clustering is captured; parameters are estimated with error |

**Monte Carlo precision:** report the Monte Carlo standard error of the VaR from 20 batches of 5,000 simulations (or the binomial interval on order statistics), and show the convergence plot (VaR against N).

**10-day horizon:**
- For MC and FHS, simulate 10-day paths (FHS: bootstrap residuals through the GARCH recursion).
- For HS, use overlapping 10-day returns.
- √10 scaling is shown only as a labelled comparison line.

### 3.3 Disagreement analysis (`risk/diagnostics.py`)

Automatically generate a table and narrative per confidence level:

| Diagnostic | What it explains |
|---|---|
| Excess kurtosis and Jarque-Bera | Normal VaR < HS/t VaR at 99% means fat tails |
| Skewness | Cornish-Fisher versus Normal gap; asymmetric downside |
| Ljung-Box on ℓ² and ARCH-LM | Volatility clustering: FHS differs from the unconditional models and moves through time |
| Ratio HS99/N99 and HS95/N95 | Normal is often *adequate or conservative at 95% but understates at 99%*: the classic crossover |
| Window sensitivity (HS at 250/500/1000) | How much "history choice" moves the number |
| Time-series plot of all VaR models (rolling) | Unconditional models lag; FHS reacts within days in March 2020 |

The narrative template states the observed gap and links it to the diagnostic. Example: "At 99%, Normal VaR is 18% below HS because portfolio excess kurtosis is 6.2 (JB p < 0.001)." The team writes the final interpretation; it is not auto-generated prose.

## 4. Implementation plan

| # | File / function | Detail |
|---|---|---|
| 1 | `risk/base.py` | Protocol, `RiskResult` dataclass (model, alpha, horizon, var_pct, var_usd, es_pct, es_usd, se) |
| 2 | `risk/var.py::HistoricalModel, NormalModel, StudentTModel, CornishFisherModel` | |
| 3 | `risk/montecarlo.py::MonteCarloModel(n_sims, dist="t", rng)` | With a batch standard error |
| 4 | `risk/garch.py::GarchFHSModel(dist="t")` | With a warm-start option for speed in backtests |
| 5 | `risk/registry.py::MODELS = {...}` | Sidebar method selector maps here |
| 6 | `risk/diagnostics.py::disagreement_table(models, returns, alphas)` | |
| 7 | `risk/horizon.py::var_h(model, h)` | Simulation or overlapping |
| 8 | Artifacts: `risk_snapshot.parquet` (all models × α × horizon), `rolling_var.parquet` | |

## 5. Acceptance tests

- Simulated i.i.d. N(0, 1%) with 10⁶ draws: HS, Normal, t (with ν → large) and MC all within 1% of 2.326% at 99%.
- Simulated Student-t with ν = 4: the t model recovers ν within ±0.5; Normal VaR99 underestimates by the theoretical amount.
- Monte Carlo VaR converges: the standard error shrinks as 1/√N.
- GARCH on simulated GARCH(1,1) recovers α₁ + β₁ within 0.03.
- VaR is monotone in α for every model (VaR90 ≤ VaR95 ≤ VaR99).
- USD conversion: var_usd = var_pct × NAV exactly.

## 6. Pitfalls

- Saying "maximum loss" or "we will not lose more than". The correct wording is "a loss exceeded on about 1% of days under the model".
- Setting μ inconsistently: some models with μ, some without. Pick one (include the estimated μ; it is tiny for 1-day) and state it.
- A Student-t scale without the √((ν−2)/ν) correction, which inflates VaR.
- Monte Carlo without a seed, so the numbers change on every app reload.
- Averaging the methods into one number. Instead, **choose** one via backtesting (Step 11) and report the others as model-risk ranges.

## 7. Defend it in Q&A

- *"Which VaR do you trust and why?"* The one that passes Kupiec and Christoffersen out-of-sample (expected to be GARCH-FHS). The others show the range of model risk.
- *"Why do they disagree at 99% but not at 95%?"* Fat tails: the 95% quantile sits in the body, where normality is roughly fine; the 99% quantile sits in the tail, where kurtosis dominates.
- *"Is VaR the most we can lose?"* No. It is a threshold; ES (Step 09) and EVT (Step 10) answer "how bad beyond it".
