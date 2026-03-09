# cutoff_jsons 轉換與邏輯規格

本資料夾用來放「時間限制（publication time constraints）」的結構化 JSON。

用途：
1. 把 `criteria_mds/*.md` 裡的時間條件獨立出來，和主題/方法條件分流。
2. 讓時間過濾可 deterministic 執行，不交由 agent 主觀判斷。

---

## 1) 標準 JSON 格式

建議每篇 paper 對應一個檔案：`cutoff_jsons/<paper_id>.json`

```json
{
  "paper_id": "2307.05527",
  "source_md": "criteria_mds/2307.05527.md",
  "time_policy": {
    "enabled": true,
    "date_field": "published",
    "start_date": "2018-02-01",
    "start_inclusive": true,
    "end_date": "2023-02-01",
    "end_inclusive": true,
    "timezone": "UTC"
  },
  "evidence": [
    {
      "section": "Stage 2 Inclusion Criteria",
      "criterion_id": "I4",
      "text": "Temporal window: submitted/published between February 1, 2018 and February 1, 2023."
    }
  ],
  "normalization_notes": [
    "Parsed Month D, YYYY to ISO date.",
    "No explicit conflict found."
  ]
}
```

### 欄位說明

1. `time_policy.enabled`
   - `true`: 有時間限制，應套用過濾。
   - `false`: 明示無時間限制。
2. `date_field`
   - 目前建議固定 `published`。
3. `start_date` / `end_date`
   - ISO `YYYY-MM-DD`。
   - 若沒有下界或上界，可用 `null`。
4. `start_inclusive` / `end_inclusive`
   - 明確記錄邊界是否包含，避免語意歧義。
5. `evidence`
   - 必留原文證據，供人工驗收。

---

## 2) 時間判定語意

推薦語意：

1. 若 `enabled=false`，不做時間過濾。
2. 若 `enabled=true`，套用：
   - `published_date >= start_date`（若有 start）
   - `published_date <= end_date`（若 `end_inclusive=true`）
   - `published_date < end_date`（若 `end_inclusive=false`）

---

## 3) `criteria_mds -> cutoff_jsons` 轉換邏輯

這裡定義「應該如何轉換」，作為人工與程式共同依據。

### 3.1 取值優先序

1. Stage 2 Screening Criteria（優先）。
2. Stage 1 Retrieval Criteria（僅當 Stage 2 沒有時間條件時作為 fallback）。

理由：Stage 2 是最終納排規則，優先於檢索階段。

### 3.2 時間條件偵測

在 I/E/R 條件中抓含下列語意的句子：

1. `between ... and ...`
2. `from ... to/until ...`
3. `after/since ...`
4. `before/until ...`
5. `no restriction` / `no publication-year restriction`

### 3.3 日期正規化

轉成 ISO 日期，支援常見格式：

1. `YYYY-MM-DD`
2. `YYYY/MM/DD`
3. `Month D, YYYY`
4. `YYYY`（轉為 `YYYY-01-01`，並在 notes 註明是 year-only）

### 3.4 邊界處理

1. 若原文是 `between A and B`，預設 `start_inclusive=true`, `end_inclusive=true`。
2. 若原文是 `before B`，預設 `end_inclusive=false`。
3. 若原文是 `until B` 但未明示，需在 `normalization_notes` 記錄採用的包含規則。

### 3.5 衝突解決

若同篇出現多條時間規則：

1. Stage 2 優先於 Stage 1。
2. 同層衝突時採「較嚴格交集」。
3. 任何自動決策都要寫進 `normalization_notes`。

### 3.6 無時間限制

若明示「無時間限制」，輸出：

```json
{
  "time_policy": {
    "enabled": false,
    "date_field": "published",
    "start_date": null,
    "start_inclusive": true,
    "end_date": null,
    "end_inclusive": false,
    "timezone": "UTC"
  }
}
```

---

## 4) 與現有程式碼的對應

目前 screening code 的時間過濾核心在：

1. `resolve_cutoff_time_window(...)`
2. `run_latte_review(...)` 內的 discard 規則
3. metadata 日期解析 `_parse_date_bound(...)` / `_extract_publication_date(...)`

目前程式尚未直接讀 `cutoff_jsons/*.json`。

現階段若要使用 `cutoff_jsons`，建議流程：

1. 先在 `cutoff_jsons/<paper_id>.json` 完成人工驗收。
2. 再把 `start_date/end_date` 映射到執行參數（或映射到 workspace cutoff artifact）。

---

## 5) 建議驗收清單

每個 `cutoff_jsons/*.json` 建議至少檢查：

1. `evidence.text` 是否能逐字支持 `time_policy`。
2. 日期是否正確正規化（尤其 Month 名稱與時區）。
3. `end_inclusive` 是否符合原文語意。
4. 是否把 Stage 1 與 Stage 2 的時間規則搞混。
5. `enabled=false` 是否真的有明示「無時間限制」證據。

