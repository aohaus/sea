# 3. Skill Estimation Methodology

## 3.1 Design rules

1. **Skill and confidence are separate quantities.** Every estimate is a
   posterior distribution (mean + variance) plus evidence metadata (count,
   effective weight, last observed).
2. **Missing data is not low skill.** No evidence ⇒ wide posterior around the
   prior, displayed as 「未測定」/「不確か」, never as a low bar.
3. **Old evidence loses certainty, not value.** Uncertainty grows with time
   since last observation; the mean is unchanged by time alone. (Forgetting of
   specific items is handled by the retention model, §3.5.)
4. **Deterministic and replayable.** Pure functions over the event log. The
   LLM never writes skill numbers.
5. **Measured, not assumed.** The model's own predictions are logged and
   scored (§3.10).

## 3.2 Competency taxonomy

Three levels: **dimension → competency → knowledge component (KC)**.

| Dimension | Example competencies | Example KCs |
|-----------|----------------------|-------------|
| Vocabulary | domain lexicons, frequency bands | `lex:kurang`, `lex:tapau`, `vocab.domain.food`, `vocab.band.0-500` |
| Grammar | affixation, negation, aspect, questions, classifiers, particles | `gram.affix.meN`, `gram.affix.ber`, `gram.affix.di_passive`, `gram.affix.kan_i`, `gram.neg.tak_tidak_bukan`, `gram.aspect.dah_sudah_sedang_akan`, `gram.q.ke_kah`, `gram.cls.orang_buah_ekor`, `gram.particle.lah_kan_je` |
| Listening | numbers/prices, colloquial reductions, fast speech | `listen.numbers.price`, `listen.reduction.camne_takpe`, `listen.rate.fast` |
| Speaking — intelligibility | target words recognised | `spk.intel.*` per scenario |
| Speaking — pronunciation | Malay-specific contrasts for Japanese speakers | `pron.r_tap_trill`, `pron.l_r`, `pron.final_k_glottal`, `pron.final_consonant_no_epenthesis`, `pron.e_pepet_vs_taling`, `pron.final_a_schwa` (KL variant accepted), `pron.ng_ny` |
| Speaking — fluency | rate, pauses | derived metrics, not KCs |
| Pragmatics/register | colloquial vs standard, politeness, address terms | `prag.address.abang_kakak_encik_puan`, `prag.register.colloquial` |
| Retention | durability of what was learned | derived from §3.5–3.6 |

Each item has a Q-matrix row: `kcs: [{kcId, weight}]` (weights sum to 1).
A prerequisite graph links KCs (e.g. `gram.affix.meN` before
`gram.affix.di_passive`).

## 3.3 Ability model (per KC)

Latent ability θ_k on a logit scale, posterior `N(μ_k, σ_k²)`.

**Prior.** `μ0 = parent competency mean` (hierarchical shrinkage) or 0;
`σ0 = 1.5`. Self-report can-do statements shift μ0 by at most ±0.5 and do not
reduce σ0 below 1.2.

**Observation model** (3PL-style, multi-KC):

```
η = Σ_k w_k·θ_k − b_item + δ_format
p = g_format + (1 − g_format)·σ(a·η)
```

- `b_item`: item difficulty (prior from generator tag + frequency band +
  length; see §3.9), `a`: discrimination (default 1.0), `g`: guessing floor.

**Online update** (Gaussian/logistic moment-matching, as in Glicko/TrueSkill
variants), for each KC k in the item, with observed score `y ∈ [0,1]` and
evidence weight `ω` (grader reliability × hint adjustment):

```
p'   = ∂p/∂η = (1 − g)·a·s·(1 − s),  s = σ(a·η)     (includes a and guessing floor)
I    = ω · w_k² · p'² / (p·(1−p))                      (Fisher information)
σ_k² ← 1 / (1/σ_k² + I)
μ_k  ← μ_k + σ_k² · ω · w_k · p' · (y − p) / (p·(1−p))
```

(With g = 0 this reduces to the familiar `μ += σ²·ω·a·w·(y − p)`,
`I = ω·a²·w²·p(1−p)`.)

**Only first attempts update ability.** Retries after feedback are logged
but treated as learning events (they update the retention model's "exposure",
not θ).

**Uncertainty drift** (missing ≠ low): between observations

```
σ_k²(t) = min(σ_k² + q·Δt_days, σ0²)     with q ≈ 0.002
```

## 3.4 Evidence signals and how each is used

