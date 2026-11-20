# 2. Learning-Event Schema

## 2.1 Principles

1. **Append-only.** Events are never updated or deleted (except by the
   retention/delete jobs in doc 7). Corrections are new events.
2. **Replayable.** Skill state = `fold(events, modelVersion)`. Any derived
   state can be dropped and rebuilt.
3. **Client-generated IDs.** `eventId` is a ULID created on the device, so
   offline retries are idempotent.
4. **Facts, not interpretations.** The client records what happened (answer,
   timings, hints). Grading and skill updates are separate server events that
   reference the raw event and carry grader/model versions.
5. **Schemas live in one shared package** (`zod`), used by PWA and Lambdas.

## 2.2 Envelope

```ts
interface EventEnvelope<T extends EventType, P> {
  eventId: string;            // ULID (time-sortable), client-generated
  schemaVersion: 1;
  type: T;
  occurredAt: string;         // ISO-8601 from device clock
  receivedAt?: string;        // set by server
  tzOffsetMin: number;        // e.g. +480 for MYT
  sessionId: string | null;   // ULID of the session
  deviceId: string;           // random per install
  appVersion: string;
  source: 'client' | 'server';
  payload: P;
}
```

## 2.3 Event types

| Type | Source | Purpose |
|------|--------|---------|
| `session_started` | client | `{ kind: 'weekday'\|'sunday'\|'diagnostic'\|'free', budgetSec, planId }` |
| `session_ended` | client | `{ reason: 'completed'\|'abandoned'\|'timeout', activeSec, itemsDone }` |
| `item_presented` | client | Item shown; carries `purpose` (see below) and planner reasons |
| `hint_used` | client | `{ itemAttemptId, level: 1\|2\|3, kind: 'first_letter'\|'gloss_ja'\|'audio_slow'\|'show_answer' }` |
| `response_submitted` | client | Raw answer + timings (ungraded facts) |
| `response_graded` | server | Grade for a response; grader + version |
| `audio_recorded` | client | Metadata for an uploaded clip |
| `audio_assessed` | server | ASR, pronunciation, fluency, linguistic results — separately |
| `feedback_viewed` | client | Dwell time on explanation |
| `visibility_changed` | client | App backgrounded/foregrounded (excludes idle time from latency) |
| `self_report` | client | Can-do statements, confidence ratings |
| `item_flagged` | client | `{ itemId, reason: 'unnatural'\|'wrong'\|'not_used_in_my_life'\|'audio_bad', note? }` |
| `profile_updated` | client | Private-context changes (scenarios, time budgets) |
| `skill_updated` | server | Before/after state per KC with cause event — audit trail for explainability |
| `plan_generated` / `plan_accepted` | server / client | Session plans and weekly plans |
| `weekly_review_generated` | server | Report snapshot ID |

### `item_presented`

```ts
{
  itemAttemptId: string;      // ULID linking presented/hint/response/grade
  itemId: string; itemVersion: number;
  format: ItemFormat;         // see 2.4
  purpose: 'learn'|'review'|'probe'|'diagnostic'|'stretch';
  kcs: { kcId: string; weight: number }[];   // Q-matrix row
  scenarioId?: string;
  register: 'colloquial'|'standard'|'both';
  predicted: { pCorrect: number; modelVersion: string };  // logged BEFORE answering → calibration
  plannerReasons: { code: string; value?: number }[];       // e.g. {code:'due', value:0.84}
}
```

Logging `predicted.pCorrect` before the answer is what makes calibration
measurable (doc 3 §3.10).

### `response_submitted`

```ts
{
  itemAttemptId: string;
  attemptNo: number;              // 1 = first try
  inputMode: 'tap'|'type'|'voice';
  answerRaw: string | string[];   // or audioId for voice
  latency: { firstInputMs: number; submitMs: number; hiddenMs: number }; // hiddenMs from visibility events
  hintsUsed: number[];            // hint levels before this submit
  wasOffline: boolean;
}
```

### `response_graded`

```ts
{
  itemAttemptId: string;
  score: 0 | 0.25 | 0.5 | 0.75 | 1;
  grader: 'exact'|'rule'|'llm'|'asr'|'self';
  graderVersion: string;
  acceptedVariant?: string;       // e.g. matched colloquial 'tak' for 'tidak'
  errors: { kcId: string; type: 'lexical'|'affix'|'word_order'|'spelling'|'register'|'particle'|'other'; detail_ja?: string }[];
  evidenceWeight: number;         // e.g. llm=0.7, self=0.3, exact=1.0
}
```

### `audio_assessed`

```ts
{
  audioId: string; itemAttemptId?: string;
  referenceText?: string;                       // for read-aloud
  asr: { engine: string; version: string; transcript: string; confidence?: number; werVsReference?: number };
  intelligibility: { score: number };           // 0..1: did target words get recognised?
  pronunciation?: {                              // absent if engine not validated
    engine: string; version: string; status: 'validated'|'experimental';
    overall: number;
    words: { word: string; score: number; phones: { expected: string; observed?: string; gop: number; ok: boolean }[] }[];
  };
  fluency: { speechRateSyllPerSec: number; pauseRatio: number; longPauses: number };
  linguistic?: { score: number; errors: { kcId: string; type: string }[] };   // only for free replies
}
```

## 2.4 Item formats

`mcq_meaning`, `mcq_form`, `cloze_typed`, `translate_ja_to_ms`,
`translate_ms_to_ja`, `listen_select`, `listen_transcribe`, `dialogue_turn`,
`read_aloud`, `speak_response`, `reorder`, `affix_build`. Each format has a
guessing floor `g` used by the model (e.g. 4-option MCQ: 0.25; typed: 0).

## 2.5 Storage

DynamoDB table `bahasa-events` (on-demand, PITR on):

| Key | Value |
|-----|-------|
| PK | `E#<yyyy-mm>` (month bucket; keeps partitions small, enables monthly export) |
| SK | `<eventId>` (ULID ⇒ chronological) |
| Write | `ConditionExpression: attribute_not_exists(SK)` ⇒ idempotent |
| Attributes | envelope fields + `payload` (Map) |

Raw audio: S3 `audio/<yyyy>/<mm>/<audioId>.webm`, referenced by ID only.
Weekly job exports the month's events as JSONL to S3 (replay + backup).

## 2.6 Versioning

- `schemaVersion` bump ⇒ new zod schema + upcaster function `vN → vN+1` used
  during replay. Old events are never rewritten.
- `modelVersion`, `graderVersion`, `plannerVersion` are semver strings stored
  on every derived event.
