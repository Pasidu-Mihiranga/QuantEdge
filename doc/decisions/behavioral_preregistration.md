# Pre-registration: with vs without MiroFish (Steps 19–20)

**Recorded:** 2026-10-28, before any MiroFish run · **Status:** frozen

| Item | Value |
|---|---|
| Frozen file | `data/behavioral/scenarios.yaml` (scenarios B1–B3, blind replays R1–R4, MVS and BRS scorecard, adoption rule) |
| SHA-256 of the file | `4c04b42aa41bd71946dc6467bc942b5beaa12c79e735ba3134d5fe0f4f073dc6` |
| Git commit that froze it | `ce7eaddfe757977ba0b744bda0e06c34c672abf1` |
| MiroFish | 666ghj/MiroFish at `7657031ac01184afe2cb220f5ee3545573b5e843`, unmodified, outside the repository (AGPL-3.0) |
| LLM | gemini-2.5-flash on Vertex AI through the local proxy (hard token budget, usage log in `data/behavioral/llm_usage.jsonl`); LLM use confirmed as allowed by the organisers |

Every run directory's `manifest.json` records the SHA-256 of `scenarios.yaml`; a run whose hash differs from the one above was produced under a changed protocol and must be reported as a deviation.

## Changes from the original Step 20 text

- **Compliant toolkit (D6, adoption gate):** "free tier" is widened to "free tier, or a paid API with written organiser approval and a hard token budget", matching the Step 19 compliance table, because the team uses an organiser-approved paid Vertex API. Recorded before any run.
- **Credit factor:** the questionnaire's `credit_spread` maps to Moody's Baa − 10-year Treasury (`BAA10Y`), because FRED keeps only three years of the ICE high-yield spread.

## Runtime settings fixed at the feasibility gate (before any scored run)

The gate uses the neutral benchmark G0, which is not one of the scored scenarios. These settings were fixed while making it run; they do not change `scenarios.yaml` and apply identically to every B run.

- **Runtime:** the published image `ghcr.io/666ghj/mirofish@sha256:d236402e…` (built 2026-03-07) predates the pinned commit, so the commit's backend code, locales and `uv.lock` are mounted read-only on it (`infra/mirofish/`). MiroFish code is unchanged; ports are bound to localhost only.
- **Language:** every request sends `Accept-Language: en`, so reports and agent text are in English for the human coders.
- **Gemini thinking off** (`thinking_budget = 0`): hidden reasoning tokens counted against MiroFish's `max_tokens` and truncated its JSON replies.
- **Recommender model:** OASIS's Twitter recommender loads `Twitter/twhin-bert-base`. It is downloaded once at revision `82ac392ce81f94560c391311ee2ddd024c5ac1fc` into a host cache that is mounted into the container. The first gate attempt stalled on this download inside the container, at round 10.
- **Rounds:** 40 (the pre-registered `max_rounds`). A 10-round trial produced no agent actions, because simulated time starts at 00:00 and agents become active from 09:00.

- **End of run:** the simulation process stays alive for interviews after its last round, and MiroFish marks a run `completed` only after the process exits. The client therefore sends `close-env` once both platforms finish. Runs start with `enable_graph_memory_update` (as MiroFish's frontend does), so the report agent reads the simulated activity from the Zep graph.

## Feasibility gate result (G0, 2026-10-28)

| Run | Client | End to end | Simulation | Report | Agents | Actions | LLM tokens | Questionnaire |
|---|---|---|---|---|---|---|---|---|
| 1 | before the end-of-run fix (≈ 6 min idle until `close-env` was sent by hand); no graph memory | 927 s | 680 s | 139 s | 8 | 167 | ≈ 1.6 M | valid at the first attempt |
| 2 | final | 564 s | 320 s | 139 s | 8 | 104 | ≈ 0.43 M | valid at the first attempt |

- **Time:** passes (one run well under 45 minutes).
- **Schema:** passes (2 of 2 answers valid at the first attempt; up to 5 attempts allowed per run).
- **Open issues for the team:**
  - **Agent count:** 8 agents, one per archetype in the seed. MiroFish creates one agent per graph entity and has no setting for this, so the pre-registered 50–150 needs a seed that names more distinct actors. This should be decided before the analyst packets are answered.
  - **Language:** the pinned MiroFish code writes agent activity to the Zep graph in hard-coded Chinese templates, so the report's quoted facts are in Chinese while its narrative is in English. The agent posts (`twitter/actions.jsonl`, `reddit/actions.jsonl`) and the questionnaire answers are in English. Changing this would need a MiroFish code change.
  - **Replicate spread:** the two runs differ on 10-year rates (+ high vs 0), the US dollar, AGG direction and duration (months vs weeks). This supports K = 5.

## Order of work (blinding)

1. The team analyst completes the questionnaire for B1–B3 and R1–R4 **without seeing any MiroFish output** (variant A), saved under `data/behavioral/analyst/`.
2. Only then are the MiroFish runs (variant B, K = 5 replicates) started.
3. Two coders independently code each MiroFish narrative; Cohen's κ is reported.
