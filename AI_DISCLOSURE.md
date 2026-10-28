# AI Disclosure (brief §8.7)

**Status:** draft; the team completes the reviewer names and confirms every statement before submission.

| Item | Disclosure |
|---|---|
| AI tool(s) used | Claude (Anthropic) via Claude Code, for implementation support and for an independent audit of the code base (separate re-derivation scripts) with a second AI reviewer. An LLM (Gemini 2.5 Flash on Vertex AI) was configured for the MiroFish behavioural lab, which was removed on 2026-10-28 before any results were used; the submitted app calls no LLM. The team adds any other tool it uses. |
| Purpose | Implementing modules to the team's written specification (`doc/steps/`); test scaffolding; the Streamlit layout; drafting of documentation, the memo template and the tear-sheet generator; debugging. |
| Human validation | **In progress:** each module is to be re-derived and signed off by a named team member (`doc/ai_log.md`); sign-offs are not yet complete. Correctness is checked with closed-form, simulation-recovery, textbook and leakage tests (pytest, 195 tests as of 2026-10-28, including the slow tests); results are cross-checked with independent libraries (scipy, statsmodels, arch) and against market facts (for example SPY −54.8% in the GFC window, AGG −15.0% in the 2022 window). |
| Decisions made by the team | The IPS limits and their calibration, the champion-model rule, the stress-scenario assumptions, the verdict logic (`doc/decisions/`), and the final recommendation and its wording. The rule engine and the memo template only assemble evidence; every judgement in the memo is written by the team. |
| Material AI-generated components | Code implementations of the data pipeline, risk models, backtests, stress tests, decision engine, ML challengers and dashboard were AI-assisted. Interpretation and the recommendation are the team's. |

The running log of AI-assisted work, with reviewer and changes after review, is in [`doc/ai_log.md`](doc/ai_log.md).
