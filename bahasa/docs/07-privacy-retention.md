# 7. Privacy & Data Retention Design

## 7.1 Principles

- Collect only what improves learning decisions; one learner, one account.
- The learner's voice is biometric-adjacent personal data: minimise storage,
  delete raw audio by default, keep derived scores.
- Personal context (home area, household, schools, clinics) is stored only
  in the server-side profile and **never committed to git** (the repository
  may be public).
- Third parties receive the minimum: text to the LLM, audio to the selected
  speech engine only.
- Everything is exportable and deletable by the learner.
- Malaysia's PDPA and the providers' terms are respected even though this is
  personal use.

## 7.2 Data inventory and retention

| Data | Where | Retention | Notes |
|------|-------|-----------|-------|
| Learning events (text answers, timings) | DynamoDB `bahasa-events` + monthly JSONL in S3 | Indefinite while account exists (needed for replay) | Free-text answers kept; learner can purge a time range |
| Derived state (KC, memory, profile) | `bahasa-app` | Indefinite, rebuildable | |
| Raw audio | S3 `audio/` | **90 days** default (configurable 0–365); 0 = delete after assessment | Lifecycle rule + verification job |
| "Baseline" audio (diagnostic, monthly checkpoint) | S3 `audio-keep/` | Until learner deletes | Opt-in per clip, for hearing own progress |
| Audio derived features (scores, phones, transcript) | events | As events | No raw waveform |
| Private context profile | `bahasa-app` `PROFILE` | Until edited/deleted | Coarse by design: "TTDI area", not an address |
| Generated content | `bahasa-app` `ITEM#` | Indefinite | Contains no personal data (sanitised scenario descriptions only) |
| Application logs | CloudWatch | 30 days | No request bodies, no transcripts, no audio keys |
| Exports | S3 `exports/` | 7 days, presigned URL 1 h | |
| Backups | DynamoDB PITR | 35 days rolling | Deleted data disappears from PITR after 35 days |

## 7.3 Third-party data flows

| Recipient | Data sent | Not sent | Control |
|-----------|-----------|----------|---------|
| Anthropic API | Item templates, learner's typed answers, KC metrics JSON, sanitised scenario labels | Audio, location, names of family/school/clinic, device IDs | Review the account's data-retention settings; prompts built from an allow-listed profile view |
| Speech vendor (chosen in Phase 0) | Audio clip + reference text | Learner identity, profile | Choose region/no-logging options where offered; document vendor retention in the spike report |
| AWS | Everything (data controller's own infrastructure) | — | Region `ap-southeast-5` or `-1`; SSE-KMS |

## 7.4 Recording other people

The app records only the learner, only on explicit tap. It shows a reminder
not to record family members or third parties; no ambient recording, no
background listening. If a future feature uses real conversations, it must
transcribe on-device or require explicit consent and is out of scope now.

## 7.5 Learner controls

- **Export all**: JSON (events + state + content) and a ZIP of retained audio.
- **Delete audio now**: all raw audio, or by date range.
- **Delete everything**: events, state, audio, profile, exports; Cognito
  user removed; confirmation by re-authentication. PITR note shown.
- **Audio retention setting**: 0 / 30 / 90 / 365 days.

## 7.6 Acceptance criteria

- Automated test: a clip older than the retention setting is absent from S3
  within 24 h of expiry (job verifies and logs counts only).
- LLM request payloads in tests contain no field outside the allow-list
  (snapshot test on the prompt builder).
- Log scan in CI-like test: no transcript, answer text or S3 audio key in
  log output.
- Export → delete-everything → re-import (dev only) reproduces the same
  profile via replay.
