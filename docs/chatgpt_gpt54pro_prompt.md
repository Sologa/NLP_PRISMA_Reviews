Please analyze this GitHub repository in depth. The goal is to diagnose and propose fixes for excessive false negatives in the screening workflow, especially at the `title + abstract` stage.

You must start by reading this handoff file first:

- `docs/chatgpt_gpt54pro_handoff.md`

Then follow the reading order defined inside that handoff file.

The most important grounding files are:

- `docs/reviewer_error_analysis.md`
- `docs/detailed_reviewer_fn_analysis.md`
- `docs/taxonomy_root_cause_qa.md`

Then read the actual run outputs:

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

Then read the criteria files:

- `criteria_jsons/2307.05527.json`
- `criteria_jsons/2409.13738.json`
- `criteria_jsons/2511.13936.json`
- `criteria_jsons/2601.19926.json`

Then inspect the runtime pipeline and reviewer implementation:

- `scripts/screening/vendor/src/pipelines/topic_pipeline.py`
- `scripts/screening/vendor/resources/LatteReview/lattereview/agents/title_abstract_reviewer.py`
- `scripts/screening/vendor/resources/LatteReview/lattereview/agents/fulltext_reviewer.py`
- `scripts/screening/vendor/resources/LatteReview/lattereview/agents/basic_reviewer.py`
- `scripts/screening/vendor/resources/LatteReview/lattereview/workflows/review_workflow.py`

Finally, compare against the markdown prompt templates:

- `sr_screening_prompts_3stage/sr_specific/03_stage1_2_criteria_review.md`
- `sr_screening_prompts/sr_specific/05_stage2_criteria_review.md`

Your tasks:

1. Validate or challenge the existing local diagnosis.
2. Clearly separate:
   - criteria problems
   - prompt problems
   - reviewer-behavior problems
   - arbitration / aggregation problems
   - retrieval / full-text problems
3. Explain which of the five root-cause buckets are mainly due to:
   - bad criteria
   - bad prompt design
   - bad criteria serialization
   - runtime workflow policy
   - missing full-text retrieval
4. Pay special attention to:
   - why `2307.05527` appears to narrow into "paper must explicitly discuss ethics"
   - why Stage 1 seems to overuse `exclude` when evidence is insufficient
   - why `2511.13936` may have an overly narrow operational definition
   - why disagreement cases may be overruled into `exclude`
   - whether `missing_fulltext` cases are truly inaccessible or just pipeline failures
5. Propose a concrete redesign of:
   - criteria serialization
   - Stage 1 prompt
   - Stage 2 prompt
   - arbitration logic
   - sparse metadata handling
   - missing full-text handling
6. Prioritize fixes by expected recall improvement and implementation complexity.

Output requirements:

1. Start with a short executive summary.
2. Then provide a root-cause analysis by bucket.
3. Then provide a review-by-review analysis for:
   - `2307.05527`
   - `2409.13738`
   - `2511.13936`
   - `2601.19926`
4. Then provide specific implementation recommendations with file-level targets in this repo.
5. If you disagree with the local reports, say exactly where and why.

Do not give generic high-level advice. Ground every major claim in the files above.
