# QA-first v1 global repair Phase 1 結果總報告

## 1. Current-State Recap

- current runtime prompt authority:
  - `scripts/screening/runtime_prompts/runtime_prompts.json`
- current production criteria authority:
  - `criteria_stage1/<paper_id>.json`
  - `criteria_stage2/<paper_id>.json`
- 本次 v1 bundle 只屬 experiment workflow：
  - `qa_first_experiments/qa_first_experiment_v1_global_repair_2409_2511_2026-03-18`
- 本次 v1 results root：
  - `screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18`
- current production score authority:
  - `2409.13738` Stage 1：
    - `screening/results/2409.13738_full/stage1_f1.stage_split_criteria_migration.json`
  - `2409.13738` Combined：
    - `screening/results/2409.13738_full/combined_f1.stage_split_criteria_migration.json`
  - `2511.13936` Stage 1：
    - `screening/results/2511.13936_full/stage1_f1.stage_split_criteria_migration.json`
  - `2511.13936` Combined：
    - `screening/results/2511.13936_full/combined_f1.stage_split_criteria_migration.json`

## 2. Execution Summary

- 執行日期：
  - `2026-03-19 04:10:21`
- 主執行命令：
  - `./.venv/bin/pip install PyYAML`
  - `./.venv/bin/python qa_first_experiments/qa_first_experiment_v1_global_repair_2409_2511_2026-03-18/tools/validate_bundle.py`
  - `./.venv/bin/python qa_first_experiments/qa_first_experiment_v1_global_repair_2409_2511_2026-03-18/tools/run_experiment.py --papers 2409.13738 2511.13936 --arms qa+synthesis --concurrency 6 --record-batch-size 6`
- 本輪實際執行的 arms：
  - `2409.13738__qa+synthesis`
  - `2511.13936__qa+synthesis`
- 本輪沒有執行的 arms：
  - `2409.13738__qa-only`
  - `2511.13936__qa-only`
  - `2307.05527`
  - `2601.19926`
- 原因：
  - 本輪只做 Phase 1。
  - Phase 1 gate 未通過，因此不進入 `qa-only` 與四篇 regression/stability pass。
- bundle validation 結果：
  - `bundle_validation: ok`
- run manifest：
  - `screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18/run_manifest.json`

## 3. Source Files Used For Comparison

### Current production baseline

- `2409.13738`
  - Stage 1:
    - `screening/results/2409.13738_full/stage1_f1.stage_split_criteria_migration.json`
  - Combined:
    - `screening/results/2409.13738_full/combined_f1.stage_split_criteria_migration.json`
- `2511.13936`
  - Stage 1:
    - `screening/results/2511.13936_full/stage1_f1.stage_split_criteria_migration.json`
  - Combined:
    - `screening/results/2511.13936_full/combined_f1.stage_split_criteria_migration.json`

### v0 QA-first baseline

- `2409.13738__qa+synthesis`
  - Stage 1:
    - `screening/results/qa_first_v0_2409_2511_2026-03-18/2409.13738__qa+synthesis/stage1_f1.json`
  - Combined:
    - `screening/results/qa_first_v0_2409_2511_2026-03-18/2409.13738__qa+synthesis/combined_f1.json`
- `2511.13936__qa+synthesis`
  - Stage 1:
    - `screening/results/qa_first_v0_2409_2511_2026-03-18/2511.13936__qa+synthesis/stage1_f1.json`
  - Combined:
    - `screening/results/qa_first_v0_2409_2511_2026-03-18/2511.13936__qa+synthesis/combined_f1.json`

### v1 Phase 1 outputs

- `2409.13738__qa+synthesis`
  - Stage 1:
    - `screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18/2409.13738__qa+synthesis/stage1_f1.json`
  - Combined:
    - `screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18/2409.13738__qa+synthesis/combined_f1.json`
- `2511.13936__qa+synthesis`
  - Stage 1:
    - `screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18/2511.13936__qa+synthesis/stage1_f1.json`
  - Combined:
    - `screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18/2511.13936__qa+synthesis/combined_f1.json`

## 4. Output Inventory

- results root：
  - `screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18`
- root-level files：
  - `screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18/run_manifest.json`
  - `screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18/REPORT_zh.md`

### 2409.13738__qa+synthesis

- arm dir：
  - `screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18/2409.13738__qa+synthesis`
