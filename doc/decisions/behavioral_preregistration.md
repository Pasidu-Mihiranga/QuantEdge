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

## Order of work (blinding)

1. The team analyst completes the questionnaire for B1–B3 and R1–R4 **without seeing any MiroFish output** (variant A), saved under `data/behavioral/analyst/`.
2. Only then are the MiroFish runs (variant B, K = 5 replicates) started.
3. Two coders independently code each MiroFish narrative; Cohen's κ is reported.
