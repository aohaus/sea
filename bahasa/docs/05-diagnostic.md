# 5. Initial Diagnostic Test Design

## 5.1 Goals

- Place the learner on every dimension with a known uncertainty in ≈ 25 min.
- Spend items where uncertainty is largest (adaptive), not on a fixed form.
- Leave untested KCs explicitly **Unknown** with wide priors — the planner's
  InfoGain term will probe them later in normal lessons.
- Collect baseline audio for speaking, under the same conditions as later
  recordings, so progress is comparable.

## 5.2 Structure (3 sittings, can be done on separate days)

| Sitting | Section | Items | Method |
|---------|---------|-------|--------|
| A (≈8 min) | Self-report can-do (Japanese) | 12 | Weak prior only |
| | Vocabulary size | 20–30 | Adaptive yes/no + verification (see 5.3) |
| B (≈9 min) | Grammar & patterns | 15–20 | CAT over grammar KCs |
| | Listening | 8–10 | Native-like TTS (validated voice), numbers/prices, colloquial reductions, 2 speeds |
| C (≈8 min) | Read-aloud | 6 sentences | Covers pronunciation KC set (§5.5) |
| | Situational speaking | 3 prompts | e.g. 「マーマックで甘さ控えめのテ・タリックを1つ注文してください」 |

## 5.3 Vocabulary size estimation

- Bank: target lexicon split into 6 frequency/relevance bands.
- Yes/no format ("知っている？") with **pseudowords** (Malay-plausible
  non-words, e.g. *kelumpang*-like forms checked against the lexicon) to
  correct for over-claiming; every 3rd "yes" is verified with a
  meaning-choice question.
- Band selection is adaptive: start at band 2, move up/down by
  verified-yes rate. Output: `θ_vocab`, band model for §3.8 of doc 3.

## 5.4 Grammar CAT

- Item pool ≈ 120 items tagged with KCs (affixes *meN-, ber-, di-, -kan, -i,
  ter-*; negation *tak/tidak/bukan*; aspect *dah/sudah, sedang, nak/akan*;
  questions *-ke/-kah, apa, berapa, bila, mana*; classifiers; particles
  *lah, kan, je*; word order; reduplication).
- Next item = argmax expected reduction in Σ σ_k² over the target KC set,
  subject to: ≤ 3 items per KC, format mix, content balance.
- Formats: MCQ form choice, cloze, affix_build (*ajar → mengajar / belajar /
  pelajar*), reorder.

## 5.5 Pronunciation coverage (read-aloud set)

Six sentences jointly covering: *r* (tap/trill) vs *l*; final *-k*
(glottal) in *tidak, budak, masak*; final consonants without epenthetic
vowels (*makan, sedap, sejuk*); *e pepet* vs *e taling* (*emak* vs *enak*,
*perempuan*); *ng/ny* (*nyanyi, bunga*); final *-a* (*apa, saya*, both
[a] and [ə] accepted). Each sentence has a reference phoneme sequence
(espeak-ng `ms` + manual correction) and accepted variants.

## 5.6 Stopping rules (per section)

Stop when any holds:
- all target KCs in the section have σ ≤ 0.6, or
- the section's item cap is reached, or
- the section's time cap is reached.

The learner can stop anytime; whatever was measured is kept, the rest stays
Unknown.

## 5.7 Output

A `diagnostic_report` (Japanese) with, per dimension: estimate band,
interval, evidence count, and an explicit "未測定" list. It seeds the first
week's plan. **No CEFR label is shown unless σ is small enough to fit within
one CEFR band** (then shown as "A2 相当（暫定）").

## 5.8 Re-diagnosis

No full re-test. Surprise probes and InfoGain-driven exploration provide
continuous assessment. A short (≈10 min) re-check of any dimension with
σ > 1.0 is offered on Sundays if it occurs.

## 5.9 Acceptance criteria

- Completing all three sittings leaves every *dimension* with σ ≤ 0.8 and
  ≥ 60% of priority KCs measured.
- Test-retest: repeating sitting B within 3 days (different items) gives
  dimension means within each other's 80% intervals.
- No KC with zero evidence is displayed as weak.
