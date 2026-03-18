# Current-State Recap

- Current runtime prompt source remains `scripts/screening/runtime_prompts/runtime_prompts.json`.
- Current production criteria remain stage-specific:
  - Stage 1: `criteria_stage1/<paper_id>.json`
  - Stage 2: `criteria_stage2/<paper_id>.json`
- Current metrics authority remains unchanged:
  - `2409.13738`: Stage 1 F1 `0.7500`, Combined F1 `0.7843`
  - `2511.13936`: Stage 1 F1 `0.8657`, Combined F1 `0.8814`
- The four QA JSON files in this bundle are experiment-only assets derived from the 2026-03-18 seed bundle. They are not criteria and do not replace production inputs.

# Seed QA Readiness Assessment

- `2409.13738 stage1`: `use_as_is`
  Reason: `T1-T5` already cover core fit, source/target linkage, non-target families, and secondary-study signal at title/abstract level.
- `2409.13738 stage2`: `use_as_is`
  Reason: `F1-F5` already cover primary research, canonical fit, concrete method, empirical validation, and non-target-family resolution.
- `2511.13936 stage1`: `patch_required`
  Reason: seed `M1` is a reviewer instruction about metadata handling, not an answerable evidence question.
  Minimal patch: remove answerable `M1`; preserve the instruction in `reviewer_guardrails[0]`.
- `2511.13936 stage2`: `patch_required`
  Reason: seed `M1` again audits reviewer behavior rather than extracting paper evidence.
  Minimal patch: remove answerable `M1`; preserve the instruction in `reviewer_guardrails[0]`.
- Patch notes are recorded in `patches/seed_qa_patch_notes.yaml`.
- No other seed questions were changed in v0.

# Draft Experiment Framing

- Treat the seed QA assets as the evidence interface, not as rewritten criteria.
- Run two experiment arms only:
  - `QA-only`: junior reviewers answer structured QA, evaluator maps QA to criteria, and `SeniorLead` adjudicates `stage_score = 3`.
  - `QA+synthesis`: junior reviewers answer structured QA, synthesis normalizes evidence into canonical fields, evaluator maps those fields to criteria, and `SeniorLead` adjudicates mixed cases.
- Preserve the current production routing contract:
  - Stage 1 junior outputs are reduced to a 1-5 `stage_score` plus a verdict recommendation.
  - Double `>= 4` includes, double `<= 2` excludes, all other cases go to `SeniorLead`.
- Keep all prompt bodies externalized in `templates/`.

# Self-Critique

- `QA-only` may still leave drift at the evaluator layer because raw QA answers remain verbose and cross-question interactions are still implicit.
- `2409` is especially vulnerable to residual false positives when `T2/F2` leaves the source object or target object only partially explicit.
- `2511` is especially vulnerable to residual false negatives when pairwise preference, ratings conversion, and RL-loop evidence are split across different sections of the paper.
- The `reviewer_guardrails` field solves the blocking `2511 M1` issue, but guardrails still depend on prompt compliance and do not enforce behavior by themselves.

# Revised Final Experiment Framing

- V0 is an additive workflow-layer experiment, not a criteria rewrite.
- The copied QA assets in `qa/` are the execution inputs for reviewer steps.
- `QA-only` tests whether structured question answering alone stabilizes criteria evaluation.
- `QA+synthesis` tests whether a normalized evidence object is necessary between QA and criteria evaluation.
- `2409` is the first paper to run because it needs no seed patch and directly probes object-boundary interpretation.
- `2511` follows after verifying the `M1 -> reviewer_guardrails` patch behaves cleanly.

# QA-Only Experiment Design

- Shared Stage 1 flow:
  - Input: metadata, title, abstract, current stage criteria paths, and the stage-specific QA JSON asset.
  - Junior output: one QA JSON answer object per reviewer, following `schemas/qa_output_contract.yaml`.
  - Evaluator output: one criteria-evaluation object per reviewer, following `schemas/criteria_evaluation_output_contract.yaml`.
  - Decision point: if both evaluator `stage_score` values are `>= 4`, include; if both are `<= 2`, exclude; otherwise send both reviewer/evaluator outputs to the Stage 1 senior prompt.
- Shared Stage 2 flow:
  - Input: metadata, title, abstract, full text, prior Stage 1 QA output, and the stage-specific Stage 2 QA asset.
  - Junior output: one Stage 2 QA JSON answer object per reviewer.
  - Evaluator output: one Stage 2 criteria-evaluation object per reviewer with `stage_score` and verdict recommendation.
  - Decision point: score `3` or evaluator conflict goes to Stage 2 senior prompt; otherwise include or exclude directly.
