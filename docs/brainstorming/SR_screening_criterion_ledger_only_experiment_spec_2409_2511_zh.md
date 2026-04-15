# `#2 criterion ledger` 專案規格：`2409 + 2511` 雙 reviewer + `SeniorLead`

日期：2026-04-15  
語言：繁體中文  
定位：下一輪只做 `#2 criterion ledger` 的實驗規格  
範圍：只談 `#2`，不混 `#1/#3/#4/#5`

---

## 1. 這一輪要做什麼

這一輪只做一件事：

- 驗證 `#2 criterion ledger` 在 `2409.13738` 與 `2511.13936` 上，若改成
  - `2 juniors`
  - `1 SeniorLead`
  - `SeniorLead = gpt-5-mini`
  是否比目前已跑過的 single-reviewer `merged_ledger_2stage_async` 更合理、更穩

這一輪**不做**：

- `#1 verification routing`
- `#3 targeted retrieval`
- `#4 paper-specific semantic assets`
- `#5 stage-aware calibration`

也就是說，這一輪的實驗目標非常單純：

- 只測 `criterion ledger` 在 multi-reviewer + senior adjudication 架構下本身有沒有價值

---

## 2. 實驗放哪裡

相關實驗固定放在：

- `single_reviewer_async_experiments/`

建議新實驗根目錄：

- `single_reviewer_async_experiments/criterion_ledger_dual_junior_senior_2409_2511_2026-04-15`

原因：

- 方便和前一輪 `gpt5nano_all4_route_matrix_2026-04-14` 並列
- 不碰 production 流程
- 不污染既有 batch / baseline 實驗樹

---

## 3. 這一輪固定架構

### reviewer 架構

- `Junior A`
- `Junior B`
- `SeniorLead`

### 模型配置

建議預設：

- `Junior A = gpt-5-nano`
- `Junior B = gpt-5-nano`
- `SeniorLead = gpt-5-mini`

原因：

- 保持成本可控
- senior lane 才用比較強的模型
- 比較符合「cheap lane + stronger adjudication lane」的設計

### reasoning_effort

建議預設：

- juniors：`medium`
- senior：`medium`

這一輪先不要把 effort 當變因。

---

## 4. 這一輪到底復用哪些東西

### 可以直接復用

以下東西可以直接從前一輪實驗樹復用：

1. merged criterion assets
   - `single_reviewer_async_experiments/gpt5nano_all4_route_matrix_2026-04-14/assets/merged/2409.13738.stage1.json`
   - `single_reviewer_async_experiments/gpt5nano_all4_route_matrix_2026-04-14/assets/merged/2409.13738.stage2.json`
   - `single_reviewer_async_experiments/gpt5nano_all4_route_matrix_2026-04-14/assets/merged/2511.13936.stage1.json`
   - `single_reviewer_async_experiments/gpt5nano_all4_route_matrix_2026-04-14/assets/merged/2511.13936.stage2.json`

2. merged output schema
   - `criterion_assessments[]`
   - `stage_score`
   - `decision_rationale`
   - `manual_review_needed`
   - `routing_note`
   - `short_summary`

3. Stage 1 / Stage 2 merged templates 的主要骨架

4. 既有 async runner 的工具模組骨架

### 只可當 baseline / 參考，不可直接拿來當新結果

以下結果只能當 baseline 與 error analysis 參考：

- `merged_ledger_2stage_async` 已跑完的 `2409 / 2511`
- 尤其是：
  - `stage1_review.json`
  - `stage2_review.json`
  - `stage1_metrics.json`
  - `combined_metrics.json`
  - `final_results.json`

用途：

- 看哪條 criterion 最常 `UNCLEAR`
- 看哪條 criterion 最常被誤判
- 當新架構的 regression baseline

### 不應直接復用

以下東西不應直接混進這輪 `#2-only` 主體：

- verification 結果
- retrieval 結果
- `paper_profiles/*.json`
- 舊的 nano 單 reviewer outputs 當成新 junior reviewer 的正式輸出

換句話說：

- schema / assets / templates 可以復用
- 真正的 reviewer outputs 一定要重跑

---

## 5. 這一輪的完整流程

### Stage 0：cutoff

沿用現有 repo 規則：

- 先套 `cutoff_jsons/<paper_id>.json`

### Stage 1：雙 junior ledger

對每筆 record：

1. `Junior A` 看 title/abstract
2. `Junior B` 看 title/abstract
3. 兩人都輸出 Stage 1 ledger

每位 junior 固定輸出：

- `criterion_assessments[]`
- `stage_score`
- `decision_rationale`
- `short_summary`

### Stage 1 senior adjudication

