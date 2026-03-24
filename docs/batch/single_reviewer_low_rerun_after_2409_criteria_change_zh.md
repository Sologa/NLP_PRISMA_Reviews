# 2409 Criteria 變更後 Low 重跑結果

- 範圍：所有在 `2026-03-23 03:03:53 +08:00` 這次 criteria 變更前已做過的模型，以 `low` effort 在 `2409.13738` 上重跑。
- 注意：這份報告以模型為單位彙整；若同一模型有多次嘗試，採最新完成者作為有效結果。
- `2409.13738` 現行完整 pipeline combined F1：`0.7843`

## 模型級摘要

| 模型 | 有效 run_id | 狀態 | cutoff後送審 | cutoff排除 | F1 | 與現行完整pipeline差值 | 備註 |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| `gpt-5` | `20260324_2409_rerun_gpt5_low` | `completed` | `65` | `19` | `0.8889` | `+0.1046` |  |
| `gpt-5-mini` | `20260324_2409_rerun2_gpt5mini_low` | `in_progress` | `65` | `19` | `` | `` | 初次嘗試 `20260324_2409_rerun_gpt5mini_low` 卡在 queue；目前以 `20260324_2409_rerun2_gpt5mini_low` 作為有效結果 |
| `gpt-5-nano` | `20260324_2409_rerun2_gpt5nano_low` | `in_progress` | `65` | `19` | `` | `` | 初次嘗試 `20260324_2409_rerun_gpt5nano_low` 卡在 queue；目前以 `20260324_2409_rerun2_gpt5nano_low` 作為有效結果 |
| `gpt-5.4` | `20260324_2409_rerun2_gpt54_low` | `in_progress` | `65` | `19` | `` | `` | 初次嘗試 `20260324_2409_rerun_gpt54_low` 卡在 queue；目前以 `20260324_2409_rerun2_gpt54_low` 作為有效結果 |
| `gpt-5.4-mini` | `20260324_2409_rerun_gpt54mini_low` | `completed` | `65` | `19` | `0.8636` | `+0.0793` |  |
| `gpt-5.4-nano` | `20260324_2409_rerun_gpt54nano_low` | `completed` | `65` | `19` | `0.8400` | `+0.0557` |  |

## 已完成

| 排名 | 模型 | F1 | Precision | Recall | 與現行完整pipeline差值 | 有效 run_id |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `gpt-5` | `0.8889` | `0.8333` | `0.9524` | `+0.1046` | `20260324_2409_rerun_gpt5_low` |
| 2 | `gpt-5.4-mini` | `0.8636` | `0.8261` | `0.9048` | `+0.0793` | `20260324_2409_rerun_gpt54mini_low` |
| 3 | `gpt-5.4-nano` | `0.8400` | `0.7241` | `1.0000` | `+0.0557` | `20260324_2409_rerun_gpt54nano_low` |

## 尚未完成

| 模型 | 最新 run_id | 狀態 | 已完成/總數 | 備註 |
| --- | --- | --- | --- | --- |
| `gpt-5-mini` | `20260324_2409_rerun2_gpt5mini_low` | `in_progress` | `0/65` | 初次嘗試 `20260324_2409_rerun_gpt5mini_low` 卡在 queue；目前以 `20260324_2409_rerun2_gpt5mini_low` 作為有效結果 |
| `gpt-5-nano` | `20260324_2409_rerun2_gpt5nano_low` | `in_progress` | `0/65` | 初次嘗試 `20260324_2409_rerun_gpt5nano_low` 卡在 queue；目前以 `20260324_2409_rerun2_gpt5nano_low` 作為有效結果 |
| `gpt-5.4` | `20260324_2409_rerun2_gpt54_low` | `in_progress` | `0/65` | 初次嘗試 `20260324_2409_rerun_gpt54_low` 卡在 queue；目前以 `20260324_2409_rerun2_gpt54_low` 作為有效結果 |

## 對應檔案

- 詳細 timing 對照：`docs/batch/single_reviewer_runs_vs_2409_criteria_change_zh.md`
- 詳細 CSV：`docs/batch/single_reviewer_low_rerun_after_2409_criteria_change.csv`
