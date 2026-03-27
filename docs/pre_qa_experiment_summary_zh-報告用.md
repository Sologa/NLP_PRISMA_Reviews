# QA 前實驗短版摘要（報告用）

日期：2026-03-26  
版本註記：本版只保留 cutoff 修正後仍有比較價值的 pre-QA 線，不再保留完整歷史長敘事。  
用途：這不是完整實驗史，而是給報告用的短版決策摘要。內容只保留三類線：`senior_no_marker`、canonical QA、single-reviewer low-model comparison。

## 1. 一句話結論

- `2409/2511` 的 pre-QA 3-reviewer 比較，現在應只看 cutoff-corrected `senior_no_marker`、current authority，以及 canonical QA。
- `2511` 的 `0.8788 / 0.9062` 是 cutoff 修正後的 `stage_split_criteria_migration` current authority，不是 `senior_no_marker`。
- `2601` 的 `0.9792 / 0.9731` 是 cutoff 修正後的 `senior_no_marker` stable reference。
- `single-reviewer low` 是外部對照線，不是 pre-QA 3-reviewer authority。

## 2. Authority 說明

| Paper | 目前應採用的 authority | Stage 1 F1 | Combined F1 | 說明 |
| --- | --- | ---: | ---: | --- |
| `2409.13738` | `stage_split_criteria_migration` | `0.7500` | `0.7500` | current authority，應直接以 stage-split 正式 JSON 為準。 |
| `2511.13936` | `stage_split_criteria_migration` | `0.8788` | `0.9062` | current authority；這就是你前面問到的 `0.8788 / 0.9062`。 |
| `2601.19926` | `senior_no_marker` | `0.9792` | `0.9731` | stable reference；這就是你前面問到的 `0.9792 / 0.9731`。 |

## 3. cutoff-corrected 3-reviewer 基線

說明：這張表只放四篇 paper 的 `senior_no_marker`。  
`TP / FP / TN / FN` 取 `combined_after_fulltext` 的 confusion；`cutoff_excluded_count` 取各 paper 的 `cutoff_audit.json`。

| Paper | Stage 1 F1 | Combined F1 | TP | FP | TN | FN | cutoff excluded | 備註 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `2307.05527` | `0.9113` | `0.9113` | `149` | `7` | `40` | `22` | `29` | 目前穩定，但只是 stable reference。 |
| `2409.13738` | `0.6774` | `0.6774` | `21` | `20` | `39` | `0` | `15` | 只是歷史 `senior_no_marker` 基線，不是 current authority。 |
| `2511.13936` | `0.7436` | `0.7500` | `27` | `15` | `42` | `3` | `11` | cutoff 修正後仍明顯落後 current authority。 |
| `2601.19926` | `0.9792` | `0.9731` | `326` | `9` | `14` | `9` | `0` | 目前 stable reference 就是這條線。 |

## 4. `2409` / `2511` 詳細比較

### 4.1 `2409.13738`

| Method | Stage 1 F1 | Combined F1 | Stage 1 confusion | Combined confusion | 短評 |
| --- | ---: | ---: | --- | --- | --- |
| `senior_no_marker` | `0.6774` | `0.6774` | `21 / 20 / 39 / 0` | `21 / 20 / 39 / 0` | FP 偏高，是 current authority 之前的歷史基線。 |
| `current authority = stage_split_criteria_migration` | `0.7500` | `0.7500` | `21 / 14 / 45 / 0` | `21 / 14 / 45 / 0` | 相比 `senior_no_marker`，主要改善是把 FP 從 `20` 壓到 `14`。 |
| `QA v1 second-pass (qa+synthesis)` | `0.7368` | `0.7368` | `21 / 15 / 44 / 0` | `21 / 15 / 44 / 0` | 比 `senior_no_marker` 好，但仍略低於 current authority。 |

### 4.2 `2511.13936`