- `2409` Stage 1 focus:
  - Junior reviewers answer `M1-M2`, `T1-T5` using only title/abstract/metadata.
  - Evaluator maps QA evidence to Stage 1 criteria and uses `T1-T4` to reduce object-boundary false positives.
  - Senior resolves cases where BPM/NLP adjacency exists but extraction target remains unclear.
- `2409` Stage 2 focus:
  - Junior reviewers answer `M1-M2`, `F1-F5` using full text plus Stage 1 output.
  - Evaluator closes canonical criteria on primary research, concrete method, empirical validation, and non-target-family evidence.
  - Senior resolves mixed cases where full text adds process evidence but not enough source-target closure.
- `2511` Stage 1 focus:
  - Junior reviewers answer `T1-T5`; metadata notes stay outside answerable QA.
  - Evaluator maps preference signal, ratings/RL hint, audio-domain fit, learning-vs-evaluation, and survey signal to Stage 1 criteria.
  - Senior resolves cases where evaluation-only and learning signals compete or where audio appears only peripherally.
- `2511` Stage 2 focus:
  - Junior reviewers answer `F1-F5` using full text plus Stage 1 output.
  - Evaluator closes preference definition, ratings conversion, audio-domain role, learning loop, and survey exclusion.
  - Senior resolves borderline multimodal-audio and RL-loop cases when evaluator score stays `3`.

# QA+Synthesis Experiment Design

- Shared Stage 1 flow:
  - Input: metadata, title, abstract, current stage criteria paths, and the stage-specific QA JSON asset.
  - Junior QA output: synthesis-friendly QA answers with `candidate_synthesis_fields`.
  - Synthesis output: one stage-targeted synthesis object per reviewer, following `schemas/minimal_synthesis_schema.yaml`.
  - Evaluator output: one criteria-evaluation object per reviewer based only on the synthesis object.
  - Decision point: same Stage 1 routing contract as current workflow, but based on evaluator `stage_score`.
- Shared Stage 2 flow:
  - Input: metadata, title, abstract, full text, prior Stage 1 QA or synthesis output, and the Stage 2 QA asset.
  - Junior QA output: Stage 2 synthesis-friendly QA answers.
  - Synthesis output: Stage 2 synthesis object that carries forward Stage 1 evidence via `stage_handoff_status` and updates it with Stage 2 closure.
  - Evaluator output: one Stage 2 criteria-evaluation object per reviewer based only on the synthesis object.
  - Decision point: score `3` or evaluator conflict goes to Stage 2 senior prompt; otherwise include or exclude directly.
- `2409` Stage 1 synthesis focus:
  - Normalize `source_object`, `target_object`, `nlp_role`, and `non_target_family`.
  - Preserve unresolved object-boundary evidence as `state = unclear` instead of stretching criteria.
- `2409` Stage 2 synthesis focus:
  - Add `primary_research`, `concrete_method`, and `empirical_validation`.
  - Carry forward Stage 1 object-boundary evidence and explicitly note whether Stage 2 resolved or preserved the conflict.
- `2511` Stage 1 synthesis focus:
  - Normalize `preference_signal`, `comparison_type`, `audio_domain`, `learning_vs_evaluation`, and `survey_signal`.
  - Keep ratings/RL ambiguity explicit instead of collapsing it into a weak include.
- `2511` Stage 2 synthesis focus:
  - Add `ratings_conversion`, `rl_loop`, and `multimodal_audio_role`.
  - Use `stage_handoff_status` to show whether Stage 2 confirms, overturns, or leaves unresolved the Stage 1 interpretation.

# Minimal Synthesis Schema

- Schema file: `schemas/minimal_synthesis_schema.yaml`
- Top-level fields:
  - `paper_id`
  - `paper_title`
  - `stage`
  - `arm`
  - `field_records`
- Every `field_record` must contain:
  - `field_name`
  - `state`
  - `normalized_value`
  - `supporting_quotes`
  - `locations`
  - `missingness_reason`
  - `conflict_note`
  - `derived_from_qids`
  - `stage_handoff_status`
- `2409` required fields:
  - `source_object`
  - `target_object`
  - `nlp_role`
  - `non_target_family`
  - `primary_research`
  - `concrete_method`
  - `empirical_validation`
- `2511` required fields:
  - `preference_signal`
  - `comparison_type`
  - `ratings_conversion`
  - `rl_loop`
  - `audio_domain`
  - `multimodal_audio_role`
  - `learning_vs_evaluation`
  - `survey_signal`

# Execution Prompts

- Reviewer templates:
  - `templates/01_stage1_qa_only_reviewer_TEMPLATE.md`
  - `templates/02_stage2_qa_only_reviewer_TEMPLATE.md`
  - `templates/03_stage1_qa_synthesis_reviewer_TEMPLATE.md`
  - `templates/04_stage2_qa_synthesis_reviewer_TEMPLATE.md`
