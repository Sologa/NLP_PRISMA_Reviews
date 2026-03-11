# GPT-5.4-Pro Handoff: Screening False Negative Analysis

## Purpose

This document is a handoff for a deeper external analysis by `gpt-5.4-pro`.

The main goal is to analyze why the current screening workflow produces too many `false negatives`, especially at the `title + abstract` stage, and to propose defensible fixes at the levels of:

- criteria design
- prompt design
- reviewer behavior
- arbitration / aggregation policy
- full-text retrieval / pipeline robustness

This handoff is intentionally redundant. It summarizes the current situation, points to the exact files that should be read, and explains what has already been established locally so that a stronger model can continue from there rather than restart from scratch.

## Problem Statement

Current end-to-end workflow:

1. Stage 1: `title + abstract` screening
2. Stage 2: only papers that survive Stage 1 receive `full text` review

Because Stage 1 `exclude` never reaches Stage 2, Stage 1 false negatives are especially costly.

The observed final results for four reviews were:

```text
2307.05527: tp=116 fp=3 tn=44 fn=55, precision=0.9748 recall=0.6784 f1=0.8000
2409.13738: tp=17 fp=7 tn=50 fn=4, precision=0.7083 recall=0.8095 f1=0.7556
2511.13936: tp=20 fp=1 tn=53 fn=10, precision=0.9524 recall=0.6667 f1=0.7843
2601.19926: tp=251 fp=0 tn=23 fn=84, precision=1.0000 recall=0.7493 f1=0.8567
```

Key first-order finding:

- Most of the problem is indeed false negatives.
- Most false negatives happen at Stage 1, before full text is ever read.

Across these four reviews:

- Total final FN = `153`
- Stage 1 FN = `117`
- Stage 2 FN = `36`

So about `76%` of the false negatives are already lost at Stage 1.

## What Has Already Been Established

Three detailed local reports were already generated and should be read first:

1. `docs/reviewer_error_analysis.md`
2. `docs/detailed_reviewer_fn_analysis.md`
3. `docs/taxonomy_root_cause_qa.md`

These reports already contain:

- reviewer-by-reviewer performance breakdown
- false negative taxonomy
- Stage 1 counterfactual policy analysis
- a deep dive on `2307.05527`
- prompt / criteria / arbitration root-cause separation
- analysis of `missing_fulltext` false negatives

You should treat those reports as the current local baseline analysis.

## Required Reading Order

To understand the problem correctly, please read in this order.

### A. Read the analysis docs first

1. `docs/reviewer_error_analysis.md`
2. `docs/detailed_reviewer_fn_analysis.md`
3. `docs/taxonomy_root_cause_qa.md`

These files explain the current diagnosis and the taxonomy used for root-cause analysis.

### B. Then inspect the actual run outputs

Use these files as the primary evidence for what the pipeline actually did:

- `screening/results/2307.05527_full/run01/latte_review_results.run01.json`
- `screening/results/2307.05527_full/latte_fulltext_review_from_run01.json`
- `screening/results/2307.05527_full/latte_fulltext_from_run01_combined_f1.json`

- `screening/results/2409.13738_full/run01/latte_review_results.run01.json`
- `screening/results/2409.13738_full/latte_fulltext_review_from_run01.json`
- `screening/results/2409.13738_full/latte_fulltext_from_run01_combined_f1.json`

- `screening/results/2511.13936_full/run01/latte_review_results.run01.json`
- `screening/results/2511.13936_full/latte_fulltext_review_from_run01.json`
- `screening/results/2511.13936_full/latte_fulltext_from_run01_combined_f1.json`

- `screening/results/2601.19926_full/run01/latte_review_results.run01.json`
- `screening/results/2601.19926_full/latte_fulltext_review_from_run01.json`
- `screening/results/2601.19926_full/latte_fulltext_from_run01_combined_f1.json`

These are the actual prediction outputs and the merged F1 summaries.

### C. Then read the criteria

These are the criteria files used in the current runs:

- `criteria_jsons/2307.05527.json`
- `criteria_jsons/2409.13738.json`
- `criteria_jsons/2511.13936.json`
- `criteria_jsons/2601.19926.json`

These matter because some of the root causes appear to come from a mismatch between:

- `topic_definition`
- `inclusion_criteria`
- what the reviewers actually operationalized

### D. Then inspect the actual runtime pipeline code

The critical files are:

