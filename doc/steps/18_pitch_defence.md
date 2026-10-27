# Step 18: Final Pitch & Q&A Defence

**Owner:** C (deck) + all (delivery) · **Week:** 4 · **Effort:** 3 days, including rehearsals · **Depends on:** 17 · **Feeds:** final judging (top 5 teams)

## 1. Target

- A **10–12 minute** pitch with a deck of 10–12 slides, delivered as if to the endowment's **investment committee**, ending in a clear verdict.
- A live app demo of at most 2 minutes, with a recorded backup.
- A rehearsed **Q&A bank** of at least 30 questions. Every member can answer questions on every step.

## 2. Why it matters

- Brief §7.5: the pitch is followed by Q&A, "in which the panel behaves as the client's investment committee".
- Brief §8.7: "Inability to explain or defend material aspects … may result in a reduction in marks or disqualification."
- Rubric: communication and defence (15%), i.e. "quality of answers under judges' questioning".

## 3. How to achieve it

### 3.1 Deck structure

Follows EDGEFORGE slide 79: what the committee should receive.

| # | Slide (title is the message) | Time | Speaker |
|---|---|---|---|
| 1 | "We recommend ADJUST/ACCEPT: [allocation] protects capital within your limits" | 0:45 | C |
| 2 | Your mandate in numbers: required return vs risk tolerance (the IPS) | 1:00 | P |
| 3 | Allocation: what we recommend and why (frontier and trade-off) | 1:15 | P |
| 4 | Why not 60/40 or max-Sharpe? (walk-forward scorecard) | 1:00 | P |
| 5 | A bad day: VaR, ES and EVT side by side, in dollars | 1:00 | R |
| 6 | The tail: EVT, how we chose the threshold, the once-in-a-decade loss | 1:00 | R |
| 7 | Can you trust these numbers? Backtest results and the traffic light | 1:00 | V |
| 8 | Crises: 2008, 2020, 2022 and our stagflation scenario | 1:15 | V |
| 9 | Where the risk comes from: risk budget and sizing | 0:45 | P |
| 9b | "Did AI behavioural simulation help? We measured it": MiroFish with vs without scorecard (/100) and the adoption outcome. Take the time from slides 3 and 8 if needed | 0:45 | V |
| 10 | Live app demo (or recording) | 1:30 | D |
| 11 | What we can't capture: limitations and governance triggers | 0:45 | C |
| 12 | Verdict and next steps (decision requested from the committee) | 0:30 | C |

Design: deck charts are exported from the same artifacts (Step 17); one message per slide; large numbers in USD; minimal text; speaker notes on every slide.

### 3.2 Q&A bank (prepare written answers; owners in brackets)

**Mandate and decision**
1. Why is this portfolio suitable for a conservative endowment? [P]
2. Your expected return is below the required return. Why should we accept it? [P]
3. Why ADJUST rather than ACCEPT? What exactly should we change? [P]
4. What horizon did you assume and why? [P]
5. Why not simply hold 60/40? [P]
6. How would you invest an extra $5M tomorrow? [P]

**Portfolio construction**
7. Why not maximise Sharpe? [P]
8. How did you estimate expected returns? Why not historical means? [P]
9. How stable are your weights? [P]
10. Why this much gold? This little EM? [P]

**Risk models**
11. Which VaR model do you trust and why? [R]
12. Why do the three VaR methods disagree at 99%? [R]
13. Is VaR the maximum we can lose? [all]
14. Why report ES in addition to VaR? [R]
15. How did you choose the EVT threshold? Would a different rule change your answer? [R]
16. What does ξ mean, in plain words? [R]
17. How confident are you in your 99.9% numbers? [R]
18. Why √10 scaling, or why not? [R]

**Validation**
19. Is your backtest really out-of-sample? [V]
20. What does failing Christoffersen mean? [V]
21. Why does the Basel traffic light only apply at 99%? [V]
22. What happens if your model turns yellow next year? [V]

**Stress**
23. What happened to your bonds in 2022, and could it happen again? [V]
24. Where did your hypothetical scenario's numbers come from? [V]
25. What would cause a 20% loss? How likely is it? [V]
26. Do correlations hold in a crisis? [R/V]

**Data, code and governance**
27. How did you clean the data? Did you remove outliers? [D]
28. How can we reproduce your results? [D]
29. Which parts did AI write, and how did you validate them? [all]
30. Walk us through the code that computes ES. [R; anyone may be asked]
31. What is your weakest assumption? [all]
32. When would you recommend we exit or reduce risk? [P]

**MiroFish / AI behavioural layer**
33. Isn't MiroFish just an LLM making things up? How did you validate it? [V]
34. Who chose the shock magnitudes: the AI or you? [R]
35. Did the LLM already "know" 2022? How does that affect your replay test? [V]
36. Is this free-tier and reproducible? [D]
37. How do you know MiroFish added value, and could you have rigged the scorecard? [V]

**Answer format:** a direct answer in one sentence, then the evidence (number or chart), then the limitation or caveat. Maximum 45 seconds.

### 3.3 Rehearsal schedule

| Day | Activity |
|---|---|
| Week 4, Day 2 | Deck v1; dry run 1 (timing only) |
| Week 4, Day 3 | Dry run 2 with a mock panel (friends or lecturers) firing 15 random Q&A-bank questions; record it |
| Week 4, Day 4 | Fix weak answers; **cross-training**: each member answers 5 questions *outside* their own step |
| Week 4, Day 5 | Dry run 3, full and timed, with the live demo; backup video ready; final deck freeze |

### 3.4 Demo protocol

- Pre-load the deployed app and a local instance; the backup video is on the desktop.
- Script: Home verdict → switch confidence 95 → 99 (the cards update) → Risk Dashboard side by side → Backtesting traffic light → Stress slider (raise the rate shock, watch the loss update) → Limitations page.
- Avoid heavy recomputations live; use precomputed paths only.

## 4. Implementation plan

| # | Task | Owner |
|---|---|---|
| 1 | Storyline agreed (slide titles = messages) | C + all |
| 2 | Charts exported from artifacts | C |
| 3 | Written Q&A answers in `doc/qa_bank.md`, each with an evidence pointer (page or chart) | each owner |
| 4 | Three rehearsals with timing and recordings | all |
| 5 | Backup demo video (2 minutes) | D |

## 5. Acceptance criteria

- Timed pitch is within 10:30–11:45 in two consecutive rehearsals.
- Every member answers 5 randomly drawn questions outside their own area acceptably (peer-scored ≥ 3/5).
- The demo runs in 2 minutes or less with no errors, and the backup video is ready.

## 6. Pitfalls

- Opening with methodology instead of the verdict. Committees want the decision first.
- Reading slides; too many formulas.
- One "quant" answering every hard question. Judges deliberately ask others (§8.7 risk).
- Defensive answers to limitation questions. Owning limitations scores marks.

## 7. Closing line (suggested)

"Our recommendation is not the portfolio with the highest expected return. It is the one whose downside we have measured, tested and can defend." This echoes the committee's own belief from the brief.