- generated files：
  - `screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18/2409.13738__qa+synthesis/stage1_f1.json`
  - `screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18/2409.13738__qa+synthesis/combined_f1.json`
  - `screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18/2409.13738__qa+synthesis/latte_review_results.json`
  - `screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18/2409.13738__qa+synthesis/latte_fulltext_review_results.json`
  - `screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18/2409.13738__qa+synthesis/hygiene_summary.json`
  - `screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18/2409.13738__qa+synthesis/validation_failures.jsonl`
  - `screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18/2409.13738__qa+synthesis/selected_for_stage2.keys.txt`

### 2511.13936__qa+synthesis

- arm dir：
  - `screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18/2511.13936__qa+synthesis`
- generated files：
  - `screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18/2511.13936__qa+synthesis/stage1_f1.json`
  - `screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18/2511.13936__qa+synthesis/combined_f1.json`
  - `screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18/2511.13936__qa+synthesis/latte_review_results.json`
  - `screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18/2511.13936__qa+synthesis/latte_fulltext_review_results.json`
  - `screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18/2511.13936__qa+synthesis/hygiene_summary.json`
  - `screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18/2511.13936__qa+synthesis/validation_failures.jsonl`
  - `screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18/2511.13936__qa+synthesis/selected_for_stage2.keys.txt`

## 5. Hygiene Verification

### 2409.13738__qa+synthesis

- validation failure log：
  - `screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18/2409.13738__qa+synthesis/validation_failures.jsonl`
- hygiene summary：
  - `screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18/2409.13738__qa+synthesis/hygiene_summary.json`
- `validation_failures.jsonl` 存在：是
- `validation_failures.jsonl` 累積行數：`85`
- `hygiene_summary.json` 內容：
  - `paper_id = 2409.13738`
  - `arm = qa+synthesis`
  - `validation_failure_count = 2`
  - `updated_at = 2026-03-19 02:52:43`
- 累積 failure 類型分佈：
  - `identity_mismatch = 28`
  - `review_leak = 18`
  - `Stage 1/2 absent+insufficient_signal = 16`
  - `BadRequest JSON parse = 9`
  - `timeout = 5`
  - `other ValueError = 9`
- 解讀：
  - `validation_failures.jsonl` 反映多次 resume 的累積失敗。
  - `hygiene_summary.json` 只反映最後一次成功 run 的 tracker。
  - 兩者不一致，代表目前 summary aggregation 還不能單獨當 hygiene authority。
- review-level leak 檢查：
  - review title exact literal：
    - `NLP4PBM: A Systematic Review on Process Extraction using Natural Language Processing with Rule-based, Machine and Deep Learning Methods`
    - final outputs 命中 `0`
  - review topic literal：
    - `NLP for process extraction from natural-language text`
    - Stage 1 final outputs 命中 `40`
    - Combined final outputs 命中 `15`
- identity mismatch 檢查：
  - final saved outputs strict identity mismatch：`0`
- hygiene 結論：
  - title leak 已被清掉。
  - topic leak 仍持續存在於 final outputs。
  - `2409` hygiene gate 未通過。

### 2511.13936__qa+synthesis

- validation failure log：
  - `screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18/2511.13936__qa+synthesis/validation_failures.jsonl`
- hygiene summary：
  - `screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18/2511.13936__qa+synthesis/hygiene_summary.json`
- `validation_failures.jsonl` 存在：是
- `validation_failures.jsonl` 累積行數：`7`
- `hygiene_summary.json` 內容：
  - `paper_id = 2511.13936`
  - `arm = qa+synthesis`
  - `validation_failure_count = 7`
  - `updated_at = 2026-03-19 04:10:21`
- failure 類型分佈：
  - `BadRequest JSON parse = 7`
- review-level leak 檢查：
  - review title exact literal：
    - `Preference-Based Learning in Audio Applications: A Systematic Analysis`
    - final outputs 命中 `0`
  - review topic literal：
    - `Preference learning in audio applications`
    - final outputs 命中 `0`
- identity mismatch 檢查：
  - final saved outputs strict identity mismatch：`0`
- hygiene 結論：
  - `2511` contamination 已被壓到接近 `0`。
  - persistent identity mismatch 與 review-title/topic leak 都沒有留在 final outputs。

## 6. Metric Comparison

### 2409.13738

