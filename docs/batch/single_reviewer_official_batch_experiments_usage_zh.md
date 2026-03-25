# 單審查者官方 Batch 實驗使用手冊

這份文件整理目前 repo 內已落地的單審查者官方 Batch 實驗線、helper、執行指令、artifact 目錄、已完成 run 與成本計算方法。

## 目標與邊界

- 實驗型態固定為 `single-reviewer official-batch baseline`
- 每個 candidate 只走一條 reviewer 決策路徑
- API 執行固定走 OpenAI 官方 Batch API
- 不改 production shared API semantics
- 不改 `scripts/screening/runtime_prompts/runtime_prompts.json`
- criteria 固定使用 `criteria_stage2/<paper_id>.json`

## 目前 helper 與 bundle 位置

官方 batch orchestration helper：

- [openai_batch_runner.py](../../scripts/screening/openai_batch_runner.py)

目前已落地 bundle：

- [single_reviewer_official_batch_gpt5_all4_2026-03-22](../../single_reviewer_batch_experiments/single_reviewer_official_batch_gpt5_all4_2026-03-22)
- [single_reviewer_official_batch_gpt54_all4_2026-03-22](../../single_reviewer_batch_experiments/single_reviewer_official_batch_gpt54_all4_2026-03-22)
- [single_reviewer_official_batch_gpt5mini_all4_2026-03-22](../../single_reviewer_batch_experiments/single_reviewer_official_batch_gpt5mini_all4_2026-03-22)
- [single_reviewer_official_batch_gpt5nano_all4_2026-03-22](../../single_reviewer_batch_experiments/single_reviewer_official_batch_gpt5nano_all4_2026-03-22)
- [single_reviewer_official_batch_gpt54mini_all4_2026-03-22](../../single_reviewer_batch_experiments/single_reviewer_official_batch_gpt54mini_all4_2026-03-22)
- [single_reviewer_official_batch_gpt54nano_all4_2026-03-21](../../single_reviewer_batch_experiments/single_reviewer_official_batch_gpt54nano_all4_2026-03-21)

## 每條 bundle 的主要檔案

每條 bundle 都包含：

- `manifest.json`
- `config/experiment_config.json`
- `tools/run_experiment.py`
- `tools/validate_bundle.py`
- `tools/render_prompt.py`
- `templates/01_single_reviewer_TEMPLATE.md`
- `templates/validation_retry_repair_policy.md`
- `samples/sample_reviewer_output.json`

## 共用輸入來源

- cutoff：`cutoff_jsons/<paper_id>.json`
- metadata：`refs/<paper_id>/metadata/title_abstracts_metadata.jsonl`
- gold：`refs/<paper_id>/metadata/title_abstracts_metadata-annotated.jsonl`
- fulltext：`refs/<paper_id>/mds/*.md`
- criteria：`criteria_stage2/<paper_id>.json`

## 現在的前置順序

目前 active 的旗艦版 batch runner 已改成：

1. 先讀 `cutoff_jsons/<paper_id>.json`
2. 再讀 `refs/<paper_id>/metadata/title_abstracts_metadata.jsonl`
3. 對 metadata 套用 deterministic 時間窗硬條件
4. cutoff 通過者才進全文解析與 batch request 建構
5. cutoff 不通過者直接產生 `exclude (cutoff_time_window)` 結果列，不送模型

也就是說，時間窗現在不是事後提示，而是 pipeline 最前面的 hard filter。

## 驗證指令

以 `gpt-5` bundle 為例：

```bash
./.venv/bin/python single_reviewer_batch_experiments/single_reviewer_official_batch_gpt5_all4_2026-03-22/tools/validate_bundle.py
```

檢查 model 與 serialization：

```bash
./.venv/bin/python single_reviewer_batch_experiments/single_reviewer_official_batch_gpt5_all4_2026-03-22/tools/validate_bundle.py \
  --check-model \
  --check-serialization
```

其他 bundle 只要把路徑替換成對應目錄即可。

## 執行模式

所有 runner 都支援三種模式：

- `--mode submit`
- `--mode collect`
- `--mode run`

說明：

