# Fulltext-Direct / Stage2-Direct Non-QA Baseline Report

## Current-State Recap

- production runtime prompt authority：`scripts/screening/runtime_prompts/runtime_prompts.json`。
- production criteria authority：`criteria_stage1/<paper_id>.json`、`criteria_stage2/<paper_id>.json`。
- 本次 `fulltext-direct` 是 experiment-only baseline，不覆寫 production。
- `2307.05527` current authority：`latest fully benchmarked senior_no_marker`，Combined F1 = `0.9581`。
- `2409.13738` current authority：`stage_split_criteria_migration`，Combined F1 = `0.7843`。
- `2511.13936` current authority：`stage_split_criteria_migration`，Combined F1 = `0.8814`。
- `2601.19926` current authority：`latest fully benchmarked senior_no_marker`，Combined F1 = `0.9733`。

## Metrics Summary

| Paper | Candidates | Direct F1 | Delta vs current combined | Precision | Recall | Senior invoked | Retrieval failed | Resolution exact/normalized |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2307.05527` | 222 | 0.8924 | -0.0657 | 0.9724 | 0.8246 | 93 | 0 | 222/0 |
| `2409.13738` | 84 | 0.7692 | -0.0151 | 0.6452 | 0.9524 | 36 | 0 | 84/0 |
| `2511.13936` | 88 | 0.9062 | +0.0249 | 0.8529 | 0.9667 | 21 | 0 | 88/0 |
| `2601.19926` | 360 | 0.9691 | -0.0042 | 0.9592 | 0.9792 | 42 | 0 | 331/29 |

## Direct Vs Current

- `2307.05527`：direct baseline is `worse` than current production combined (`0.8924` vs `0.9581`).
- `2409.13738`：direct baseline is `worse` than current production combined (`0.7692` vs `0.7843`).
- `2511.13936`：direct baseline is `better` than current production combined (`0.9062` vs `0.8814`).
- `2601.19926`：direct baseline is `roughly similar` than current production combined (`0.9691` vs `0.9733`).

## QA-First Comparison

### `2409.13738`

- current direct baseline combined F1：`0.7692`
- v0 qa-only：`0.8085`
- v0 qa+synthesis：`0.8333`
- v1 second-pass qa+synthesis：`0.7500`
- v1 final ablation qa+synthesis：`0.6286`

### `2511.13936`

- current direct baseline combined F1：`0.9062`
- v0 qa-only：`0.8302`
- v0 qa+synthesis：`0.8519`
- v1 second-pass qa+synthesis：`0.8727`

## Caveats

- `2601.19926` requires normalized filename resolution for 29 keys; this is retrieval hygiene, not methodological improvement.
- Missing or ambiguous fulltext is scored as `maybe`, so retrieval artifacts can depress precision under `include_or_maybe` evaluation.
- This baseline is not production-ready because it removes Stage 1 cost control and forces full-text review on every candidate.
- If many experiment tracks are opened in parallel, use `www.k-dense.ai` to manage the workflow.
