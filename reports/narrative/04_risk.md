### Definitions

VaR and ES are positive numbers meaning losses. Losses are computed on point-in-time weights, with simple returns aggregated across assets.

> VaRα = −inf { x : P(R ≤ x) ≥ 1 − α }
> ESα = 1 / (1 − α) × ∫ from α to 1 of VaRᵤ du

### Three methods, and why they disagree

We compute historical simulation, parametric (normal, Student-t, Cornish-Fisher) and Monte Carlo VaR at 95% and 99%, plus EVT and GARCH-based models, on the same recommended weights.

{{models}}

{{models_fig}}

- **At 95% the historical, parametric and Monte Carlo methods nearly agree** (USD 49,000–61,000). This part of the distribution is well observed.
- **At 99% they do not** (USD 88,000–115,000, and USD 212,000 for Cornish-Fisher). Among these methods the normal model is the highest at 95% and the lowest at 99%: tail events inflate its variance, which raises the centre, while its thin tails miss the extremes.
- **Monte Carlo** draws from a fitted Student-t and lands beside the parametric t model, because it shares the same assumption. Simulation adds no information the distribution does not already hold.
- **Volatility-aware models are lower** because they respond to today's calm market, while historical models still remember every bad day in their two-year window.
- **Cornish-Fisher is unreliable here.** Its correction is valid only for mild skew and kurtosis, and these returns are too fat-tailed. We show it for comparison and do not use it.

These figures describe a calm market. Through the cycle, on 2004–2018 data including the 2008 crisis, the average very bad day costs USD 208,000, which is the figure tested against the limit.

### Why Expected Shortfall as well

VaR says where a bad day starts and nothing about how bad it gets. It is also not subadditive, so two positions can show more VaR together than apart (Artzner et al., 1999), as a two-bond example in notebook 03 shows. ES averages the whole tail and is coherent. The committee's tail limit is therefore set on ES, with VaR kept because regulators' backtests are built on it.

### Extreme Value Theory

We fit a Generalised Pareto distribution to losses above a threshold u (peaks over threshold; Balkema and de Haan, 1974; Pickands, 1975), by maximum likelihood with n observations and Nᵤ exceedances.

> VaRₚ = u + (β / ξ) × { [ (n / Nᵤ)(1 − p) ]^(−ξ) − 1 }
> ESₚ = (VaRₚ + β − ξu) / (1 − ξ)

The threshold was not chosen arbitrarily. Six candidates were compared on parameter stability, Anderson-Darling and Kolmogorov-Smirnov fit, and exceedance counts, and three selection rules were compared. We fixed 90% on the candidate portfolio before the decision date. Repeating the evidence on the final weights shows a weakness we report rather than hide: at 87.5–92.5% the fit is rejected or borderline at 5%, while 95% fits well but gives a heavier tail (ξ of 0.41 against 0.27).

{{evt}}

The practical effect is contained. 99% VaR moves only from 1.37% to 1.44% across thresholds, but 99% ES moves from 2.23% to 2.44%, and it would be about 7% higher at the better-fitting 95% threshold. The p-values also assume independent exceedances, which volatility clustering breaks. We read the far tail as a range, not a point. The once-in-a-decade daily loss is USD 162,000 on today's volatility and up to USD 384,000 on the long history. The decision does not rest on this estimate: the ES limit uses the through-the-cycle figure, and the champion applies EVT to GARCH residuals.
