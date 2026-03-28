# Experiment Framing

## Status

- experiment-only
- isolated from production criteria / prompts / results authority
- intended to compare against current single-reviewer direct-review baselines

## Why this line exists

這條實驗線的目的不是重寫 criteria，而是把 single reviewer lane 內部改成：

```text
cutoff
-> stage1 QA extraction
-> stage1 deterministic synthesis
-> stage1 criteria evaluation
-> stage2 selection
-> stage2 QA extraction
-> stage2 deterministic synthesis
-> stage2 criteria evaluation
-> final single-reviewer verdict
```

## Non-goals

- 不修改 `criteria_stage1/`
- 不修改 `criteria_stage2/`
- 不修改 `scripts/screening/runtime_prompts/runtime_prompts.json`
- 不修改 `screening/results/results_manifest.json`
- 不引入 multi-reviewer routing 或 `SeniorLead`

## Current comparison authority

- `2409.13738`：`stage_split_criteria_migration`
- `2511.13936`：`stage_split_criteria_migration`

## Testing policy

- smoke first
- full second
- all phases fixed to `gpt-5-nano`
- all runs fixed to `--reasoning-effort low`
