# ChatGPT Seed QA Assets for 2409 and 2511: V1 Global Repair Bundle

This folder contains experiment-only QA seed assets derived from:

- `nlp_prisma_reviews_qa_generation_2026-03-17/qa_generated/2409.13738_stage1_qa.md`
- `nlp_prisma_reviews_qa_generation_2026-03-17/qa_generated/2409.13738_stage2_qa.md`
- `nlp_prisma_reviews_qa_generation_2026-03-17/qa_generated/2511.13936_stage1_qa.md`
- `nlp_prisma_reviews_qa_generation_2026-03-17/qa_generated/2511.13936_stage2_qa.md`

Scope:

- Only the two current weak papers: `2409.13738` and `2511.13936`
- Intended for `QA-only` and `QA+synthesis` experiments
- Copied from the frozen v0 bundle into a new v1 experiment branch so prompt, schema, and runner repairs can be tested without mutating v0
- Not production criteria
- Not current runtime prompt input
- Prompt templates live under `templates/` and are intended to be loaded externally rather than hardcoded in Python.

Normalization decisions:

- The seed QA questions were converted from Markdown tables into structured JSON.
- The incorrect seed-package claim that repo PDFs were missing was not carried forward as an experiment fact.
- Question text, handoff hints, and conflict-handling guidance were preserved.

Current production truth remains:

- Runtime prompt: `scripts/screening/runtime_prompts/runtime_prompts.json`
- Stage 1 criteria: `criteria_stage1/<paper_id>.json`
- Stage 2 criteria: `criteria_stage2/<paper_id>.json`