- Synthesis template:
  - `templates/05_synthesis_builder_TEMPLATE.md`
- Evaluator templates:
  - `templates/06_criteria_evaluator_from_qa_only_TEMPLATE.md`
  - `templates/07_criteria_evaluator_from_synthesis_TEMPLATE.md`
- Senior templates:
  - `templates/08_stage1_senior_from_qa_only_TEMPLATE.md`
  - `templates/09_stage1_senior_from_synthesis_TEMPLATE.md`
  - `templates/10_stage2_senior_from_qa_only_TEMPLATE.md`
  - `templates/11_stage2_senior_from_synthesis_TEMPLATE.md`
- Template manifest:
  - `templates/prompt_manifest.yaml`
- Thin loader:
  - `tools/render_prompt.py`
- Prompts remain externalized and are rendered by placeholders only.

# Experiment Matrix

| Arm | Input assets | Intermediate outputs | Final outputs | Expected failure mode it targets | Success criteria |
| --- | --- | --- | --- | --- | --- |
| `2409 + QA-only` | `qa/2409.13738.stage1.seed_qa.json`, `qa/2409.13738.stage2.seed_qa.json`, stage-split criteria, runtime metadata/title/abstract/fulltext | junior QA outputs, evaluator outputs, optional senior adjudication | Stage 1 and Stage 2 decision records with score + verdict | source/target/object-boundary confusion causing hard false positives | no criteria rewrites, no prompt hardcoding, better traceability than direct review, and reduced object-boundary FP without material F1 regression |
| `2409 + QA+synthesis` | same QA assets plus `schemas/minimal_synthesis_schema.yaml` | junior QA outputs, synthesis objects, evaluator outputs, optional senior adjudication | Stage 1 and Stage 2 decision records grounded in normalized fields | residual drift after raw QA when `source_object`, `target_object`, and `nlp_role` remain implicit | no criteria rewrites, no prompt hardcoding, cleaner field-level provenance, and improved or non-materially-regressed F1 versus current authority |
| `2511 + QA-only` | `qa/2511.13936.stage1.seed_qa.json`, `qa/2511.13936.stage2.seed_qa.json`, stage-split criteria, runtime metadata/title/abstract/fulltext | junior QA outputs, evaluator outputs, optional senior adjudication | Stage 1 and Stage 2 decision records with score + verdict | evaluation-only vs learning confusion, pairwise/ranking ambiguity, ratings-conversion ambiguity | no criteria rewrites, no prompt hardcoding, cleaner traceability than direct review, and better handling of preference-learning boundaries without material F1 regression |
| `2511 + QA+synthesis` | same QA assets plus `schemas/minimal_synthesis_schema.yaml` | junior QA outputs, synthesis objects, evaluator outputs, optional senior adjudication | Stage 1 and Stage 2 decision records grounded in normalized fields | normalization failures around `comparison_type`, `rl_loop`, `multimodal_audio_role`, and `learning_vs_evaluation` | no criteria rewrites, no prompt hardcoding, clearer field normalization, and improved or non-materially-regressed F1 versus current authority |

# Risk And Patch Notes

- Weak-but-retained seed questions:
  - `2409 T2/F2`: still packs source object and target object into one question family, so synthesis must split the resulting evidence into separate fields.
  - `2511 T2/F1`: still groups converted ratings and RL-loop eligibility, so evaluator and synthesis must keep the mechanisms separable in `normalized_value`.
- Likely false-positive risks:
  - `2409`: BPM or process-mining adjacency without explicit text-to-process extraction evidence.
  - `2511`: user-study preference collection that is only evaluative, or multimodal papers where audio is incidental.
- Likely false-negative risks:
  - `2409`: titles/abstracts that imply extraction targets indirectly and need Stage 2 closure.
  - `2511`: papers where ranking or preference conversion is described later in the method rather than in the abstract.
- Workflow-layer fixes that should stay out of formal criteria:
  - metadata guardrails for `2511`
  - synthesis normalization
  - evaluator scoring rubric
  - senior adjudication over evidence objects

# Recommended Run Order

1. `2409 + QA-only`
2. `2409 + QA+synthesis`
3. `2511 + QA-only`
4. `2511 + QA+synthesis`

Why this order:

- `2409` is the cleanest first paper because it needs no seed patch and directly tests whether structured evidence reduces object-boundary false positives.
- `QA-only` should run before `QA+synthesis` so the ablation is clean.
- `2511` should follow after verifying that the guardrail-only `M1` patch does not leak back into answerable evidence.
- If this work later branches into many parallel experiment tracks, use `www.k-dense.ai` rather than duplicating the same handoff context across multiple threads.