- `scripts/screening/vendor/src/pipelines/topic_pipeline.py`
- `scripts/screening/vendor/resources/LatteReview/lattereview/agents/title_abstract_reviewer.py`
- `scripts/screening/vendor/resources/LatteReview/lattereview/agents/fulltext_reviewer.py`
- `scripts/screening/vendor/resources/LatteReview/lattereview/agents/basic_reviewer.py`
- `scripts/screening/vendor/resources/LatteReview/lattereview/workflows/review_workflow.py`

These files are important because the actual runtime reviewer prompt is not the same thing as the markdown prompt templates in `sr_screening_prompts/`.

### E. Finally compare against the markdown prompt templates

These files are the more explicit screening prompt templates that exist in the repo:

- `sr_screening_prompts_3stage/sr_specific/03_stage1_2_criteria_review.md`
- `sr_screening_prompts/sr_specific/05_stage2_criteria_review.md`

These files contain more explicit instructions such as:

- use `UNCLEAR`
- use `maybe`
- do not guess
- require evidence

One key question is whether the current runtime vendor prompts are too generic compared with these templates.

## Current Findings You Should Start From

The local analysis already supports the following working conclusions.

### 1. This is not only a single-reviewer problem

There is reviewer-specific signal:

- `JuniorMini` is the strongest Stage 1 reviewer overall.
- `JuniorNano` is more conservative and produces more Stage 1 FN.

But the larger issue is not just one weak reviewer. It is also:

- overly conservative Stage 1 behavior
- senior arbitration overriding recoverable cases
- criteria/prompt misalignment for some reviews

### 2. Stage 1 is the main recall bottleneck

When papers survive into full text, the junior reviewers are much better.

So the primary system problem is not "the model cannot judge full text well."
It is "too many papers never reach full text."

### 3. The runtime reviewer prompt is very generic

The runtime `TitleAbstractReviewer` prompt only says, roughly:

- review title/abstract
- use inclusion/exclusion criteria
- output 1 to 5
- include only if all inclusion criteria are met and no exclusion criteria are met

It does not clearly instruct the reviewer that:

- Stage 1 should be recall-oriented
- lack of evidence is not exclusion evidence
- `topic_definition` is not itself a hard criterion
- sparse metadata should bias toward `maybe`

### 4. `topic_definition` is being serialized into the inclusion text

In `topic_pipeline.py`, criteria are serialized into plain text for reviewers, and `topic_definition` is prepended as:

- `主題定義：...`

This likely causes reviewers to treat background topic framing as part of the hard inclusion rules.

This appears especially important for `2307.05527`.

### 5. Senior arbitration likely amplifies false negatives

In the current workflow:

- some disagreement cases are sent to `SeniorLead`
- if `SeniorLead` produces a score, the final verdict uses the senior score directly

This means that a disagreement case such as:

- junior positive
- junior negative
- senior negative

becomes a final `exclude`, even though the case might be better handled as `maybe`.

### 6. A simple Stage 1 counterfactual improves recall a lot

The local counterfactual was:

- only `exclude` at Stage 1 if both juniors are negative

Aggregate effect across the four reviews:

- current Stage 1: `tp=440 fp=17 tn=164 fn=117`
- counterfactual: `tp=498 fp=23 tn=158 fn=59`

Metrics:

- precision: `0.9628 -> 0.9559`
- recall: `0.7899 -> 0.8941`
- f1: `0.8679 -> 0.9239`

This suggests the current Stage 1 policy is too conservative.

## The Five High-Level Root-Cause Buckets

The local taxonomy condensed the false negative problem into five buckets:

1. `Topic framing was mistaken for hard criteria`
2. `Absence of positive evidence was treated as evidence for exclusion`
3. `Operational definitions were too narrow`
4. `Disagreement arbitration was too conservative`
5. `Full-text retrieval / pipeline failures`

These buckets do not all have the same root cause.

### Bucket 1

Likely root cause:

- criteria serialization + generic runtime prompt

### Bucket 2

Likely root cause:

- Stage 1 decision policy, especially how uncertainty is handled

### Bucket 3

Likely root cause:

- criteria wording / operationalization itself

### Bucket 4

Likely root cause:

- workflow / arbitration logic

### Bucket 5

Likely root cause:

- downloader / matcher / path-resolution failure

## Review-Specific Notes

### `2307.05527`

This is the clearest case of criteria/prompt misalignment.

The key issue:

