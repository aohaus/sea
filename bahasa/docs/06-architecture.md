# 6. Architecture

## 6.1 Overview

```
 iPhone/Android (PWA: React + TS + Vite, Workbox SW, IndexedDB queue)
        │  HTTPS (Cognito JWT)                 │ presigned PUT (audio)
        ▼                                      ▼
 CloudFront ── S3 (static web, OAC)        S3 audio bucket (private, SSE-KMS, lifecycle)
        │                                      │ ObjectCreated → SQS
        ▼                                      ▼
 API Gateway HTTP API (JWT authorizer)     Lambda: speech-assess (container image)
        │                                      │  ASR vendor API  +  pronunciation engine
        ▼                                      ▼
 Lambda (Node 22, TS, one per route group) ── DynamoDB: bahasa-events (append-only)
   /events   /plan   /items   /audio/url        DynamoDB: bahasa-app (state, content, plans, profile)
   /profile  /report /export                     Secrets Manager: LLM + speech keys
        │
        ├── Anthropic Messages API (content gen, LLM grading, weekly narrative)
        └── EventBridge Scheduler (Asia/Kuala_Lumpur):
              05:00 daily  pre-plan + pre-generate
              Sun 06:00    weekly metrics + report
              Sun 03:00    retention/deletion job, monthly event export
```

IaC: **AWS CDK (TypeScript)**, one stack per environment (`dev`, `prod`).

## 6.2 Frontend

- React 18 + TypeScript (strict) + Vite, `vite-plugin-pwa` (Workbox).
- State: TanStack Query for server data; local IndexedDB (Dexie) for event
  outbox, cached session packs, TTS audio.
- Outbox: events written locally first, flushed in batches of ≤ 25 to
  `POST /events`; server is idempotent on `eventId`.
- Audio: `MediaRecorder` (webm/opus on Android, mp4/aac on iOS Safari —
  the server normalises with ffmpeg to 16 kHz mono WAV).
- UI language Japanese; Malay text always with register badge (口語/標準)
  and tap-to-hear.
- The client computes nothing authoritative; it displays `pCorrect` and
  plans provided by the server.

## 6.3 Backend

- Node 22 Lambdas, TypeScript, esbuild bundles; shared `@bahasa/core`
  package containing: zod schemas, skill model, retention model, planner
  (pure functions, unit-tested, used for replay too).
- Event ingestion is synchronous: on `response_submitted`, the server grades
  (rule grader inline; LLM grader async), appends `response_graded`, updates
  KC/memory state with optimistic locking (`version` attribute), appends
  `skill_updated`.
- `bahasa-app` table single-table layout:

| PK | SK | Item |
|----|----|------|
| `PROFILE` | `current` / `snap#<isoWeek>` | dimension roll-ups, private context |
| `KC#<kcId>` | `state` | μ, σ², evidence, durability α/β, fluency |
| `MEM#<itemKey>` | `state` | D, S, last review, due |
| `ITEM#<itemId>` | `v#<n>` | content (GSI1: `KC#<kcId>`/`level`, GSI2: `SCN#<scenarioId>`) |
| `PLAN#<date>` | `<sessionKind>` | planned session |
| `REPORT#<isoWeek>` | `weekly` | weekly report snapshot |

## 6.4 LLM usage (Anthropic Claude API, server-side only)

| Task | Mode | Notes |
|------|------|-------|
| Item generation | Message Batches (nightly, 50% cost) | Structured outputs (`output_config.format`) with the item JSON schema; zod re-validation |
| Free-response grading | Synchronous | Structured output `{score, errors[], feedback_ja}`; ω=0.7; 5% weekly audit sample shown to learner |
| Explanations (Japanese) | Pre-generated with items | Cached with item version |
| Weekly narrative | Synchronous, Sunday | Grounded on metrics JSON only; numbers inserted by template |

- Model: `claude-opus-5-5` by default for all tasks, adaptive thinking with
  explicit `effort` per route (e.g. `low` for grading, `high` for weekly
  plan). Whether a cheaper model (e.g. `claude-haiku-5-5`) is acceptable for
  grading is a cost decision for the learner, made only after an eval set
  (Phase 3) shows grading quality holds.
- Prompt caching: a frozen system prompt (style guide, register rules, KC
  taxonomy, JSON schema) placed first with `cache_control`; volatile content
  last. Verify `cache_read_input_tokens > 0`.
- Handle `stop_reason: "refusal"` and enable server-side fallbacks.
- Never send: audio, exact location, household names. Prompts receive only
  scenario IDs/descriptions from a sanitised profile view.

## 6.5 Speech stack — empirical validation first (Phase 0)

Malay support is uneven across vendors; nothing below is assumed to work
until measured.

| Capability | Candidates to test |
|------------|--------------------|
| ASR (ms-MY, incl. colloquial KL speech, code-switching with English) | Amazon Transcribe, Google Cloud Speech-to-Text, Azure Speech, Whisper large-v3 (self-hosted on Lambda/container if latency allows), Meta MMS |
| Pronunciation assessment | Azure Pronunciation Assessment (only if it supports ms-MY — to verify); self-hosted phoneme recogniser (wav2vec2 XLS-R phoneme CTC) + forced alignment + GOP scoring against espeak-ng `ms` reference phonemes with variant lexicon |
| TTS (reference & listening items) | Azure ms-MY neural voices, Google ms-MY voices, Amazon Polly (verify Malay availability) |

**Spike protocol (Phase 0):**
- Corpus: 40 prompts (read-aloud + scenario replies, standard and
  colloquial). Recordings: ≥ 100 learner utterances; ≥ 30 native
  utterances (rater or tutor) as positive control; 10 deliberately
  mispronounced learner utterances per target contrast.
- Human labels: native rater scores each learner utterance 1–5 and marks
  mispronounced words.
- Metrics per engine: WER on native colloquial and standard; keyword-hit
  rate on learner speech; pronunciation Spearman ρ vs. rater; word-level
  error detection precision/recall; p50/p95 latency; cost per assessment;
  region/data-retention terms.
- Go/no-go: ASR WER ≤ 15% on native standard speech and ≤ 25% on
  colloquial; pronunciation ρ ≥ 0.6 and word-level precision ≥ 0.7 at
  recall ≥ 0.5; p95 ≤ 5 s; ≤ US$0.01 per assessment. Below threshold ⇒
  pronunciation ships as `experimental` (shown, not used in the profile).
- Output: `docs/speech-spike-report.md` with raw results committed (audio
  itself is not committed).

## 6.6 Security

- Single Cognito user, self-sign-up disabled, passkey or TOTP MFA; API
  Gateway JWT authorizer; all routes require auth except static assets.
- Secrets in Secrets Manager, read by Lambda at cold start; never in the
  client bundle, never in git, never in logs.
- Least-privilege IAM per Lambda; S3 buckets block public access; CloudFront
  OAC; CSP with `connect-src` limited to the API origin.
- WAF rate limit on the API (single user ⇒ low threshold).

## 6.7 Observability & cost

- Structured JSON logs without payload bodies; 30-day retention.
- Custom metrics: LLM tokens and cost per route, speech seconds, planner
  latency, calibration metrics (weekly).
- AWS Budgets alert at 80% of the monthly ceiling.
