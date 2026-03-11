# Reviewer-Oriented Error Analysis for Screening FN

## Scope

This note analyzes the four full-review runs below, with emphasis on false negatives and reviewer-specific behavior.

- `2307.05527`
- `2409.13738`
- `2511.13936`
- `2601.19926`

Data sources used for this note:

- `screening/results/<paper>_full/run01/latte_review_results.run01.json`
- `screening/results/<paper>_full/latte_fulltext_review_from_run01.json`
- `refs/<paper>/metadata/title_abstracts_metadata-annotated.jsonl`

Scoring convention used for standalone reviewer analysis:

- `4-5` -> positive
- `1-2` -> negative
- `3` -> unclear

Important caveat:

- `SeniorLead` is not directly comparable to the two junior reviewers as a standalone classifier, because in these runs it only covers a small subset of records and leaves many cases blank. Its numbers are still useful for understanding arbitration behavior.

## Executive Summary

There is reviewer-specific signal.

- `JuniorMini` is the best Stage 1 reviewer overall on recall.
- `JuniorNano` is consistently more conservative than `JuniorMini` in Stage 1.
- The biggest recall loss is not a single bad junior reviewer. It is the combination of:
  - both juniors being too strict on some reviews, and
  - `SeniorLead` / final aggregation turning many disagreement cases into `exclude`.

Across all four reviews:

- Total Stage 1 FN: `117`
- Stage 1 FN where both juniors were negative: `59`
- Stage 1 FN where at least one junior was positive or unclear, but the final Stage 1 verdict still became `exclude`: `58`

This split matters:

- `59` cases are genuine reviewer-understanding / criteria-boundary errors.
- `58` cases are aggregation or senior-override losses.

## Aggregate Reviewer Performance

### Stage 1: Title + Abstract

| Reviewer | TP | FP | TN | FN | Unclear | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `JuniorNano` | 386 | 16 | 161 | 121 | 54 | 0.960 | 0.761 |
| `JuniorMini` | 384 | 13 | 160 | 80 | 101 | 0.967 | 0.828 |
| `SeniorLead` | 60 | 1 | 6 | 58 | 613 | 0.984 | 0.508 |

Interpretation:

- `JuniorMini` has the best Stage 1 recall and slightly better precision.
- `JuniorNano` is noticeably more aggressive in excluding positives.
- `SeniorLead` has very high precision but extremely sparse coverage; its main effect is arbitration, not broad screening.

### Stage 2: Full Text

| Reviewer | TP | FP | TN | FN | Unclear | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `JuniorNano` | 411 | 11 | 1 | 24 | 10 | 0.974 | 0.945 |
| `JuniorMini` | 403 | 11 | 1 | 26 | 16 | 0.973 | 0.939 |
| `SeniorLead` | 17 | 0 | 0 | 25 | 415 | 1.000 | 0.405 |

Interpretation:

- Once a paper reaches full text, both juniors perform well.
- The main recall bottleneck is Stage 1, not Stage 2.
- A non-trivial part of Stage 2 FN is operational, especially `missing_fulltext`, not reviewer reasoning.

## Review-by-Review Analysis

### `2307.05527`

Stage 1 standalone recall:

- `JuniorNano`: `0.782`
- `JuniorMini`: `0.916`

Stage 1 final FN: `33`

Most important pattern:

- `17` cases were `JuniorNano=neg`, `JuniorMini=pos`, then final Stage 1 became `exclude`.
- `6` cases were `JuniorNano=pos`, `JuniorMini=neg`, then final Stage 1 became `exclude`.
- Only `6` cases had both juniors negative.

What this means:

- This review is not primarily a "both juniors fail" problem.
- It is mostly a disagreement-resolution problem.
- `SeniorLead` is the main recall bottleneck here: it dropped `27` gold-positive papers at Stage 1 even though at least one junior was positive or unclear.

Error mode:

- The review topic is repeatedly interpreted as "the candidate paper must directly discuss ethics".
- In practice, this makes the reviewer policy much narrower than the actual evidence-base labels.

Representative examples:

- `huang2020ai`: generative music and human-AI co-creation, excluded because it "does not examine ethical implications".
- `Suh2021AI`: included at Stage 1, then excluded at Stage 2 for the same "not explicitly ethics-focused" reason.

Bottom line:

- `2307.05527` is the clearest case where `SeniorLead` / arbitration is a bigger problem than either junior alone.

### `2409.13738`

Stage 1 standalone recall:

- `JuniorNano`: `0.850`
- `JuniorMini`: `0.889`

Stage 1 final FN: `4`

Pattern:

- `2` cases had both juniors negative.
- `2` cases had one junior positive or unclear, but final still became `exclude`.

What this means:

- No single reviewer is dramatically worse here.
- `JuniorMini` is slightly better, but the sample is small.
- The real issue is decision policy on borderline process-extraction papers.

Error mode:

- Papers are excluded because the abstract does not clearly state validation experiments.
- In several cases, that should likely become `maybe`, not immediate `exclude`.

Representative examples:

- `etikala2021extracting`: excluded for "decision model rather than process model" and lack of explicit validation in abstract.
- `honkisz2018concept`: excluded because experiments are not clearly described in the abstract.