| Method | Stage 1 F1 | Combined F1 | Stage 1 confusion | Combined confusion | 短評 |
| --- | ---: | ---: | --- | --- | --- |
| `senior_no_marker` | `0.7436` | `0.7500` | `29 / 19 / 38 / 1` | `27 / 15 / 42 / 3` | cutoff 修正後仍落後明顯，不能再當 current 敘事。 |
| `current authority = stage_split_criteria_migration` | `0.8788` | `0.9062` | `29 / 7 / 50 / 1` | `29 / 5 / 52 / 1` | 這是目前正式 authority；cutoff 問題已修正，主問題回到 reviewer / evidence interpretation。 |
| `QA v1 second-pass (qa+synthesis)` | `0.8772` | `0.8571` | `25 / 2 / 55 / 5` | `24 / 2 / 55 / 6` | precision 很高，但 recall 掉下來，最終未超過 current authority。 |

## 5. single-reviewer low comparison

### 5.1 F1 快覽

說明：先只看 `Final F1`。`current authority` 放進來只是當比較基準；`gpt-5 low` 或 `gpt-5-mini low` 若沒有完成 run，就直接標示 `未完成`。

| Paper | Current authority Combined F1 | `gpt-5 low` | `gpt-5-mini low` |
| --- | ---: | ---: | ---: |
| `2307.05527` | `0.9113` | `未完成` | `0.9130` |
| `2409.13738` | `0.7500` | `0.8889` | `0.8571` |
| `2511.13936` | `0.9062` | `0.9000` | `0.7692` |
| `2601.19926` | `0.9731` | `0.8982` | `0.9573` |

### 5.2 詳細表

說明：這裡只比較 `gpt-5 low` 與 `gpt-5-mini low`。  
`Final F1` 直接取各自的 `single_reviewer_batch_f1.json`；`Delta vs current authority` 為 `Final F1 - current authority combined F1` 現算值。

| Paper | Model | Run ID | Final F1 | Precision | Recall | TP | FP | TN | FN | Delta vs current authority | 備註 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `2307.05527` | `gpt-5` | `未完成` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | repo 內目前沒有完成的 `gpt-5 low` run。 |
| `2307.05527` | `gpt-5-mini` | `20260325_gpt5mini_low_2307_sep` | `0.9130` | `0.9735` | `0.8596` | `147` | `4` | `47` | `24` | `+0.0017` | 與目前 stable reference 幾乎持平，僅略高。 |
| `2409.13738` | `gpt-5` | `20260324_2409_rerun_gpt5_low` | `0.8889` | `0.8333` | `0.9524` | `20` | `4` | `59` | `1` | `+0.1389` | 高於 current 3-reviewer authority，但屬不同 workflow。 |
| `2409.13738` | `gpt-5-mini` | `20260324_2409_rerun2_gpt5mini_low` | `0.8571` | `0.7500` | `1.0000` | `21` | `7` | `56` | `0` | `+0.1071` | 同樣高於 current 3-reviewer authority，但仍是 single-reviewer 對照。 |
| `2511.13936` | `gpt-5` | `20260326_gpt5_low_2511_sep` | `0.9000` | `0.9000` | `0.9000` | `27` | `3` | `55` | `3` | `-0.0063` | 幾乎貼近 current authority `0.9062`，但仍略低。 |
| `2511.13936` | `gpt-5-mini` | `20260326_gpt5mini_low_2511_resubmit` | `0.7692` | `0.9091` | `0.6667` | `20` | `2` | `56` | `10` | `-0.1370` | 明顯低於 current authority `0.9062`。 |
| `2601.19926` | `gpt-5` | `20260326_gpt5_low_2601_sep` | `0.8982` | `0.9823` | `0.8274` | `278` | `5` | `19` | `58` | `-0.0749` | 明顯低於目前 stable reference `0.9731`。 |
| `2601.19926` | `gpt-5-mini` | `20260325_gpt5mini_low_2601_sep` | `0.9573` | `0.9813` | `0.9345` | `314` | `6` | `18` | `22` | `-0.0158` | 低於目前 stable reference `0.9731`。 |

## 6. 短結論