- `submit`：建立 request、寫 `input.jsonl`、上傳 batch file、建立 batch job
- `collect`：讀既有 `run_id`、拉 batch 狀態、下載 `output.jsonl` / `error.jsonl`、解析結果、產生 F1 與報告
- `run`：`submit + wait + collect`

## 常用執行指令

### `gpt-5` 跑 `2409.13738`，`low`

```bash
./.venv/bin/python single_reviewer_batch_experiments/single_reviewer_official_batch_gpt5_all4_2026-03-22/tools/run_experiment.py \
  --mode run \
  --papers 2409.13738 \
  --reasoning-effort low
```

### `gpt-5.4` 跑 `2409.13738`，`low`

```bash
./.venv/bin/python single_reviewer_batch_experiments/single_reviewer_official_batch_gpt54_all4_2026-03-22/tools/run_experiment.py \
  --mode run \
  --papers 2409.13738 \
  --reasoning-effort low
```

### `gpt-5-mini` 跑 `2409.13738`，`low`

```bash
./.venv/bin/python single_reviewer_batch_experiments/single_reviewer_official_batch_gpt5mini_all4_2026-03-22/tools/run_experiment.py \
  --mode run \
  --papers 2409.13738 \
  --reasoning-effort low
```

### `gpt-5-nano` 跑 `2409.13738`，`low`

```bash
./.venv/bin/python single_reviewer_batch_experiments/single_reviewer_official_batch_gpt5nano_all4_2026-03-22/tools/run_experiment.py \
  --mode run \
  --papers 2409.13738 \
  --reasoning-effort low
```

### `gpt-5.4-mini` 跑 `2409.13738`，`low`

```bash
./.venv/bin/python single_reviewer_batch_experiments/single_reviewer_official_batch_gpt54mini_all4_2026-03-22/tools/run_experiment.py \
  --mode run \
  --papers 2409.13738 \
  --reasoning-effort low
```

### `gpt-5.4-nano` 跑 `2409.13738`，`low`

```bash
./.venv/bin/python single_reviewer_batch_experiments/single_reviewer_official_batch_gpt54nano_all4_2026-03-21/tools/run_experiment.py \
  --mode run \
  --papers 2409.13738 \
  --reasoning-effort low
```

### 四篇全跑

```bash
./.venv/bin/python single_reviewer_batch_experiments/<bundle>/tools/run_experiment.py \
  --mode run \
  --papers 2307.05527 2409.13738 2511.13936 2601.19926
```

## artifact 目錄結構

每個 `run_id` 都會產生：

- `screening/results/<results_root>/runs/<run_id>/batch_jobs/review/<model>/input.jsonl`
- `screening/results/<results_root>/runs/<run_id>/batch_jobs/review/<model>/upload_file.json`
- `screening/results/<results_root>/runs/<run_id>/batch_jobs/review/<model>/batch_create.json`
- `screening/results/<results_root>/runs/<run_id>/batch_jobs/review/<model>/batch_latest.json`
- `screening/results/<results_root>/runs/<run_id>/batch_jobs/review/<model>/output.jsonl`
- `screening/results/<results_root>/runs/<run_id>/batch_jobs/review/<model>/error.jsonl`
- `screening/results/<results_root>/runs/<run_id>/batch_jobs/review/<model>/parsed_results.json`
- `screening/results/<results_root>/runs/<run_id>/papers/<paper_id>/single_reviewer_batch_results.json`
- `screening/results/<results_root>/runs/<run_id>/papers/<paper_id>/single_reviewer_batch_f1.json`
- `screening/results/<results_root>/runs/<run_id>/papers/<paper_id>/cutoff_audit.json`
- `screening/results/<results_root>/runs/<run_id>/run_manifest.json`
- `screening/results/<results_root>/runs/<run_id>/REPORT_zh.md`

## GitHub 上傳建議

建議保留在 GitHub 供後續分析的檔案：

