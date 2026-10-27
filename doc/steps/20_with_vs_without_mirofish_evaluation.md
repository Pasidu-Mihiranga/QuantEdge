# Step 20: With vs Without MiroFish (A/B Evaluation, Scored out of 100)

**Owner:** V (lead), P (baseline designer), C (blind review logistics) · **Week:** 3 Days 4–5 (scoring); scorecard frozen in Week 2 · **Effort:** 2 days · **Depends on:** 12, 19 · **Feeds:** 13 (which scenario becomes the official hypothetical), 15, 17, 18

## 1. Target

A pre-registered, reproducible evaluation that answers one question with a number: **"Does adding MiroFish make our stress testing and investment decision better?"**

- **Variant A (without MiroFish):** the team designs the hypothetical scenarios by completing the Step 19 questionnaire themselves, translated by the same machinery.
- **Variant B (with MiroFish):** the questionnaire answers come from MiroFish simulations, human-validated, translated by the same machinery.
- Two scores, each **out of 100**:
  1. **MiroFish Value Score (MVS)**: an objective, metric-based score of scenario quality (primary).
  2. **Blind Rubric Score (BRS)**: reviewers blind-score both versions of the stress section and memo using the **official competition rubric weights** (secondary; approximates what judges will think).
- A pre-declared **adoption rule** decides whether MiroFish's scenario becomes our official "team-designed hypothetical scenario" or stays an exploratory appendix.

## 2. Why it matters

- The innovation criterion rewards "**well-justified** extensions". Showing quantitatively whether the AI layer adds value is itself strong evidence of rigour and honesty.
- It guards against the main risk of AI features: looking impressive while being statistically empty.
- Brief §8.7: AI output must be "independently evaluated and substantiated". This step is that evaluation.

## 3. How to achieve it

### 3.1 Fair-comparison design

| Control | How |
|---|---|
| Same inputs | Both variants use the same triggers (B1–B3, R1–R4), the same seed facts and the same as-of dates |
| Same machinery | Both go through the identical `translate.py` → stress engine → decision engine |
| Only one difference | Who answers the questionnaire: a team analyst (A) or MiroFish plus human coding (B) |
| Blinding | The A analyst completes the questionnaires **before** seeing any MiroFish output. BRS reviewers see versions labelled "X" and "Y" (random assignment, key held by C) |
| Pre-registration | Weights, metrics, thresholds and the adoption rule are frozen in `data/behavioral/scenarios.yaml`; its SHA-256 and git commit are recorded **before** the first MiroFish run |
| Uncertainty | B has K = 5 replicates and A is deterministic. The MVS for B is reported as mean ± 95% bootstrap CI across replicates |
| Naive floor | A third reference, **Variant N**: the average of the three historical crisis shock vectors, scaled. It shows whether either variant beats a trivial design |

### 3.2 MiroFish Value Score (MVS), 100 points, computed identically for A, B and N

| Dim | Name | Pts | Metric (computed automatically unless noted) |
|---|---|---|---|
| D1 | **Historical fidelity** (blind replays R1–R4) | 20 | For each replay: sign hit rate h (fraction of the 7 ETFs with the correct direction), Spearman ρ between scenario and realised window returns, and portfolio-loss error e = \|L_scn − L_real\| / \|L_real\| (recommended weights). Score = 20 × mean over replays of [0.35·h + 0.35·max(ρ, 0) + 0.30·max(0, 1 − e)] |
| D2 | **Tail informativeness** | 15 | (a) Severity ratio s = min(1, L_scn / L_ref), with L_ref = the larger of the worst historical stress loss and the EVT 1-in-10-year h-day loss. (b) Novelty: Mahalanobis distance (stressed Σ) from the nearest historical crisis vector, with full credit inside the "novel but plausible" band [2, 4]. Score = 15 × (0.5·s + 0.5·novelty) |
| D3 | **Plausibility and economic consistency** | 15 | (a) d² of the ETF shock vector under stressed Σ: full credit if the χ²₇ percentile ≤ 99.9%, falling linearly to 0 at 99.999%. (b) Fraction passing economic rules: rates↑ ⇒ AGG within ±50% of −D·Δy; equity panic ⇒ EEM ≤ SPY; oil↑ ⇒ XLE ≥ SPY; flight-to-safety targets ≥ 0; LLM-stated asset directions agree with the translated signs. Score = 15 × (0.5·a + 0.5·b) |
| D4 | **Decision usefulness** | 20 | (a) Discrimination: range of losses across the 7 candidates ÷ the mean loss, capped at 1. (b) Actionability: 1 if the scenario changes the candidate ranking, a check in Step 13, or a sizing recommendation that survives re-optimisation; otherwise 0. (c) **Human:** 3 reviewers (≥ 1 external, e.g. a lecturer) rate "helps the committee decide" from 1 to 5, normalised. Score = 20 × (0.35·a + 0.25·b + 0.40·c) |
| D5 | **Reproducibility and stability** | 15 | (a) Coefficient of variation of the portfolio loss across replicates, CV_L: score max(0, 1 − CV_L/0.5) (A and N are deterministic, so 1). (b) Inter-rater agreement for the coding (Cohen's κ, mapped κ ≤ 0.2 → 0 to κ ≥ 0.8 → 1; A uses two analysts' independent answers). (c) The cache rebuilds the page bit-for-bit (1/0). Score = 15 × (0.4·a + 0.3·b + 0.3·c) |
| D6 | **Cost, compliance and transparency** | 15 | Checklist: free-tier compliant (5), seed uses approved data only (3), runtime within budget (2), full provenance from signal to number for every shock (3), AI disclosure complete (2) |
| | **Total** | **100** | |

