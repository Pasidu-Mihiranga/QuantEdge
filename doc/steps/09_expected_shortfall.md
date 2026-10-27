# Step 09: Expected Shortfall / CVaR (Layer 3)

**Owner:** R · **Week:** 2 (Day 3) · **Effort:** 1 day · **Depends on:** 08 · **Feeds:** 11, 13, 15

## 1. Target

- ES for **every** VaR model in Step 08, at 90/95/99% and 97.5%, for 1-day and 10-day horizons, in % and USD.
- An explicit, written **rationale for modelling ES in addition to VaR**, with an empirical demonstration.
- The ES/VaR ratio compared with the Normal benchmark ratio, used as a tail-heaviness signal.

## 2. Why it matters

- Brief §8.3: "report Expected Shortfall, giving suitable rationale for modelling CVaR in addition to VaR."
- Brief §6: the risk dashboard shows VaR, ES and EVT side by side.
- Risk deck slides 13–14: ES is coherent and subadditive; it measures tail severity; the quantile-integral definition applies.
- For a client who prioritises avoiding large losses, ES is the natural headline risk number. It also anchors the IPS ES budget (Step 05) and the Robust Mean-ES optimiser (Step 07).

## 3. How to achieve it

### 3.1 Definition

ES_α = (1/(1−α)) ∫_α^1 VaR_u du, the quantile-integral definition (Acerbi-Tasche). For continuous distributions it equals E[ℓ | ℓ ≥ VaR_α].

### 3.2 Estimators

| Model | ES_α |
|---|---|
| Historical | Mean of the worst k = ⌈(1−α)n⌉ losses (Acerbi-Tasche estimator; consistent with the quantile-integral definition when there are ties) |
| Normal | −μ + σ·φ(z_α)/(1−α) |
| Student-t | −μ + s·[g_ν(t_α)/(1−α)]·[(ν + t_α²)/(ν−1)], with t_α = t_ν⁻¹(α), g_ν the t density and s the scale (Step 08) |
| Cornish-Fisher | Modified ES (Boudt-Peterson-Croux 2008) **or** numerical integration of the CF quantile over u ∈ [α, 1); use numerical integration (simpler to defend) |
| Monte Carlo | Mean of the simulated losses ≥ VaR; batch standard error |
| GARCH-FHS | −μ + σ_{t+1}·ES_α(z), where ES of the standardised residuals is computed empirically |
| EVT | Step 10 formula |

### 3.3 Rationale (wording for the app and report)

1. **VaR is silent beyond the threshold.** Two portfolios with the same VaR can have very different losses in the worst 1% of days. ES measures that severity.
2. **Coherence.** ES is subadditive (Artzner et al. 1999), so diversification never appears to *increase* ES. VaR can violate this, which makes VaR-based risk budgets inconsistent.
3. **Regulatory practice.** The Basel Fundamental Review of the Trading Book (FRTB) replaced 99% VaR with **97.5% ES** for market-risk capital. Under Normality the two are similar (2.338σ versus 2.326σ), but ES grows faster as tails fatten.
4. **Optimisable.** ES is convex in weights (Rockafellar-Uryasev), so it can be used directly as a portfolio constraint (Step 07).
5. **Client fit.** The committee's belief that "avoiding large losses is more important" is a statement about tail severity, which is what ES measures.

### 3.4 ES/VaR ratio diagnostic

- Under Normality: ES/VaR = 1.254 at 95% and 1.146 at 99%.
- Show each model's ratio against these reference values. An empirical HS ratio above the reference is direct evidence of fat tails, which links to EVT (Step 10).

### 3.5 Demonstrate non-subadditivity of VaR (short, convincing example)

Simulate two independent defaultable-bond-like assets, each with a 4% loss probability. At 95%, each asset's own VaR is 0, while the combined portfolio's VaR is positive. ES stays subadditive. This takes a few lines of code and goes in the Methodology page and the report. It shows understanding beyond formula use.

## 4. Implementation plan

| # | Task | Detail |
|---|---|---|
| 1 | Implement `.es(alpha)` on each model class from Step 08 | Shared helper `es_from_sample(losses, alpha)` |
| 2 | `risk/es.py::normal_es, t_es, cf_es_numeric` | Closed forms |
| 3 | `risk/diagnostics.py::es_var_ratio_table` | With Normal reference values |
| 4 | `risk/examples.py::subadditivity_demo(rng)` | For the Methodology page |
| 5 | Add 97.5% ES to the snapshot artifacts | FRTB comparison |

## 5. Acceptance tests

- Normal closed form against MC with 10⁶ simulations: within 0.5%.
- t closed form against `scipy.stats.t.expect` numerical integration: within 1e-6.
- ES ≥ VaR for every model and α (property test across random windows).
- Historical ES with ties: the quantile-integral estimator matches a hand calculation on a toy sample.
- Subadditivity demo: VaR(A+B) > VaR(A) + VaR(B) and ES(A+B) ≤ ES(A) + ES(B).

## 6. Pitfalls

- Computing historical ES as the mean of losses **>** VaR on tiny samples (at 99% over 250 days, about 2 observations). Report the sample size and prefer W ≥ 500 for 99%.
- Calling ES "the expected worst-case loss". It is the *average loss on the worst (1−α) fraction of days*.
- Mixing confidence levels in the side-by-side display. The brief requires the **same** α for VaR, ES and EVT.

## 7. Defend it in Q&A

- *"Why ES if regulators used VaR for decades?"* Regulators moved to ES (FRTB, 97.5%) precisely because VaR ignores tail severity and is not subadditive. Our client's priority is severity.
- *"Your ES is much larger than your VaR. Is the portfolio unsafe?"* The ratio of X versus a Normal reference of 1.15 tells us the tail is fatter than Normal. That is why we use ES for the budget and EVT for the extremes.