- the review topic discusses `ethical implications of generative audio models`
- but the actual inclusion criteria are not identical to "paper must explicitly discuss ethics"
- nevertheless, reviewers frequently excluded papers because they did not explicitly discuss ethics

This suggests the pipeline is using topic framing too aggressively as a hard filter.

This review should be treated as the best place to inspect prompt/criteria misalignment in detail.

### `2409.13738`

This review looks more like a Stage 1 uncertainty-handling problem.

Papers were often excluded because:

- validation was not explicit in the abstract

This is more consistent with:

- abstract insufficiency wrongly mapped to `exclude`

than with a fundamentally broken criteria file.

### `2511.13936`

This review looks more like a criteria operationalization problem.

The likely issue:

- the criteria and/or reviewer policy operationalized `preference learning in audio` too narrowly

For example, papers with:

- speech emotion tasks
- ranking
- ordinal formulations
- relative labels

may have been treated as out of scope even when gold labels considered them in scope.

### `2601.19926`

This review is mixed:

- sparse metadata / citation-like abstracts
- Stage 1 over-conservative exclusion
- some `missing_fulltext` false negatives that appear retrievable in principle

This review is useful for separating:

- semantic screening failures
- retrieval / pipeline failures

## Important Note on `missing_fulltext`

Do not assume that `missing_fulltext` means the paper should naturally be excluded.

In the current results for `2601.19926`, there are `gold-positive` papers that were marked:

- `exclude (missing_fulltext)`

The locally identified gold-positive missing-fulltext keys were:

- `agarwal:etal:2025`
- `Warstadt:etal:2020`
- `jumelet:etal:2025`
- `Tenney:etal:2019b`
- `aoyama:schneider:2022`

At least several of these appear publicly accessible today via ACL Anthology / arXiv / OpenReview-style sources.

So please treat this as a likely pipeline/download resolution problem, not just an availability problem.

## Questions for GPT-5.4-Pro

Please analyze the repo and answer the following at a higher level of rigor than the local notes.

### A. Prompt and criteria interaction

1. Is the main failure in bucket 1 primarily caused by:
   - prompt wording
   - criteria serialization
   - the criteria files themselves
   - or their interaction?

2. Should `topic_definition` ever be shown to the reviewer at decision time?
   If yes, how should it be framed so it cannot be mistaken for a hard criterion?

3. Is the current runtime reviewer prompt fundamentally too generic for this task?
   If so, what are the minimum necessary instructions that must be added?

### B. Stage 1 policy

4. Is the current Stage 1 decision policy too conservative for a screening pipeline whose goal is high recall?

5. Is the counterfactual policy:
   - `exclude only when both juniors are negative`
   a good default?
   If not, what is the better policy?

6. Should `unclear` be treated as `maybe` by default in Stage 1?

### C. Criteria quality

7. Which of the four reviews have genuinely weak / under-specified criteria files?

8. For `2511.13936`, should the criteria be rewritten to explicitly include:
   - ordinal formulations
   - rank-based learning
   - implicit audio context from speech/emotion tasks

### D. Arbitration

9. Is the current use of `SeniorLead` structurally wrong for a recall-first screening task?

10. Should senior review:
   - override juniors
   - act only as a tie-break annotator
   - or convert disagreements into `maybe`

### E. Full-text retrieval

11. Which `missing_fulltext` cases are likely real retrieval failures rather than genuinely inaccessible papers?

12. What changes should be made so that retrieval failures do not silently become false negatives?

### F. Deliverables

13. Please propose a concrete redesign of:
   - criteria serialization
   - Stage 1 prompt
   - Stage 2 prompt
   - arbitration logic
   - handling of sparse metadata
   - handling of missing full text

14. Please prioritize fixes by expected recall gain versus implementation complexity.

## Expected Style of Output

Please produce:

1. A root-cause analysis that clearly separates:
   - criteria problems
   - prompt problems
   - reviewer behavior problems
   - workflow / aggregation problems
   - retrieval problems

2. A review-by-review diagnosis for:
   - `2307.05527`
   - `2409.13738`
   - `2511.13936`
   - `2601.19926`

3. A recommended implementation plan with specific file targets in this repo.

4. If possible, concrete rewritten prompt snippets or pseudo-code for the new aggregation policy.

## Final Instruction

Please do not start from generic advice. Use the existing local analysis docs and the run outputs listed above as the primary grounding material, and then challenge or refine those conclusions where needed.