| Source | Stage 1 P/R/F1 | Combined P/R/F1 | Stage 2 Selected | Stage 1 Maybe | Stage 1 Senior-Finalized |
| --- | --- | --- | ---: | ---: | ---: |
| current production | `0.6000 / 1.0000 / 0.7500` | `0.6667 / 0.9524 / 0.7843` | `40` | `3` | `42` |
| v0 `qa+synthesis` | `0.5526 / 1.0000 / 0.7119` | `0.7407 / 0.9524 / 0.8333` | `38` | `8` | `36` |
| v1 `qa+synthesis` | `0.4038 / 1.0000 / 0.5753` | `0.7407 / 0.9524 / 0.8333` | `52` | `51` | `66` |

- 讀法：
  - v1 `2409` Combined F1 與 v0 完全相同：`0.8333`
  - v1 `2409` Stage 1 precision 明顯下降：`0.5526 -> 0.4038`
  - v1 `2409` Stage 2 selected count 明顯上升：`38 -> 52`
- 指標檔案：
  - current Stage 1：
    - `screening/results/2409.13738_full/stage1_f1.stage_split_criteria_migration.json`
  - current Combined：
    - `screening/results/2409.13738_full/combined_f1.stage_split_criteria_migration.json`
  - v0 Stage 1：
    - `screening/results/qa_first_v0_2409_2511_2026-03-18/2409.13738__qa+synthesis/stage1_f1.json`
  - v0 Combined：
    - `screening/results/qa_first_v0_2409_2511_2026-03-18/2409.13738__qa+synthesis/combined_f1.json`
  - v1 Stage 1：
    - `screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18/2409.13738__qa+synthesis/stage1_f1.json`
  - v1 Combined：
    - `screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18/2409.13738__qa+synthesis/combined_f1.json`

### 2511.13936

| Source | Stage 1 P/R/F1 | Combined P/R/F1 | Stage 2 Selected | Stage 1 Maybe | Stage 1 Senior-Finalized |
| --- | --- | --- | ---: | ---: | ---: |
| current production | `0.7838 / 0.9667 / 0.8657` | `0.8966 / 0.8667 / 0.8814` | `36` | `15` | `53` |
| v0 `qa+synthesis` | `0.9600 / 0.8000 / 0.8727` | `0.9583 / 0.7667 / 0.8519` | `25` | `1` | `23` |
| v1 `qa+synthesis` | `0.4688 / 1.0000 / 0.6383` | `0.9231 / 0.8000 / 0.8571` | `64` | `64` | `77` |

- 讀法：
  - v1 `2511` Stage 1 recall 從 v0 `0.8000` 回升到 `1.0000`
  - 但 Stage 1 precision 從 v0 `0.9600` 掉到 `0.4688`
  - Combined F1 比 v0 小幅上升：`0.8519 -> 0.8571`
  - Combined F1 仍低於 current production：`0.8814`
- 指標檔案：
  - current Stage 1：
    - `screening/results/2511.13936_full/stage1_f1.stage_split_criteria_migration.json`
  - current Combined：
    - `screening/results/2511.13936_full/combined_f1.stage_split_criteria_migration.json`
  - v0 Stage 1：
    - `screening/results/qa_first_v0_2409_2511_2026-03-18/2511.13936__qa+synthesis/stage1_f1.json`
  - v0 Combined：
    - `screening/results/qa_first_v0_2409_2511_2026-03-18/2511.13936__qa+synthesis/combined_f1.json`
  - v1 Stage 1：
    - `screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18/2511.13936__qa+synthesis/stage1_f1.json`
  - v1 Combined：
    - `screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18/2511.13936__qa+synthesis/combined_f1.json`

## 7. Case-Level Inspection

### 2409.13738

- case：
  - `elallaoui2018automatic`
- Stage 1：
  - v0：
    - `include (senior:4)`
  - v1：
    - `maybe (senior:3)`
- Combined：
  - v0：
    - `exclude (senior:1)`
  - v1：
    - `exclude (senior:2)`
- contamination：
  - v1 Stage 1 row 仍含 `NLP for process extraction from natural-language text`
- 解讀：
  - verdict 變化比較像 evaluator 變得更 defer。
  - 但這個 case 不能算乾淨的 hygiene success，因為 topic leak 仍在。

- case：
  - `honkisz2018concept`
- Stage 1：
  - v0：
    - `include (senior:4)`
  - v1：
    - `include (junior:4,4)`
- Combined：
  - v0：
    - `include (junior:5,5)`
  - v1：
    - `include (junior:5,5)`
