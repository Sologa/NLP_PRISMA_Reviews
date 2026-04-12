# Performance Comparison

- run_id: `20260408_full_gpt54mini_xhigh_2stagedirect_2409_2511`
- comparison scope:
- current two-stage direct-review runs on `2409.13738` and `2511.13936`
- current authority from `screening/results/results_manifest.json`
- note:
- for `2409.13738`, the runner currently compares against `combined_f1.stage_split_criteria_migration.json = 0.7500`
- this file follows the actual current authority used by the runner, not the older value shown in some historical summaries

## 2409.13738

| Model | effort | Stage 1 F1 | Combined F1 | Delta vs current stage1 | Delta vs current combined | Notes |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| current authority | `authority` | `0.7500` | `0.7500` | `0.0000` | `0.0000` | `results_manifest.json` |
| gpt-5 | `low` | `0.8333` | `0.8444` | `+0.0833` | `+0.0944` | `20260406_full_gpt5_low_2stagedirect_2409_2511` |
| gpt-5 | `low` | `0.8571` | `0.8889` | `+0.1071` | `+0.1389` | `20260406_full_gpt5_low_2stagedirect_rerun_2409_2511` |
| gpt-5-mini | `low` | `0.7925` | `0.8750` | `+0.0425` | `+0.1250` | `20260406_full_gpt5mini_low_2stagedirect_2409_2511` |
| gpt-5.4-mini | `low` | `0.7727` | `0.8095` | `+0.0227` | `+0.0595` | `20260408_full_gpt54mini_low_2stagedirect_2409_2511` |
| gpt-5.4-mini | `xhigh` | `0.7727` | `0.8095` | `+0.0227` | `+0.0595` | `20260408_full_gpt54mini_xhigh_2stagedirect_2409_2511` |

## 2511.13936

| Model | effort | Stage 1 F1 | Combined F1 | Delta vs current stage1 | Delta vs current combined | Notes |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| current authority | `authority` | `0.8788` | `0.9062` | `0.0000` | `0.0000` | `results_manifest.json` |
| gpt-5 | `low` | `0.8929` | `0.8727` | `+0.0141` | `-0.0335` | `20260406_full_gpt5_low_2stagedirect_2409_2511` |
| gpt-5-mini | `low` | `0.8475` | `0.8621` | `-0.0313` | `-0.0442` | `20260406_full_gpt5mini_low_2stagedirect_2409_2511` |
| gpt-5.4-mini | `low` | `0.8077` | `0.8077` | `-0.0711` | `-0.0986` | `20260408_full_gpt54mini_low_2stagedirect_2409_2511` |
| gpt-5.4-mini | `xhigh` | `0.9123` | `0.9123` | `+0.0335` | `+0.0060` | `20260408_full_gpt54mini_xhigh_2stagedirect_2409_2511` |

## Readout

- `2409.13738`: `gpt-5.4-mini xhigh` did not improve over `gpt-5.4-mini low`; both stayed at `0.7727 / 0.8095`.
- `2511.13936`: `gpt-5.4-mini xhigh` materially improved over `gpt-5.4-mini low`, from `0.8077 / 0.8077` to `0.9123 / 0.9123`.
- `2511.13936`: on combined F1, `gpt-5.4-mini xhigh` is now slightly above current authority by `+0.0060`.
- `2409.13738`: on combined F1, the best current two-stage run in repo remains `gpt-5 low rerun` at `0.8889`.

## Historical One-Stage Reference

- `2409.13738`: best historical one-stage gpt-5 family score in current summary is `gpt-5.4 low` with combined F1 `0.9130`.
- `2511.13936`: best historical one-stage gpt-5 family score in current summary is `gpt-5 low` with combined F1 `0.9000`.
- These are historical one-stage direct-review artifacts, not the current baseline workflow.
