# 8. Phased Implementation Plan

Each phase ends with a demo on the learner's phone and an explicit approval
before the next phase starts. Estimates assume Claude Code doing the
implementation with the learner reviewing.

## Phase 0 — Validation spikes (no product code)

**Scope:** speech engines (doc 6 §6.5), Malay content quality, region
availability, cost model.
- Recording web page (throwaway) to capture the spike corpus.
- Scripts to run each ASR/pronunciation/TTS candidate and compute metrics.
- 50 LLM-generated items reviewed by a native speaker for naturalness and
  register correctness.

**Acceptance:**
- `speech-spike-report.md` with metrics per engine, chosen engines, and
  go/no-go for validated pronunciation.
- ≥ 85% of reviewed generated items rated natural; error categories
  feed the generation style guide.
- Region decision documented with service availability.
- Monthly cost estimate ≤ ceiling at expected usage (≈ 25 sessions, ≈ 150
  speaking clips per month).

## Phase 1 — Foundation

**Scope:** CDK stacks, Cognito single user, CloudFront/S3 PWA shell,
`POST /events` with idempotency, IndexedDB outbox, shared `@bahasa/core`
schemas, CI (typecheck, lint, unit tests), installable PWA.

**Acceptance:**
- Installs to home screen on iOS and Android; works offline for cached shell.
- 1,000 events sent with random duplicates/reorders ⇒ exactly 1,000 stored.
- No secret in the client bundle (automated grep of build output).
- `cdk diff` clean after deploy; teardown script documented.

## Phase 2 — Skill engine + diagnostic

**Scope:** KC taxonomy v1, item bank v1 (~300 seed items), skill model,
retention model, grading (exact/rule), diagnostic flow (doc 5), profile view
with uncertainty bars and 未測定 states, replay command.

**Acceptance:**
- Unit tests: posterior update math (known cases), uncertainty drift,
  "no evidence ⇒ Unknown", hint caps, latency excluded from θ.
- Simulation test: synthetic learner with known θ — engine recovers θ within
  80% interval for ≥ 80% of KCs after 200 responses.
- Replay of the event log reproduces stored state bit-for-bit.
- Diagnostic acceptance criteria in doc 5 §5.9.

## Phase 3 — Adaptive daily lessons

**Scope:** planner (doc 4), weekday and Sunday session flows, surprise
probes, durability statuses, LLM item generation (batch) + validation,
LLM grading of free responses with audit, explanations, 「なぜこの内容？」,
item flagging, offline session packs.

**Acceptance:**
- Planner is deterministic for a fixed seed; property tests: budget respected
  (±20%), review share ≤ cap, probe share ≤ 15%, new-item cap, no
  same-scenario thrice.
- 2 weeks of real use: weekday median length within ±20% of budget; ≥ 70%
  of items scenario-tagged; flagged-item rate < 5%.
- Grading eval set (≥ 100 labelled free responses, incl. colloquial
  variants): agreement with human label ≥ 90% on correct/incorrect.
- Session fully playable in airplane mode with sync on reconnect.

## Phase 4 — Speaking

**Scope:** recording UX, presigned upload, speech-assess worker, three
separate speaking scores (doc 3 §3.7), pronunciation feedback per word/phone
in Japanese (e.g. 「*tidak* の最後の k は声門閉鎖で軽く止める」), audio
retention lifecycle.

**Acceptance:**
- Phase 0 thresholds hold on 30 fresh clips (regression check).
- p95 end-to-end feedback ≤ 5 s on 4G.
- A deliberately wrong-grammar but well-pronounced reply and a correct but
  poorly-pronounced reply produce distinguishable score profiles.
- Retention job deletes expired audio (doc 7 §7.6).

## Phase 5 — Weekly review and plan updates

**Scope:** Sunday metrics job, weekly report UI (per-dimension change with
intervals, durable vs fragile, probe results, calibration status), plan
proposal + accept/edit, LLM narrative grounded on metrics JSON.

**Acceptance:**
- Report numbers match an independent recomputation from events.
- Narrative contains no numeric claim absent from the metrics JSON
  (automated check).
- Accepted edits measurably change the next week's plan composition.

## Phase 6 — Hardening and model quality

**Scope:** calibration dashboard, FSRS parameter refit (after ≥ 1,000
reviews), item difficulty recalibration batch, export/delete-everything,
cost dashboard and budget alerts, backup restore drill.

**Acceptance:**
- G1 gate (doc 1): log-loss ≤ 0.9× baseline, ECE ≤ 0.08 after 300 responses.
- G2: ≥ 80% pass rate on probes of Durable items over 4 weeks.
- Restore from PITR + JSONL export into a fresh `dev` stack succeeds.
- Monthly cost within ceiling for 2 consecutive months.

## Out of scope (until requested)

Conversation role-play with live LLM voice, handwriting, Jawi, sharing with
family members, push-notification nudging beyond a single optional daily
reminder.