以下情況才送 `SeniorLead`：

1. `Junior A` 與 `Junior B` 的 `stage_score` 落在不同決策區
   - 例如一個 `exclude`，一個 `maybe/include`
2. 核心 inclusion criteria 在兩人之間衝突
3. 任一核心 criterion 有 `UNCLEAR`

`SeniorLead` 輸入應包含：

- title
- abstract
- `Junior A` 的完整 ledger
- `Junior B` 的完整 ledger

`SeniorLead` 的任務：

- 不是重跑一遍自由判斷
- 而是看兩份 ledger 在哪條 criterion 上衝突
- 再做 Stage 1 final adjudication

### Stage 2：雙 junior ledger

只有 Stage 1 最終結果為：

- `include`
- `maybe`

才進 Stage 2。

Stage 2 流程與 Stage 1 類似：

1. `Junior A` 看 full text
2. `Junior B` 看 full text
3. 兩人都輸出 Stage 2 ledger

### Stage 2 senior adjudication

以下情況才送 `SeniorLead`：

1. `Junior A` / `Junior B` final decision 區不同
2. 核心 Stage 2 criterion 衝突
3. 任一核心 criterion 仍 `UNCLEAR`

`SeniorLead` 輸入應包含：

- title
- abstract
- full text
- `Junior A` Stage 2 ledger
- `Junior B` Stage 2 ledger

最後由 `SeniorLead` 產出 final Stage 2 adjudication。

---

## 6. 這一輪真正要測的問題

這一輪不是測：

- 更大模型會不會更強
- routing 值不值得
- retrieval 有沒有幫助

這一輪真正只測三件事：

1. `criterion ledger` 在雙 reviewer 架構下，是否比單 reviewer 更穩
2. `SeniorLead` 是否真的能利用兩份 ledger 做更合理 adjudication
3. `criterion-level disagreement` 是否提供比單一 reviewer output 更高價值的訊號

---

## 7. 這一輪至少要輸出的檔案

每個 `paper x phase` 至少要有：

- `junior_a_stage1_review.json`
- `junior_b_stage1_review.json`
- `stage1_senior_review.json`
- `stage1_final_results.json`
- `stage1_metrics.json`

- `junior_a_stage2_review.json`
- `junior_b_stage2_review.json`
- `stage2_senior_review.json`
- `final_results.json`
- `combined_metrics.json`

run 級別至少要有：

- `run_manifest.json`
- `request_log.jsonl`
- `response_log.jsonl`
- `SUMMARY_zh.md`

---

## 8. 這一輪怎麼跟前一輪比較

主要 baseline 應該是：

- 前一輪的 `merged_ledger_2stage_async`

也就是：

- 單 reviewer
- `gpt-5-nano`
- 兩階段 merged ledger

新實驗要回答的是：

- 加上第二位 junior 與 `SeniorLead = gpt-5-mini` 後
- 相較於舊的 `merged_ledger_2stage_async`
- `2409 / 2511` 有沒有更穩定或更合理

不應該把：

- `current authority`

當成本輪唯一 baseline。  
它只能當 secondary reference。

---

## 9. 估價

這裡先只估：

- `2409 + 2511`
- `2 juniors = gpt-5-nano`
- `SeniorLead = gpt-5-mini`
- async
- 不做 verification/retrieval/calibration

保守估計：

- 約 `$2.5 ~ $4.0`

若 senior lane 命中太多：

- 約 `$4.0 ~ $6.0`

建議預算：

- 先抓 `$4`

---

## 10. 這一輪不需要改什麼

### 不需要改 formal criteria 語義

不應改：

- `criteria_stage1/<paper_id>.json`
- `criteria_stage2/<paper_id>.json`

至少這一輪不應該改它們的語義。

### 需要改的是 support layer

這一輪真正需要做的是：

1. 多 reviewer ledger prompt
2. senior adjudication prompt
3. dual-junior runner
4. senior merge/adjudication logic
5. 新的輸出與 metrics 對齊

---

## 11. 目前建議

如果這個 thread 只做 `#2`，那最合理的做法是：

1. 只開 `2409 + 2511`
2. 只做 `criterion ledger`
3. 採用：
   - `Junior A = gpt-5-nano`
   - `Junior B = gpt-5-nano`
   - `SeniorLead = gpt-5-mini`
4. 不混 routing / retrieval / calibration
5. 把前一輪 `merged_ledger_2stage_async` 當主 baseline

一句話版：

- 這一輪要做的不是更花俏的新架構
- 而是驗證：`criterion ledger` 在真正的雙 reviewer + senior 架構下，到底有沒有實質價值
