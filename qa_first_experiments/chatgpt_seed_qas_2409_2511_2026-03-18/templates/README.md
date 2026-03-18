# QA-First Experiment Prompt Templates

These prompt templates are externalized on purpose.

Use them as file-based templates rather than embedding prompt text in `.py` files.

Recommended loading pattern:

1. Select the appropriate template under `templates/`.
2. Fill placeholders such as `{{PAPER_ID}}`, `{{STAGE}}`, `{{CRITERIA_JSON_PATH}}`, and `{{SEED_QA_JSON_PATH}}`.
3. Pass the rendered prompt to the model runner.

Template set:

- `01_stage1_qa_only_reviewer_TEMPLATE.md`
- `02_stage2_qa_only_reviewer_TEMPLATE.md`
- `03_stage1_qa_synthesis_reviewer_TEMPLATE.md`
- `04_stage2_qa_synthesis_reviewer_TEMPLATE.md`
- `05_synthesis_builder_TEMPLATE.md`
- `06_criteria_evaluator_from_qa_only_TEMPLATE.md`
- `07_criteria_evaluator_from_synthesis_TEMPLATE.md`
- `prompt_manifest.yaml`

Design rules:

- These templates are experiment-only workflow assets.
- They are not formal criteria.
- They are intended for the two current weak papers `2409.13738` and `2511.13936`, but are parameterized so the paper-specific paths are injected externally.