**D1 contamination caveat (disclosed):** the LLM, and the team analyst, may remember these episodes. The replays are anonymised, and both variants are equally exposed. Episodes such as the 2013 taper tantrum, August 2015 and Q4 2018 are less memorable than 2008 or 2020. Report D1 both with and without R4 (2022) as a sensitivity check.

### 3.3 Blind Rubric Score (BRS), 100 points, using the official weights

- Prepare two blinded packets, X and Y, each containing that variant's version of the **stress-testing page screenshots, the hypothetical-scenario write-up and the one-page memo**.
- 3 to 5 reviewers (team members not involved in that variant, plus at least one external reviewer) score each packet on the official criteria:

| Criterion | Weight | Reviewer question |
|---|---|---|
| Investment decision-making | 30 | Does this lead to a sound, actionable, client-appropriate recommendation? |
| Technical rigour | 25 | Are the scenario construction and loss calculations correct and justified? |
| Software and interface | 15 | Is it clear and usable for a non-technical committee? |
| Innovation and ambition | 15 | Is the extension well justified and valuable? |
| Communication and defence | 15 | Is it clear? Would it survive committee questioning? |

- Each criterion is rated 0–10 and weighted to /100. Report the mean ± SD across reviewers and the inter-rater agreement (Kendall's W).

### 3.4 Adoption rule (pre-registered)

1. **Compliance gate:** if B scores 0 on any D6 compliance item (free tier, approved data), then **B is rejected**, whatever its score.
2. **Adopt B as the official hypothetical scenario** if MVS_B − MVS_A ≥ **5 points** **and** the 95% bootstrap CI of the difference excludes 0 **and** BRS_B ≥ BRS_A.
3. **Hybrid** if the difference is between 0 and 5, or the CI includes 0. A stays official; B is shown as a complementary exploratory scenario in the Behavioural Stress Lab.
4. **Exploratory appendix only** if MVS_B < MVS_A. Report the negative result honestly ("AI behavioural simulation did not add value over analyst design on our metrics because …").
5. Both variants must beat Variant N. If neither does, say so: that is a finding about hypothetical-scenario design in general.

### 3.5 Outputs

- `data/behavioral/summary/scorecard.parquet`: per variant and dimension, sub-metrics, points, and the CI for B.
- App section **"With vs Without MiroFish"** (on page 10, or a tab of Stress Testing):
  - a stacked bar of D1–D6 for A, B and N, with the total out of 100 and error bars for B;
  - a radar chart of the six dimensions;
  - the BRS table;
  - the adoption-rule outcome badge (**ADOPTED / HYBRID / APPENDIX / REJECTED**) and a one-paragraph team interpretation.
- A report section (about 1 page) and one pitch slide (Step 18).

## 4. Implementation plan

| # | Task | File | Owner | When |
|---|---|---|---|---|
| 1 | Freeze the scorecard in `scenarios.yaml` (weights, bands, thresholds, adoption rule); record hash and commit | config | V | **W2 D5, before any run** |
| 2 | Variant A questionnaires completed blind by analyst 1, with an independent duplicate by analyst 2 (for D5b) | cache | P (+1) | W3 D1 |
| 3 | Variant N constructed from historical crisis vectors | `behavioral/baselines.py` | V | W3 D1 |
| 4 | `behavioral/evaluate.py`: D1–D3, D4a–b, D5 and D6 metrics, plus bootstrap over replicates | src | V | W3 D3–D4 |
| 5 | Reviewer packets X/Y built automatically (screenshots plus memo PDF); randomisation key kept by C | `reports/blind_review/` | C | W3 D4 |
| 6 | Reviewer scoring form (Google Form or CSV), for D4c and BRS | | C | W3 D4–D5 |
| 7 | Final scorecard, adoption decision, team interpretation | `doc/decisions/mirofish_adoption.md` | V + all | W3 D5 |
| 8 | App section, report section, pitch slide | app, report, deck | C | W4 |

## 5. Acceptance tests

- Unit tests for each metric on synthetic inputs:
  - a perfect replay gives D1 = 20;
  - an identical-to-history shock gives novelty 0;
  - an implausible shock (d² at the 99.9999th percentile) gives D3a = 0;
  - deterministic input gives D5a = 1.
- The scorecard total equals the sum of the dimensions, and each dimension lies within [0, its maximum].
- The pre-registration hash in the final report matches the committed `scenarios.yaml` from before the first run (check the git log).
- Re-running `evaluate.py` from the cache reproduces the scorecard exactly.

## 6. Pitfalls

- Tuning weights after seeing the results. This invalidates the comparison; the pre-registration hash prevents it.
- Letting the A analyst see MiroFish output first.
- Comparing B's best replicate with A. Always use the mean and CI across replicates.
- Reviewers who know which packet is MiroFish. Strip all MiroFish branding from the packets.
- Treating a higher MVS as "MiroFish predicts markets". It only means "better scenario design on these criteria".

## 7. Defend it in Q&A

- *"How do you know MiroFish helped?"* We pre-registered a 100-point scorecard and a blind review using your rubric weights. B scored X ± CI against A's Y (Δ = Z), so by our rule it was adopted / kept as hybrid / kept as an appendix.
- *"Couldn't you have tuned the scorecard to favour your AI feature?"* The weights were frozen and hashed before the first run; the commit is in the repository history.
- *"What if MiroFish lost?"* Then we report that. A negative, well-measured result is still evidence-based decision-making, which is exactly the committee's philosophy.
