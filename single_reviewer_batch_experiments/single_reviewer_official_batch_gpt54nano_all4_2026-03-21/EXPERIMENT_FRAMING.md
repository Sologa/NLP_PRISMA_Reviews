# 實驗 framing

## 這次實驗是什麼

這次實驗明確定義為：

- 單審查者
- 官方 Batch API
- 全文直審
- experiment-only

也就是：

- 每個 candidate 只走一條 reviewer 決策路徑
- 不保留 `two juniors + SeniorLead`
- 不走 preserved-workflow
- 不把本地 `asyncio + semaphore + gather` 誤稱為 batch

## 這次實驗不是什麼

- 不是 production 變更
- 不是 shared provider 改造
- 不是 vendored runtime 語意改寫
- 不是把 `chat_batch()` 重新命名成官方 batch
- 不是先做單 reviewer、之後再考慮 batch

## 方法邊界

- criteria 只使用 `criteria_stage2/<paper_id>.json`
- prompt 使用 experiment-local template
- 目前 production `runtime_prompts.json` 只作為 current-state 參照，不作為本實驗 prompt source
- OpenAI API 執行必須走官方 batch job：
  - `files.create(..., purpose="batch")`
  - `batches.create(...)`
  - `output_file_id` / `error_file_id`
  - `custom_id` 對映

## 比對基線

這次結果只對照 current authority：

- `2307.05527`：`combined_after_fulltext_senior_no_marker_report.json`
- `2409.13738`：`combined_f1.stage_split_criteria_migration.json`
- `2511.13936`：`combined_f1.stage_split_criteria_migration.json`
- `2601.19926`：`combined_after_fulltext_senior_no_marker_report.json`