- bundle 本體：`single_reviewer_batch_experiments/<bundle>/`
- 結果摘要：`screening/results/<results_root>/runs/<run_id>/run_manifest.json`
- Batch 狀態與 token 使用量：`screening/results/<results_root>/runs/<run_id>/batch_jobs/review/<model>/batch_latest.json`
- 每篇結果：`screening/results/<results_root>/runs/<run_id>/papers/<paper_id>/single_reviewer_batch_results.json`
- 每篇指標：`screening/results/<results_root>/runs/<run_id>/papers/<paper_id>/single_reviewer_batch_f1.json`
- 人看得懂的 run 摘要：`screening/results/<results_root>/runs/<run_id>/REPORT_zh.md`
- metadata / gold：`refs/<paper_id>/metadata/*.jsonl`
- criteria：`criteria_stage2/<paper_id>.json`

建議不要推上 GitHub 的 raw batch 工件：

- `screening/results/<results_root>/runs/<run_id>/batch_jobs/review/<model>/input.jsonl`
- `screening/results/<results_root>/runs/<run_id>/batch_jobs/review/<model>/output.jsonl`
- `screening/results/<results_root>/runs/<run_id>/batch_jobs/review/<model>/error.jsonl`
- `screening/results/<results_root>/runs/<run_id>/batch_jobs/review/<model>/upload_file.json`
- `screening/results/<results_root>/runs/<run_id>/batch_jobs/review/<model>/batch_create.json`
- `screening/results/<results_root>/runs/<run_id>/batch_jobs/review/<model>/parsed_results.json`
- `screening/results/<results_root>/runs/<run_id>/papers/<paper_id>/fulltext_resolution_audit.json`

## 目前已完成的重要 run

### `gpt-5`

- `2409.13738`，`low`：
  - [run_manifest.json](../../screening/results/single_reviewer_official_batch_gpt5_all4_2026-03-22/runs/20260322_094235Z/run_manifest.json)
  - [batch_latest.json](../../screening/results/single_reviewer_official_batch_gpt5_all4_2026-03-22/runs/20260322_094235Z/batch_jobs/review/gpt-5/batch_latest.json)
  - [single_reviewer_batch_f1.json](../../screening/results/single_reviewer_official_batch_gpt5_all4_2026-03-22/runs/20260322_094235Z/papers/2409.13738/single_reviewer_batch_f1.json)

### `gpt-5.4`

- `2409.13738`，`low`：
  - [run_manifest.json](../../screening/results/single_reviewer_official_batch_gpt54_all4_2026-03-22/runs/20260322_120414Z/run_manifest.json)
  - [batch_latest.json](../../screening/results/single_reviewer_official_batch_gpt54_all4_2026-03-22/runs/20260322_120414Z/batch_jobs/review/gpt-5.4/batch_latest.json)
  - [single_reviewer_batch_f1.json](../../screening/results/single_reviewer_official_batch_gpt54_all4_2026-03-22/runs/20260322_120414Z/papers/2409.13738/single_reviewer_batch_f1.json)

### `gpt-5-nano`

- 四篇全量，未顯式 effort：
  - [run_manifest.json](../../screening/results/single_reviewer_official_batch_gpt5nano_all4_2026-03-22/runs/20260321_173147Z/run_manifest.json)
- `2409.13738`，`high`：
  - [run_manifest.json](../../screening/results/single_reviewer_official_batch_gpt5nano_all4_2026-03-22/runs/20260322_023703Z/run_manifest.json)
- `2409.13738`，`low`：
  - [run_manifest.json](../../screening/results/single_reviewer_official_batch_gpt5nano_all4_2026-03-22/runs/20260322_041730Z/run_manifest.json)

### `gpt-5-mini`

- 四篇全量，未顯式 effort：
  - [run_manifest.json](../../screening/results/single_reviewer_official_batch_gpt5mini_all4_2026-03-22/runs/20260321_180142Z/run_manifest.json)
- `2409.13738`，`low`：
  - [run_manifest.json](../../screening/results/single_reviewer_official_batch_gpt5mini_all4_2026-03-22/runs/20260322_042952Z/run_manifest.json)

### `gpt-5.4-nano`

- `2409.13738`，未顯式 effort：
  - [run_manifest.json](../../screening/results/single_reviewer_official_batch_gpt54nano_all4_2026-03-21/runs/20260321_171754Z/run_manifest.json)
