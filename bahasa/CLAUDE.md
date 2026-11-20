# CLAUDE.md — bahasa (adaptive Malaysian Malay learning PWA)

This directory is a single-user, AI-native Malay learning app. The rest of the
`sea` repository (haze, basic, signals, scripts) is unrelated — do not modify
it when working here.

## Status

**Planning phase. Do not write application code until the learner approves
the plan.** The plan lives in `docs/` (start at `docs/README.md`). When the
plan and the code disagree, the plan wins until the plan is updated; update
the relevant doc in the same change as any design deviation.

Current phase: **0 — awaiting approval** (see `docs/08-implementation-plan.md`).

## Product in one paragraph

One learner (Japanese native, living in west Kuala Lumpur) learning practical
Malaysian Malay for daily life. Short weekday lessons, longer Sunday review.
The engine keeps a multidimensional, uncertainty-aware skill profile from an
append-only event log and plans each session (content, difficulty, scenario,
review timing). Explanations in Japanese; examples in authentic Malaysian
Malay, labelled colloquial (口語) or standard (標準).

## Non-negotiable rules

1. **Missing data ≠ low skill.** Every estimate has mean + uncertainty +
   evidence. No evidence ⇒ "Unknown", never a low score. Time without
   evidence increases uncertainty, not decreases the mean.
2. **The LLM never computes skill numbers or chooses what to study.** Skill
   model and planner are deterministic, versioned, pure TypeScript functions
   in `packages/core`. The LLM generates content, grades free text (as
   lower-weight evidence) and writes narratives bound to computed JSON.
3. **Events are append-only and the profile is replayable.** Never mutate or
   delete events except via the retention/delete jobs. Any change to model
   logic bumps `modelVersion`; replay must reproduce stored state.
4. **Speaking has three separate scores**: intelligibility (ASR),
   pronunciation (phone/word-level), linguistic correctness. Never merge
   them. Pronunciation from an unvalidated engine is `experimental` and
   excluded from the profile.
5. **Validate speech capabilities empirically.** Do not assume a vendor
   supports Malay (ms-MY) for a feature; check the Phase 0 spike report.
6. **Secrets are server-side only** (Secrets Manager). Nothing secret in the
   PWA bundle, git, logs or test fixtures.
7. **Privacy:** this repository may be public. Never commit personal context
   (exact neighbourhood, family members, school/clinic names, recordings,
   real event logs). Personal context lives only in the server-side profile.
   LLM prompts use the allow-listed sanitised profile view; audio never goes
   to the LLM. Logs never contain answers, transcripts or audio keys.
8. **Malay authenticity:** Malaysian, not Indonesian, forms. Give both
   registers where they differ (*tak/tidak, nak/hendak, dah/sudah, kat/di,
   je/sahaja*) and accept both in grading unless the item targets register.

## Stack (planned)

- PWA: React 18 + TypeScript (strict) + Vite + vite-plugin-pwa, TanStack
  Query, Dexie (IndexedDB outbox and session packs).
- Backend: AWS Lambda (Node 22, TS, esbuild), API Gateway HTTP API with
  Cognito JWT authorizer, DynamoDB (`bahasa-events`, `bahasa-app`), S3 +
  CloudFront, SQS, EventBridge Scheduler (Asia/Kuala_Lumpur), Secrets
  Manager. IaC: AWS CDK (TypeScript).
- LLM: Anthropic Claude API via the official `@anthropic-ai/sdk`, model
  `claude-opus-5-5` unless the learner decides otherwise; structured outputs
  for all machine-read responses; prompt caching on the frozen system prompt;
  Message Batches for nightly generation; handle `refusal` stop reason.
- Speech: chosen in Phase 0 (see `docs/speech-spike-report.md` once written).

## Planned layout

```
bahasa/
  CLAUDE.md
  docs/                 plan documents (01–08), spike reports
  packages/core/        zod schemas, skill model, retention, planner (pure, no I/O)
  apps/web/             PWA
  services/api/         Lambda handlers (thin; call core)
  services/speech/      speech-assess worker (container image)
  infra/                CDK app
  tools/                replay, simulation, eval scripts
```

## Conventions

- TypeScript strict, no `any`; zod schemas are the single source of truth
  for events, items and API contracts.
- Tests: Vitest. Core math needs unit tests with hand-computed cases plus a
  synthetic-learner simulation test. Planner needs property tests.
- Every derived record stores the producing version (`modelVersion`,
  `plannerVersion`, `graderVersion`).
- UI strings in Japanese; code, identifiers, comments and commit messages in
  English.
- Keep Lambdas thin; business logic lives in `packages/core`.
- Prefer small, phase-scoped PRs; each PR states which acceptance criteria it
  satisfies.

## Commands

To be defined in Phase 1 (`pnpm` workspaces expected: `pnpm test`,
`pnpm typecheck`, `pnpm lint`, `pnpm --filter infra cdk diff`). Update this
section when they exist.

## Definition of done (any change)

Typecheck, lint and tests pass; acceptance criteria for the phase item are
demonstrated; relevant doc in `docs/` updated; no personal data or secrets in
the diff.
