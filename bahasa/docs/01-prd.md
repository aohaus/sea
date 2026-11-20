# 1. Product Requirements Document

## 1.1 Problem

Generic apps teach Indonesian-flavoured or textbook Malay, ignore what the
learner already knows, and confuse "answered correctly today" with "knows it".
The learner needs practical Malaysian Malay for daily life in Kuala Lumpur,
explained in Japanese, in very short weekday sessions plus a Sunday review.

## 1.2 Vision

A personal learning agent that maintains an honest, evidence-based model of
the learner's skills and, every session, chooses the content, difficulty,
scenario and review timing with the highest expected value — and can explain
why.

## 1.3 User

Exactly one learner. Japanese native speaker living in west Kuala Lumpur
(TTDI area), family household. Private profile details (home area, household
members' roles, school/clinic/shop names, upcoming events) are stored only in
the server-side profile, never in git.

## 1.4 Goals (measurable)

| ID | Goal | Metric |
|----|------|--------|
| G1 | Honest skill model | Next-response prediction log-loss beats a per-format baseline by ≥ 10% after 300 responses; calibration error (ECE) ≤ 0.08 |
| G2 | Durable learning, not cramming | ≥ 80% pass rate on surprise probes of items the model marks "durable" |
| G3 | Fits the routine | Weekday session median length within ±20% of chosen budget; Sunday review ≤ 30 min |
| G4 | Practical relevance | ≥ 70% of items tagged to a real-life scenario from the learner's profile |
| G5 | Speaking feedback is trustworthy | Pronunciation score Spearman ρ ≥ 0.6 vs. native rater (Phase 0 gate) |
| G6 | Visible progress | Weekly report shows per-dimension change with uncertainty bands, never a bare number |

## 1.5 Non-goals

- Multi-user, sign-up, social features, leaderboards, payments.
- Streak/gamification mechanics that reward volume over learning.
- Teaching Jawi script, formal literary Malay, or Indonesian.
- Native app store distribution (PWA only).
- An LLM "deciding" skill levels — numbers come from the deterministic engine.

## 1.6 Core user journeys

**J1 Weekday quick lesson (3–10 min).** Open app → today's session already
planned (budget preset by weekday default, adjustable) → mix of due reviews,
1 target skill in 1 scenario, possibly 1 surprise probe → immediate Japanese
feedback → "なぜこの内容？" shows the planner's reasons → session closes with
a 1-line summary.

**J2 Sunday review (20–30 min).** Longer interleaved review across the week's
material + speaking practice + weekly report: per-dimension change with
confidence, durable vs. fragile items, what the model is unsure about, and the
proposed focus for next week (accept / edit).

**J3 Initial diagnostic (≈25 min, splittable into 3 sittings).** Adaptive
placement across vocabulary, grammar, listening and speaking. Areas not
tested remain "unknown" — not "low".

**J4 Speaking.** Record a read-aloud or scenario reply → three separate
results: *Was it understood?* (ASR intelligibility), *Was the Malay right?*
(linguistic correctness), *How was the pronunciation?* (phone/word-level
assessment). Each feeds a different part of the profile.

**J5 Offline.** On the LRT / poor signal: the next 1–2 session packs are
cached; responses queue locally and sync later without duplication.

## 1.7 Functional requirements

| ID | Requirement |
|----|-------------|
| F1 | Multidimensional profile: vocabulary, grammar, listening, speaking (intelligibility, pronunciation, fluency), retention; plus fine-grained knowledge components (KCs) — see doc 3 |
| F2 | Every interaction is logged as an immutable event with timing, hint use, input mode, grader and versions (doc 2) |
| F3 | Each estimate carries mean, uncertainty and evidence count/recency; UI distinguishes "unknown" from "weak" |
| F4 | Session planner uses proficiency, weak points, time budget, due reviews, personal scenarios, and prerequisites (doc 4) |
| F5 | Surprise probes (≈10% of items) test previously "learned" material after a gap, separating short-term from durable memory |
| F6 | Audio pronunciation assessment is separate from ASR transcription and from grammatical correctness |
| F7 | Weekly report + learning-plan update, numbers computed by the engine, narrative by LLM bound to those numbers |
| F8 | Each item shows register: 口語 (colloquial, e.g. *tak, nak, dah, kat*) vs. 標準 (*tidak, hendak, sudah, di*) and accepts both where appropriate |
| F9 | Learner can flag any item ("不自然", "間違い", "使わない") — flagged items are retired and the flag is evidence for content quality |
| F10 | Full export (JSON + audio) and full delete |
| F11 | Explainability: every planned item has machine-readable reasons, rendered in Japanese |

## 1.8 Content scope (initial scenarios)

Configured in the private profile; initial candidates: mamak/kopitiam
ordering (*"Teh tarik kurang manis satu."*), wet market & grocery
(*"Berapa sekilo?"*), Grab rides (*"Berhenti kat depan tu, bang."*),
condo/guardhouse & management office, clinic/pharmacy (*"Anak saya demam
sejak semalam."*), school & teacher communication, neighbours & small talk,
contractors/repairs, phone calls & WhatsApp messages, numbers/prices/time,
seasonal (Hari Raya, Deepavali, CNY greetings).

## 1.9 Non-functional requirements

| Area | Requirement |
|------|-------------|
| Performance | Next item renders < 150 ms (pre-fetched); speaking result p95 < 5 s for a ≤ 6 s clip |
| Offline | Planned sessions usable fully offline except speaking assessment (queued) |
| Security | All secrets server-side; single Cognito user, self-sign-up disabled, MFA/passkey |
| Privacy | Doc 7; raw audio auto-deleted after 90 days by default |
| Cost | ≤ US$25/month target, tracked per service |
| Reproducibility | The full skill profile can be rebuilt by replaying the event log with any model version |
| Accessibility | Mobile-first, one-hand use, large tap targets, works on iOS Safari and Android Chrome |

## 1.10 Risks

| Risk | Mitigation |
|------|------------|
| LLM-generated Malay sounds unnatural or Indonesian | Register/authenticity style guide, lexicon checks, learner flagging, native review of seed set |
| Malay speech tooling weak (esp. pronunciation) | Phase 0 empirical spike with go/no-go thresholds; fall back to intelligibility-only |
| One learner ⇒ item difficulty and ability are confounded | Fixed difficulty priors, hierarchical shrinkage, slow item recalibration (doc 3 §3.9) |
| Over-engineering for one user | Serverless, on-demand billing, phased delivery with gates |