- `2409.13738`，`low`：
  - [run_manifest.json](../../screening/results/single_reviewer_official_batch_gpt54nano_all4_2026-03-21/runs/20260322_053646Z/run_manifest.json)

### `gpt-5.4-mini`

- `2409.13738`，`low`：
  - [run_manifest.json](../../screening/results/single_reviewer_official_batch_gpt54mini_all4_2026-03-22/runs/20260322_080853Z/run_manifest.json)

## 成本計算公式

定義：

- `I = input_tokens`
- `C = cached_input_tokens`
- `O = output_tokens`
- `U = I - C`

官方 Batch 成本：

```text
Cost_batch = (U / 1,000,000) * P_in
           + (C / 1,000,000) * P_cache
           + (O / 1,000,000) * P_out
```

注意：

- `reasoning_tokens` 已經包含在 `output_tokens` 裡
- 不要再把 `reasoning_tokens` 額外乘一次價格

## 已驗證的官方 Batch 單價

來源：

- [GPT-5 模型頁](https://developers.openai.com/api/docs/models/gpt-5)
- [GPT-5-mini 模型頁](https://developers.openai.com/api/docs/models/gpt-5-mini)
- [GPT-5-nano 模型頁](https://developers.openai.com/api/docs/models/gpt-5-nano)
- [GPT-5.4-mini 模型頁](https://developers.openai.com/api/docs/models/gpt-5.4-mini)
- [GPT-5.4-nano 模型頁](https://developers.openai.com/api/docs/models/gpt-5.4-nano)
- [Pricing](https://developers.openai.com/api/docs/pricing)

目前用到的 Batch 單價：

- `gpt-5`：input `$1.25`，cached input `$0.125`，output `$10.00`
- `gpt-5.4`：input `$2.50`，cached input `$0.25`，output `$15.00`
- `gpt-5-mini`：input `$0.25`，cached input `$0.025`，output `$2.00`
- `gpt-5-nano`：input `$0.05`，cached input `$0.005`，output `$0.40`
- `gpt-5.4-mini`：input `$0.75`，cached input `$0.075`，output `$4.50`
- `gpt-5.4-nano`：input `$0.20`，cached input `$0.02`，output `$1.25`

## 旗艦版成本估算方法

如果要用已跑過的 `mini` / `nano` token 使用量去回推 `gpt-5` 或 `gpt-5.4` 旗艦版，做法是：

1. 先拿本地 run 的 `input_tokens` / `output_tokens`
2. 再用公開量化資料估計旗艦版相對 `mini` 的 output-token 倍率
3. 把估出的 `O_est` 代回 `Cost_batch`

目前最可用的公開量化資料是這篇論文的補充表：

- [PREPRINTv2-Performance of GPT-5 Frontier Models in Ophthalmology Question Answering](https://storage.googleapis.com/arxiv-dataset/arxiv/arxiv/pdf/2508/2508.09956v2.pdf)

其中 `GPT-5` 相對 `GPT-5-mini` 的 output-token 比率大約是：

- `low`：`1.3378x`
- `medium`：`1.0918x`
- `high`：`1.1940x`

這些倍率可以當 `gpt-5` 的估算底座；`gpt-5.4` 若沒有公開 direct token 表，可暫時用同家族倍率做 proxy，但必須標示為估算，不可當成官方精確 token 規格。

## 比對 current baseline

單 reviewer 官方 batch 的結果，請對照：

- `2307.05527`：
  - [combined_after_fulltext_senior_no_marker_report.json](../../screening/results/2307.05527_full/combined_after_fulltext_senior_no_marker_report.json)
- `2409.13738`：
  - [combined_f1.stage_split_criteria_migration.json](../../screening/results/2409.13738_full/combined_f1.stage_split_criteria_migration.json)
- `2511.13936`：
  - [combined_f1.stage_split_criteria_migration.json](../../screening/results/2511.13936_full/combined_f1.stage_split_criteria_migration.json)
- `2601.19926`：
  - [combined_after_fulltext_senior_no_marker_report.json](../../screening/results/2601.19926_full/combined_after_fulltext_senior_no_marker_report.json)

## 備註

- `gpt-5` 與 `gpt-5.4` 的 `low / medium / high` 真實 token 使用量仍以實跑為準
- 用 `mini` 或 `nano` 回推旗艦版成本時，重點是估預算區間，不是偽裝成精確實測
- 若後續實驗線再變多，適合用 `www.k-dense.ai` 做 workflow 管理

## 本次新增的 `gpt-5 low` 實跑摘要

- run id：`20260322_094235Z`
- paper：`2409.13738`
- model：`gpt-5`
- reasoning_effort：`low`
- batch status：`completed`
- request：`84 / 84` 成功
- usage：
  - `input_tokens = 866,843`
  - `output_tokens = 87,456`
  - `reasoning_tokens = 39,360`
- 實測 Batch 成本：
  - `Cost = (866,843 / 1,000,000) * 1.25 + (87,456 / 1,000,000) * 10`
  - `= 1.083554 + 0.874560 = $1.958114`
- F1：
  - `precision = 0.8500`
  - `recall = 0.8095`
  - `f1 = 0.8293`

## 本次新增的 `gpt-5.4 low` 實跑摘要

- run id：`20260322_120414Z`
- paper：`2409.13738`
- model：`gpt-5.4`
- reasoning_effort：`low`
- batch status：`completed`
- request：`84 / 84` 成功
- usage：
  - `input_tokens = 866,843`
  - `output_tokens = 63,740`
  - `reasoning_tokens = 7,466`
- 實測 Batch 成本：
  - `Cost = (866,843 / 1,000,000) * 2.50 + (63,740 / 1,000,000) * 15`
  - `= 2.167108 + 0.956100 = $3.123208`
- F1：
  - `precision = 0.7500`
  - `recall = 0.8571`
  - `f1 = 0.8000`

## 2409 criteria 變更後的 low 重跑

- 通用 rerun bundle：
  - [single_reviewer_official_batch_2409_low_rerun_after_criteria_change_2026-03-24](../../single_reviewer_batch_experiments/single_reviewer_official_batch_2409_low_rerun_after_criteria_change_2026-03-24)
- 結果根目錄：
  - [single_reviewer_official_batch_2409_low_rerun_after_criteria_change_2026-03-24](../../screening/results/single_reviewer_official_batch_2409_low_rerun_after_criteria_change_2026-03-24)
- 專門報告：
  - [single_reviewer_low_rerun_after_2409_criteria_change_zh.md](./single_reviewer_low_rerun_after_2409_criteria_change_zh.md)
  - [single_reviewer_low_rerun_after_2409_criteria_change.csv](./single_reviewer_low_rerun_after_2409_criteria_change.csv)
- 與 criteria 變更先後對照：
  - [single_reviewer_runs_vs_2409_criteria_change_zh.md](./single_reviewer_runs_vs_2409_criteria_change_zh.md)
  - [single_reviewer_runs_vs_2409_criteria_change.csv](./single_reviewer_runs_vs_2409_criteria_change.csv)
- 清理 log：
  - [single_reviewer_2409_rerun_cleanup_log_2026-03-25.md](./single_reviewer_2409_rerun_cleanup_log_2026-03-25.md)

目前本地保留的有效 rerun：

- `gpt-5`
  - run id：`20260324_2409_rerun_gpt5_low`
  - F1：`0.8889`
- `gpt-5-mini`
  - run id：`20260324_2409_rerun2_gpt5mini_low`
  - F1：`0.8571`
- `gpt-5-nano`
  - run id：`20260324_2409_rerun2_gpt5nano_low`
  - F1：`0.8400`
- `gpt-5.4`
  - run id：`20260324_2409_rerun2_gpt54_low`
  - F1：`0.9130`
- `gpt-5.4-mini`
  - run id：`20260324_2409_rerun_gpt54mini_low`
  - F1：`0.8636`
- `gpt-5.4-nano`
  - run id：`20260324_2409_rerun_gpt54nano_low`
  - F1：`0.8400`

已刪除第一遍的映射關係不在此重複列出，統一記錄於 cleanup log。
