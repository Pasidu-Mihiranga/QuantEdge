# AI Disclosure (brief §8.7)

**Status:** the team confirms every statement and adds reviewer names before submission.

| Item | Disclosure |
|---|---|
| AI tool used | Claude (Anthropic) through Claude Code. |
| Purpose | Code implementation to the team's written specifications, tests, the Streamlit layout, an independent audit of the code base, analysis drafts in the notebooks, research, and drafts of the documentation, the memo, the tear sheet, the report narrative and the decision-defence document. |
| Human validation | The analysis notebooks were written separately from the production code, and the two are reconciled by automated tests: the same backtest results (final test: same breaches and losses on 957 days), the same verdict, weights and frontier. Test code checks results against hand calculations. Named team sign-off of each module is recorded in `doc/ai_log.md`. |
| Decisions made by the team | The return objective, crisis budget, caps, return assumptions, scenario, verdict rule and the final recommendation, recorded and signed in `doc/decisions/inputs_lock.md`. AI provided evidence and options. |
| Material AI-generated components | Most of the code in `src/`, `app/`, `tests/` and `scripts/`; notebook code and draft findings; the first drafts of the written documents, which the team reviews and rewrites. |

The running log of AI-assisted work, with reviewer and changes after review, is in [`doc/ai_log.md`](doc/ai_log.md).
