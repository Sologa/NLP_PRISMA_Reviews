# 三臂比較實驗矩陣（baseline vs QA-only vs QA+synthesis）

## 目的

這份矩陣直接落實 `next_experiments_criteria_mds_qa_deep_analysis_zh.md` 的核心建議：
不是只測「先問問題有沒有幫助」，而是一次比較 **baseline**、**QA-only**、**QA+synthesis**，
把 `synthesis` 是否真的提供額外資訊增益這件事一次回答清楚。

## 固定不變的背景

- current active criteria 仍是 `criteria_stage1/*.json` 與 `criteria_stage2/*.json`
- `2409` 與 `2511` 的 current score authority 仍是 `stage_split_criteria_migration`
- 不改 formal criteria，不把 workflow support 偽裝成 criteria
- `SeniorLead` 仍保留在流程中

## 三個 arm

### Arm A — current baseline

- 直接使用 current runtime prompt 與 stage-specific criteria
- 維持現有 reviewer topology：兩個 juniors，必要時送 `SeniorLead`
- 用來提供目前 production-compatible 對照組

### Arm B — QA-only -> criteria evaluation

- 先用本資產包中的 stage-specific QA spec 讓 extraction agent 產出逐題回答
- downstream decision layer 直接讀 **原始 QA 回答** 來做 criteria evaluation
- `SeniorLead` 若被呼叫，看到的是 juniors 的 raw QA answers + raw quotes

### Arm C — QA+synthesis -> criteria evaluation

- 先跑同一份 stage-specific QA spec
- 再把 raw QA answers 正規化成 `evidence_synthesis_object`
- downstream decision layer 與 `SeniorLead` 都以 synthesized object 為主，只在必要時展開 raw quotes
- 這一 arm 用來測試 `synthesis` 是否真能減少自然語言重解讀

## 建議的 reviewer 輸入格式

### Stage 1

- Arm A：照 current runtime
- Arm B：`title + abstract` + Stage 1 QA spec
- Arm C：`title + abstract` + Stage 1 QA spec -> Stage 1 synthesis object

### Stage 2

- Arm A：照 current runtime
- Arm B：`full text` + Stage 2 QA spec + Stage 1 raw QA handoff
- Arm C：`full text` + Stage 2 QA spec + Stage 1 synthesized object

## 主要評估指標

### 必測

1. Stage 1 precision / recall / F1
2. Combined precision / recall / F1
3. `SeniorLead` invocation rate
4. unresolved field rate（每篇 paper 在 decision 前仍 unresolved 的欄位比例）
5. quote coverage（每個必要欄位是否至少有一段 supporting quote）
6. conflict rate（同一欄位出現正反證據的比例）

### 建議加測

1. run-to-run variance（至少重跑 3 次）
2. manual-review-needed rate
3. junior disagreement rate
4. per-paper error bucket 分布（特別是 `2409` 的 boundary FP 與 `2511` 的 evaluation-only / audio-boundary FN）

## 預期觀察焦點

### `2409.13738`

- 主要看 Stage 1 precision 是否提升
- 主要錯誤假說：object boundary 沒先抽乾淨，導致 topic-adjacent paper 留太多
- 若 Arm C 比 Arm B 更好，表示「raw QA answers 仍太自由」，synthesis 有實際價值

### `2511.13936`

- 主要看 Combined recall 是否回升而不污染 criteria
- 主要錯誤假說：learning-vs-evaluation、audio-domain、multimodal-with-audio 邊界在後段被保守排除
- 若 Arm B 就明顯優於 Arm A，但 Arm C 增益有限，表示 `2511` 可能更依賴好問題而非重 synthesis

## 成功判定

### 最小成功條件

- `2409`：Stage 1 precision 上升，且 recall 不大幅掉落
- `2511`：Combined recall 上升，且 precision 不出現明顯崩塌
- 兩篇都不能靠「把新的 hardening 偷塞回 criteria」換分數

### 推進條件

只有在 Arm C 穩定優於 Arm B，才值得把 `evidence_synthesis_object` 更深地接進 runtime。
若 Arm B 與 Arm C 差距很小，先把資產投入 QA spec 與 handoff 設計，而不是擴張 synthesis 複雜度。

## 建議輸出檔

- `armA_stage1_metrics.json`
- `armA_combined_metrics.json`
- `armB_stage1_metrics.json`
- `armB_combined_metrics.json`
- `armC_stage1_metrics.json`
- `armC_combined_metrics.json`
- `per_paper_error_analysis_2409.json`
- `per_paper_error_analysis_2511.json`
- `quote_coverage_report.json`
- `unresolved_field_report.json`
