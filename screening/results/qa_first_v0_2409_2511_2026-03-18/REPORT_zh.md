# QA-first cutoff-corrected 實驗結果報告

## Current-State Recap

- runtime prompts：`scripts/screening/runtime_prompts/runtime_prompts.json`
- production criteria：`criteria_stage1/<paper_id>.json` 與 `criteria_stage2/<paper_id>.json`
- repo-managed 3-reviewer path 現在一律先套 `cutoff_jsons/<paper_id>.json`

## Metrics Summary

| Paper | Arm | Stage 1 F1 | Combined F1 | Stage 2 selected | Stage 2 reviewed | Cutoff excluded |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `2409.13738` | `qa-only` | 0.7925 | 0.7925 | 32 | 0 | 15 |
| `2409.13738` | `qa+synthesis` | 0.7636 | 0.7636 | 34 | 0 | 15 |
| `2511.13936` | `qa-only` | 0.8519 | 0.8302 | 24 | 16 | 11 |
| `2511.13936` | `qa+synthesis` | 0.8727 | 0.8519 | 25 | 16 | 11 |

## Baseline Authority

- `2409.13738` current Stage 1 F1 = `0.7500`; Combined F1 = `0.7500`.
- `2511.13936` current Stage 1 F1 = `0.8788`; Combined F1 = `0.9062`.

## Notes

- `cutoff_filtered` rows are now authoritative excludes.