| Signal | Use | Not used for |
|--------|-----|--------------|
| Correctness (first attempt) | θ update | — |
| Hints | Score cap: hint L1 → max 0.75, L2 → 0.5, show-answer → 0 & ω=0.5 | — |
| Response time | **Fluency/automaticity** score per KC: `z = (ln RT − E[ln RT | format, length])/s`, EWMA over *correct* responses only; `hiddenMs` subtracted, RT > 60 s discarded | Never lowers θ |
| Grader type | ω: exact/rule 1.0, asr 0.8, llm 0.7, self 0.3 | — |
| Spaced recall | Retention model §3.5 and durability §3.6 | — |
| Surprise probes | Durability §3.6, retention calibration | — |
| Audio | Separate speaking sub-dimensions §3.7 | Vocabulary/grammar θ only via the *linguistic* score of free replies |
| Self-report | Weak prior only | Never overrides observed evidence |

## 3.5 Retention model (per memory item)

Memory items = lexical items, phrases, and pattern instances. State follows
an FSRS-style model: difficulty `D`, stability `S` (days), retrievability

```
R(t) = (1 + t / (9·S))^(−1)
```

Updated on every *review-type* first attempt (correct/incorrect/hinted),
using published FSRS update rules with default parameters at first; parameters
are refit on the learner's own data once ≥ 1,000 reviews exist (Phase 6).
Target retention for scheduling: 0.90 (configurable).

## 3.6 Short-term vs. durable mastery

For each KC and memory item, two separate numbers are tracked:

- **Current performance**: θ (or recent accuracy) — can be inflated by
  massed practice.
- **Durability**: Beta posterior `Beta(α, β)` over the pass rate on
  **delayed, unannounced** retrievals: surprise probes and reviews where the
  gap since last exposure ≥ max(3 days, 0.5·S).

Statuses:

| Status | Rule |
|--------|------|
| 未測定 Unknown | < 2 weighted observations |
| 学習中 Learning | evidence exists, θ-based p̂ < 0.8 |
| 短期定着 Fragile | p̂ ≥ 0.8 but no passed delayed retrieval with gap ≥ 7 days |
| 定着 Durable | ≥ 2 passed delayed retrievals, one with gap ≥ 21 days, durability mean ≥ 0.8 and S ≥ 30 d |
| 要再確認 Regressed | Durable item failed a probe → back to Learning, flagged in weekly report |

**Cramming indicator** per KC: `in-session accuracy − delayed accuracy`; if
> 0.25 with ≥ 6 observations, the planner spreads that KC's practice wider.

## 3.7 Speaking: three independent scores

| Score | Question | Source | Updates |
|-------|----------|--------|---------|
| Intelligibility | Would a Malaysian understand it? | ASR transcript vs. target (keyword hit rate, WER) | `spk.intel.*` |
| Pronunciation | Were the sounds produced well? | Phone/word-level assessment (GOP-style or vendor) against reference phonemes; accepts KL variants (e.g. final *-a* as [ə], final *-k* as glottal stop) | `pron.*` KCs |
| Linguistic correctness | Was the Malay right? | Rule/LLM grading of transcript for free responses | grammar/vocab KCs with ω=0.7 × ASR confidence |

A good accent with wrong grammar, or correct grammar with poor
pronunciation, are both representable. If the pronunciation engine fails the
Phase 0 gate, pronunciation is stored with `status: 'experimental'` and
excluded from the profile.

## 3.8 Roll-up to dimensions

- **Vocabulary size** (target lexicon ≈ 2,500 practical lemmas, weighted by
  frequency × personal relevance):
  `E[known] = Σ_i w_i·P(known_i)`; tested items use their own posterior;
  untested items use a band model `P(known) = σ(θ_vocab − b_band)` and add
  its variance. Reported as "約 820 語（90% 区間 650–1,000）".
- **Other dimensions**: precision-weighted mean of competency posteriors,
  variance combined; reported with an interval and evidence count.
- **Retention dimension**: share of learned items predicted R ≥ 0.9 today,
  and durability rate on the last 4 weeks of probes.

## 3.9 Item difficulty with a single learner

With one learner, item difficulty and ability are not separately
identifiable. Rules:

- `b_item` starts from a prior: generator-assigned level (1–6), frequency
  band of the hardest lemma, sentence length, format.
- `b_item` is recalibrated only from first attempts **≥ 14 days apart**,
  with strong shrinkage to its template/band group mean (hierarchical,
  updated weekly in batch).
- Group-level difficulty (template × format) is learned from all items in
  the group, which is what actually generalises.

## 3.10 Calibration and model quality (acceptance tests)

- Every `item_presented` logs `pCorrect` before the answer.
- Weekly metrics: log-loss, Brier, ECE (10 bins), against baselines:
  (a) per-format running accuracy, (b) per-KC running accuracy.
- Probe calibration: predicted `R(t)` vs. observed probe outcome.
- Gate: after 300 graded first attempts, model log-loss ≤ 0.9 × baseline (a)
  and ECE ≤ 0.08. Otherwise the weekly report says so and the planner widens
  its exploration rate.
- Replay test: rebuilding the profile from the event log reproduces the
  stored profile exactly (same `modelVersion`).
