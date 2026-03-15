# Screening Migration Plan (Current Repo Only)

Historical note:

- This document is an older migration plan.
- Current active criteria are no longer `criteria_jsons/*.json`.
- Current runtime reads:
  - Stage 1: `criteria_stage1/<PAPER_ID>.json`
  - Stage 2: `criteria_stage2/<PAPER_ID>.json`
- For current-state guidance, use:
  - `AGENTS.md`
  - `docs/chatgpt_current_status_handoff.md`
  - `screening/results/results_manifest.json`

實作細節與指令請看：`docs/screening_smoke5_runbook.md`

## 0. 規則

1. 只做 screening，不混下載流程。
2. 所有執行 script 放 `scripts/screening/`。
3. 所有測試資料與輸出都在本 repo。
4. 不在 code 中硬編碼任何外部專案絕對路徑。

## 1. 目錄

```text
scripts/
  screening/
    prepare_review_smoke_inputs.py
    run_review_smoke5.sh
    vendor/
      scripts/topic_pipeline.py
      src/**
      resources/LatteReview/lattereview/**
      resources/schemas/review_response.schema.json

screening/
  data/
    source/cads/
      arxiv_metadata.json
      criteria.json
    cads_smoke5/
      arxiv_metadata.top5.json
      criteria.json
      manifest.json
  results/
    cads_smoke5/
      latte_review_results.json
```

## 2. 流程

1. `prepare_review_smoke_inputs.py` 從 `screening/data/source/cads/` 取資料，切 `top-k`（預設 5）。
2. `run_review_smoke5.sh` 讀 `.env`，跑本 repo vendor pipeline，輸出到 `screening/results/cads_smoke5/`。

也支援既有 repo 格式（無需手動改檔）：

- metadata: `refs/<PAPER_ID>/metadata/title_abstracts_metadata.jsonl`
- Stage 1 criteria: `criteria_stage1/<PAPER_ID>.json`
- Stage 2 criteria: `criteria_stage2/<PAPER_ID>.json`
- 執行：`PAPER_ID=<id> TOP_K=<k> bash scripts/screening/run_review_smoke5.sh`

## 3. 驗證

```bash
python3 scripts/screening/prepare_review_smoke_inputs.py --top-k 5
bash scripts/screening/run_review_smoke5.sh
```

## 4. 目前狀態

- scripts 已移到 `scripts/screening/`。
- source/smoke/output data 都在本 repo。
- code 端已移除外部專案絕對路徑。

## 5. 待辦決策（先記錄，暫不實作）

### 5.1 Criteria 固定格式 + 分流判斷

目標：

1. 先手動把 criteria 文檔整理為固定格式（structured JSON）。
2. 將判斷分流為兩段：
   - 時間條件：deterministic pre-filter（程式先判斷）
   - 其餘條件（例如 secondary research 等）：由 agent 判斷

驗收規則：

1. 手動整理後的 criteria 檔案需由你驗收後才可啟用。
2. 未驗收前，維持現有流程，不自動切換。

### 5.2 保留雙 setting，並用 args 控制做實驗

目標：

1. 保留「結構化欄位餵入」與「metadata 整串文字餵入」兩種 setting。
2. 以 CLI args 控制，支援 A/B 實驗比較。

規格草案（尚未實作）：

- `--criteria-mode`
  - `structured_split`：使用固定格式 criteria，時間先 pre-filter，其餘給 agent
  - `legacy_raw`：沿用目前 criteria 讀取/解析方式
- `--metadata-mode`
  - `fields`：以原始欄位提供，並以 `title`/`abstract` 做 screening（不做欄位轉換）
  - `raw_text`：直接餵 metadata 原始字串
- `--experiment-tag <name>`
  - 方便落盤比較不同 setting 結果

注意：

1. `raw_text` 可能增加 prompt 噪音與 token 成本，是否採用以實驗結果為準。
2. 上述 args 先記錄，待你確認後再進入實作。