- contamination：
  - v1 無 review-title/topic leak
- 解讀：
  - 這是 evaluator behavior shift，不是 contamination 修正。

### 2511.13936

- case：
  - `anastassiou2024seed`
- Stage 1：
  - v0：
    - `exclude (senior:1)`
  - v1：
    - `maybe (senior:3)`
- Combined：
  - v0：
    - 未進 Stage 2
  - v1：
    - `maybe (senior:3)`
- contamination：
  - v1 無 review-title/topic leak
- 解讀：
  - 這是最典型的 global defer-friendly repair 訊號。
  - 變化主要來自 evaluator behavior，不是 hygiene。

- case：
  - `lin2004rouge`
- Stage 1：
  - v0：
    - `exclude (junior:2,1)`
  - v1：
    - `exclude (senior:1)`
- Combined：
  - v0：
    - 未進 Stage 2
  - v1：
    - 未進 Stage 2
- contamination：
  - v0 row 含 review title literal
  - v1 row 無 review-title/topic leak
- 解讀：
  - 這個 case 的主要改善是 hygiene cleanup。
  - final verdict 沒變，但 candidate-level reasoning 綁定乾淨很多。

- case：
  - `google_scholar_hindex`
- Stage 1：
  - v0：
    - `exclude (senior:1)`
  - v1：
    - `maybe (senior:3)`
- Combined：
  - v0：
    - 未進 Stage 2
  - v1：
    - `maybe (senior:3)`
- contamination：
  - v0 row 含 review title literal
  - v1 row 無 review-title/topic leak
- 解讀：
  - 這個變化同時包含 hygiene 修正與 evaluator defer。

## 8. Phase-Gate Decision

- 是否進入 Phase 2：否
- 是否擴跑 `qa-only` arms：否
- 是否擴到四篇 regression/stability pass：否

### 理由

- `2409`：
  - hygiene 未過關，review topic literal 仍持續出現在 final outputs。
  - Stage 1 precision 也明顯變差。
- `2511`：
  - Stage 1 recall 確實回升。
  - Combined F1 也比 v0 略好。
  - 但 global defer patch 目前過強，Stage 1 precision 崩得太多，Combined 仍低於 current production。

### 本輪應回答的核心問題

- v1 global hygiene patch 是否把 contamination 壓到接近 0：
  - `2511`：是
  - `2409`：否
- v1 global Stage 1 defer-friendly patch 是否讓 `2511` 的 Stage 1 recall 回升：
  - 是，`0.8000 -> 1.0000`
- 這條 global patch 是否傷到 `2409` precision / closure quality：
  - Stage 1 precision：有
  - Combined closure quality：沒有，v1 Combined F1 與 v0 持平
- `2409 qa+synthesis` 在 v1 下是否不劣於 v0：
  - 是，Combined F1 同為 `0.8333`
- `2511 qa+synthesis` 在 v1 下是否優於 v0：
  - 是，Combined F1 `0.8519 -> 0.8571`
- 若 `2511` 仍未達 current production：
  - 主要不像 hygiene 問題
  - 比較像 global Stage 1 defer patch 過強，且 Stage 2 closure 還不夠

## 9. Recommended Next Move

- 不要先跑 `qa-only`
- 不要先擴到四篇
- 下一步應該留在同一個 Phase 1 loop，再跑一次 `2409 + 2511 qa+synthesis`

### 建議先修的兩件事

- 第一件：
  - 把 `2409` 的 review topic literal seepage 清到 final outputs 為 `0`
  - 目前 title leak 已經清掉，但 topic leak 還沒清掉
- 第二件：
  - 把 global Stage 1 defer 規則從目前的「大面積 unresolved => 3」收斂成「只有在存在正向 thematic fit / plausible target-object fit，但 closure 不足時才 => 3」

### 不建議現在做的事

- 不要因為 `2511` recall 回升，就直接進 `qa-only`
- 不要把這輪結果當成 production replacement
- 不要跳過 `2409` hygiene 未過關的事實，直接做四篇 regression

## 10. Final One-Line Summary

- `2511` 的 contamination 幾乎清乾淨了，且 recall 確實回升；但這條 global defer patch 目前過強。
- `2409` 的 combined 沒掉，但 Stage 1 precision 明顯惡化，而且 review topic leak 仍存在。
- 因此本輪結果不足以進 Phase 2；下一步應先修 `2409` hygiene 與 global defer policy，再重跑同一組 `qa+synthesis` arms。