Bottom line:

- `2409.13738` does not indicate a uniquely bad reviewer.
- It indicates an overly strict Stage 1 threshold on "experiment clearly stated".

### `2511.13936`

Stage 1 standalone recall:

- `JuniorNano`: `0.700`
- `JuniorMini`: `0.655`

Stage 1 final FN: `10`

Pattern:

- `8` cases had both juniors negative.
- Only `2` cases were disagreement cases that final arbitration dropped.

What this means:

- This review is not mainly a senior-override problem.
- It is also not mainly a `JuniorNano` vs `JuniorMini` gap.
- Both juniors are applying a definition that is too narrow.

Error mode:

- Audio modality is often implicit through task context such as `speech emotion recognition`, `customer service calls`, or known speech datasets.
- Preference learning is interpreted too literally as explicit A/B or pairwise clip comparison, while the gold labels appear to accept broader ranking / ordinal / relative-label formulations in audio tasks.

Representative examples:

- `lotfian2016retrieving`: clear preference-learning language, excluded because the abstract does not explicitly say `audio`.
- `parthasarathy2016using`: rank-based learning on the `SEMAINE` setting, excluded because it was not treated as clearly audio-centered preference learning.
- `han2020ordinal`: speech emotion recognition in calls, excluded because ordinal learning was not treated as valid preference-like learning.

Bottom line:

- `2511.13936` is a shared reviewer-definition problem, not a single-reviewer problem.

### `2601.19926`

Stage 1 standalone recall:

- `JuniorNano`: `0.749`
- `JuniorMini`: `0.785`

Stage 1 final FN: `70`

Pattern:

- `43` cases had both juniors negative.
- `27` cases had at least one junior positive or unclear, but final still became `exclude`.

What this means:

- There is a mild reviewer gap: `JuniorMini` is better than `JuniorNano`.
- But the bigger problem is mixed:
  - many sparse-metadata cases where both juniors fail, and
  - many arbitration losses on disagreement cases.

Error mode:

- A large fraction of metadata entries contain citation-like or minimal abstracts.
- If the title/abstract does not explicitly surface `Transformer`, `syntax`, or `probing`, Stage 1 often excludes.
- Some Stage 2 FN are operational rather than semantic, for example `missing_fulltext`.

Representative examples:

- `mccoy_right_2019`: abstract is effectively just citation text, so reviewers exclude because Transformer/syntax evidence is missing.
- `Tenney:etal:2019b`: correct Stage 1 include, but Stage 2 becomes `exclude (missing_fulltext)`.
- `Warstadt:etal:2020`: same pattern; not a reasoning failure.

Bottom line:

- `2601.19926` is partly a reviewer problem, but also a metadata-quality and full-text-availability problem.

## Is There One Reviewer With a Clearly Bigger Problem?

Short answer:

- `JuniorNano` is the weaker Stage 1 reviewer overall.
- But `JuniorNano` is not the whole story.
- The full recall loss is split between junior strictness and senior/aggregation strictness.

More precise answer:

1. If you compare only the two juniors, `JuniorMini` is consistently better for Stage 1 recall overall:
   - aggregate recall `0.828` vs `0.761`
   - better on `2307`, `2409`, and `2601`
   - slightly worse on `2511`, but that review is dominated by shared-definition errors anyway

2. If you ask what causes final Stage 1 false negatives, `SeniorLead` / arbitration is a major source:
   - `2307`: `27` gold-positive drops after at least one junior was positive or unclear
   - `2409`: `2`
   - `2511`: `2`
   - `2601`: `27`

3. Therefore the practical answer is:
   - there is a reviewer-quality gap (`JuniorNano` < `JuniorMini` in Stage 1),
   - but the larger system problem is how disagreement cases are resolved.

## Operational Conclusions

If the goal is to improve recall without materially hurting precision, the highest-yield changes are:

1. Make Stage 1 disagreement handling recall-oriented.
   - If one junior is positive and the other is negative, default to `maybe`, not `exclude`.
   - If one junior is unclear and the other is not strongly negative, default to `maybe`.

2. Use `JuniorMini` as the safer Stage 1 anchor.
   - Its recall is better on three of the four reviews and better in aggregate.

3. Restrict `SeniorLead` from narrowing scope based on topic paraphrase.
   - This is especially important for `2307.05527`, where the arbitration logic seems narrower than the gold evidence-base definition.

4. Add a sparse-metadata fallback.
   - For citation-like or abstract-poor records, avoid hard `exclude` in Stage 1 unless there is direct exclusion evidence.
   - This matters most for `2601.19926`.

5. Separate semantic FN from retrieval FN in reporting.
   - `missing_fulltext` should not be mixed with reviewer reasoning errors.

## Priority Order for Follow-Up

Because reviewer-specific issues do exist, the next analysis should still stay reviewer-first:

1. Fix Stage 1 arbitration rules.
2. Calibrate `JuniorNano` to behave closer to `JuniorMini` on recall-sensitive reviews.
3. Only then move to the broader taxonomy / prompt redesign pass.

If needed, the next document should quantify how many FN would be recovered by these two simple policy changes:

- `junior disagreement -> maybe`
- `sparse abstract -> maybe unless explicit exclusion evidence`
