# Experiment Framing

## Status

- experiment-only
- isolated from production criteria / prompts / results authority
- intended to compare against current single-reviewer direct-review baselines and prior split QA lines
- decision authority aligned to production score-driven mapping

## Why this line exists

這條實驗線的目的不是重寫 criteria，而是把 single reviewer lane 改成：

```text
cutoff
-> stage1 merged review (micro-QA + criteria decision)
-> stage2 selection
-> stage2 merged review (micro-QA + criteria decision)
-> final single-reviewer verdict
```

其中 stage recommendation 不由模型單獨輸出；runner 依 `stage_score` deterministic 派生 `include / maybe / exclude`。

## Non-goals

- 不修改 `criteria_stage1/`
- 不修改 `criteria_stage2/`
- 不修改 `scripts/screening/runtime_prompts/runtime_prompts.json`
- 不修改 `screening/results/results_manifest.json`
- 不引入 multi-reviewer routing 或 `SeniorLead`
- 不沿用 split synthesis/evaluator phase

## Current comparison authority

- `2409.13738`：`stage_split_criteria_migration`
- `2511.13936`：`stage_split_criteria_migration`

## Testing policy

- smoke first
- full second
- all phases fixed to `gpt-5-nano`
- all runs default to `--reasoning-effort low`
