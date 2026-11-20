# Bahasa — Adaptive Malaysian Malay Learning Agent (Plan)

Status: **PLAN ONLY — awaiting approval. No application code exists yet.**

A single-user, mobile-first PWA that continuously estimates the learner's real
Malay ability and decides *what* to study, *how hard*, *in which everyday
scenario*, and *when to review*. Explanations are in Japanese; examples are
authentic Malaysian Malay (colloquial KL speech and standard Bahasa Melayu,
always labelled by register).

| # | Document | Contents |
|---|----------|----------|
| 1 | [PRD](01-prd.md) | Goals, non-goals, user journeys, functional & non-functional requirements, success metrics |
| 2 | [Learning-event schema](02-learning-event-schema.md) | Append-only event log, payloads, storage keys, versioning |
| 3 | [Skill estimation](03-skill-estimation.md) | Competency taxonomy, Bayesian ability model, retention model, confidence vs. skill, durability, speaking scores, calibration |
| 4 | [Adaptive lesson selection](04-lesson-selection.md) | Session planner, utility function, difficulty targeting, surprise probes, weekly plan updates |
| 5 | [Initial diagnostic](05-diagnostic.md) | Adaptive placement test, item bank, stopping rules |
| 6 | [Architecture](06-architecture.md) | PWA, AWS serverless, LLM and speech integration, speech validation spike |
| 7 | [Privacy & data retention](07-privacy-retention.md) | Data inventory, retention table, third-party flows, deletion/export |
| 8 | [Implementation plan](08-implementation-plan.md) | Phases 0–6 with acceptance criteria |

Project instructions for Claude Code: [`../CLAUDE.md`](../CLAUDE.md).

## Decisions needed before Phase 0

1. **Repository visibility.** `aohaus/sea` is public and serves GitHub Pages.
   The plan keeps personal context (exact neighbourhood, household details)
   out of git and in a server-side private profile. Should the app live here
   under `bahasa/`, or in a new **private** repository? (Recommendation:
   private repo; the docs here can move with it.)
2. **Speech vendor accounts** you are willing to use for the Phase 0 spike
   (AWS, Google Cloud, Azure). Each needs an API credential and network
   access from the build environment.
3. **A native-speaker rater** (tutor, colleague) for ~2 hours to rate
   pronunciation recordings. Without human ratings, pronunciation scores
   cannot be validated and will ship as "experimental".
4. **Monthly cost ceiling.** Proposed: ≤ US$25/month all-in.
5. **AWS region.** `ap-southeast-5` (Malaysia) if every required service is
   available there, else `ap-southeast-1` (Singapore). Verified in Phase 0.
6. **Your own starting estimate** (e.g. "survival phrases, can order food")
   — used only as a weak prior.