- `2307`：目前完成的 `gpt-5-mini low` single-reviewer 幾乎與 stable reference 持平，僅略高 `+0.0017`。
- `2409`：在 cutoff 修正後，`current authority > canonical QA > senior_no_marker`；兩條 single-reviewer low 對照都高於目前 3-reviewer authority，但屬不同 workflow。
- `2511`：current authority 已回到 `0.9062`；新完成的 `gpt-5 low` 已幾乎貼近 authority（`0.9000`），但仍未超過；`gpt-5-mini low` 則明顯更低。
- `2511`：不應再把它描述成 cutoff mismatch 主問題；cutoff 已修正，現在主問題是 reviewer / evidence interpretation。
- `2601`：高位穩定，`0.9792 / 0.9731` 本身就是 `senior_no_marker` stable reference；新完成的 `gpt-5 low` 與既有 `gpt-5-mini low` 都低於它。 

## 7. 數據來源（正式 JSON）

- `senior_no_marker`：
  - `screening/results/2307.05527_full/review_after_stage1_senior_no_marker_report.json`
  - `screening/results/2307.05527_full/combined_after_fulltext_senior_no_marker_report.json`
  - `screening/results/2409.13738_full/review_after_stage1_senior_no_marker_report.json`
  - `screening/results/2409.13738_full/combined_after_fulltext_senior_no_marker_report.json`
  - `screening/results/2511.13936_full/review_after_stage1_senior_no_marker_report.json`
  - `screening/results/2511.13936_full/combined_after_fulltext_senior_no_marker_report.json`
  - `screening/results/2601.19926_full/review_after_stage1_senior_no_marker_report.json`
  - `screening/results/2601.19926_full/combined_after_fulltext_senior_no_marker_report.json`
- `2409/2511 current authority`：
  - `screening/results/2409.13738_full/stage1_f1.stage_split_criteria_migration.json`
  - `screening/results/2409.13738_full/combined_f1.stage_split_criteria_migration.json`
  - `screening/results/2511.13936_full/stage1_f1.stage_split_criteria_migration.json`
  - `screening/results/2511.13936_full/combined_f1.stage_split_criteria_migration.json`
- canonical QA：
  - `screening/results/qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19/2409.13738__qa+synthesis/stage1_f1.json`
  - `screening/results/qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19/2409.13738__qa+synthesis/combined_f1.json`
  - `screening/results/qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19/2511.13936__qa+synthesis/stage1_f1.json`
  - `screening/results/qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19/2511.13936__qa+synthesis/combined_f1.json`
- single-reviewer low：
  - `screening/results/single_reviewer_official_batch_gpt5mini_all4_2026-03-22/runs/20260325_gpt5mini_low_2307_sep/papers/2307.05527/single_reviewer_batch_f1.json`
  - `screening/results/single_reviewer_official_batch_2409_low_rerun_after_criteria_change_2026-03-24/runs/20260324_2409_rerun_gpt5_low/papers/2409.13738/single_reviewer_batch_f1.json`
  - `screening/results/single_reviewer_official_batch_2409_low_rerun_after_criteria_change_2026-03-24/runs/20260324_2409_rerun2_gpt5mini_low/papers/2409.13738/single_reviewer_batch_f1.json`
  - `screening/results/single_reviewer_official_batch_gpt5_all4_2026-03-22/runs/20260326_gpt5_low_2511_sep/papers/2511.13936/single_reviewer_batch_f1.json`
  - `screening/results/single_reviewer_official_batch_gpt5mini_all4_2026-03-22/runs/20260326_gpt5mini_low_2511_resubmit/papers/2511.13936/single_reviewer_batch_f1.json`
  - `screening/results/single_reviewer_official_batch_gpt5_all4_2026-03-22/runs/20260326_gpt5_low_2601_sep/papers/2601.19926/single_reviewer_batch_f1.json`
  - `screening/results/single_reviewer_official_batch_gpt5mini_all4_2026-03-22/runs/20260325_gpt5mini_low_2601_sep/papers/2601.19926/single_reviewer_batch_f1.json`
- cutoff counts：
  - `screening/results/2307.05527_full/cutoff_audit.json`
  - `screening/results/2409.13738_full/cutoff_audit.json`
  - `screening/results/2511.13936_full/cutoff_audit.json`
  - `screening/results/2601.19926_full/cutoff_audit.json`
