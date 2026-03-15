# 2409 Criteria Stage-Split Report

Historical note:

- This report is a historical intermediate step.
- It predates the repo-wide migration to stage-specific criteria files.
- Current active criteria are:
  - `criteria_stage1/2409.13738.json`
  - `criteria_stage2/2409.13738.json`
- Current score authority is the stage-split migration metrics, not the `criteria_2409_stage_split` scores in this report.

Date: 2026-03-13  
Paper ID: `2409.13738`  
Run tag: `criteria_2409_stage_split`

## 1. Scope（本輪只改 criteria，不改 code/prompt/policy）

本輪僅做以下變更：

1. 修改 `criteria_jsons/2409.13738.json`（stage-specific operationalization）。
2. 新增本報告 `docs/criteria_2409_stage_split_report.md`。

明確未改動：

- `scripts/screening/vendor/src/pipelines/topic_pipeline.py`
- `scripts/screening/runtime_prompts/runtime_prompts.json`
- SeniorLead 機制
- Stage 1 routing / aggregation 規則
- `missing_fulltext` handling
- 其他 paper 的 criteria

## 2. 原 criteria 的 stage-mixing 問題

原版 `2409` 主要把以下條件放在同一層 required：

- 核心語義條件：是否為 NLP-driven process extraction
- fulltext 才穩定判斷條件：method concreteness、empirical validation
- 文獻型態條件：full paper / English / fulltext

這會讓 Stage 1（title+abstract）在資訊不完整時，容易把「無法確認」誤映射成「排除證據」；同時也會讓 reviewer 在 topic-adjacent 與 core target object 之間判斷不穩定。

## 3. 新 criteria 的 Stage 1 / Stage 2 拆分

### 3.1 Stage 1 observable projection（title+abstract）

在 `inclusion_criteria.required` 中明確化三個可觀測 gate：

1. **Core task gate**：必須是從自然語言到流程表示/流程模型的抽取或建構。
2. **Method-role gate**：NLP/text processing 必須是抽取流程中的核心方法，而非背景工具。
3. **Uncertainty handling gate**：若 core fit 成立但 abstract 缺 fulltext 級細節，應保留為 `maybe`，不應直接排除。

### 3.2 Stage 2 confirmatory projection（fulltext）

把 final confirmation 條件明確標成 Stage 2：

- full research paper
- English + fulltext available
- primary research
- concrete method completeness
- empirical validation completeness

### 3.3 Negative overrides

在 `exclusion_criteria` 明確寫出：

- topic-adjacent / process-adjacent 但非 text-to-process core objective
- 只做 generic NLP/LLM/dataset/benchmark，沒有流程表示抽取目標
- 只做 IE/NER/分類/檢索而未明確映射到 process representation
- BPM 非目標任務（prediction/redesign/compliance/matching 等）

並新增非功能欄位：

- `stage_projection.stage1_observable`
- `stage_projection.stage2_confirmatory`
- `stage_projection.negative_overrides`

（pipeline 目前不依賴這些欄位，不影響相容性）

## 4. Before / After 指標（baseline = senior_no_marker）

比較口徑：`include_or_maybe`；可評估集合固定為 78 筆。

### 4.1 Stage 1

| version | TP | FP | TN | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline `senior_no_marker` | 21 | 26 | 31 | 0 | 0.4468 | 1.0000 | 0.6176 |
| `criteria_2409_stage_split` | 21 | 19 | 38 | 0 | 0.5250 | 1.0000 | 0.6885 |

變化：

- precision：`+7.82pp`
- recall：持平（`1.0000`）
- F1：`+0.0709`

### 4.2 Combined（base + fulltext）

| version | TP | FP | TN | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline `senior_no_marker` | 21 | 19 | 38 | 0 | 0.5250 | 1.0000 | 0.6885 |
| `criteria_2409_stage_split` | 21 | 12 | 45 | 0 | 0.6364 | 1.0000 | 0.7778 |

變化：

- precision：`+11.14pp`
- recall：持平（`1.0000`）
- F1：`+0.0893`

## 5. FP/FN 差異分析

### 5.1 Stage 1：被修掉的典型 FP

共移除 15 筆 FP（無新增 FN），代表鍵：

- `qian_chatdev_2024`
- `devlin_bert`
- `devlin_bert_2018`
- `sanh2020distilbert`
- `mikolov2013distributed`
- `du2022_r-gqa`
- `cunningham2013getting`
- `li2005using`
- `hildebrandt_dcr`
- `vidgof2023large`

這些大多屬於 generic NLP / 非核心 text-to-process 目標，對應本輪新增的 Stage 1 strong negatives。

### 5.2 Combined：被修掉的典型 FP

共移除 10 筆 FP（無新增 FN），代表鍵：

- `qian_chatdev_2024`
- `devlin_bert`
- `devlin_bert_2018`
- `sanh2020distilbert`
- `mikolov2013distributed`
- `du2022_r-gqa`
- `cunningham2013getting`
- `li2005using`
- `hildebrandt_dcr`
- `vidgof2023large`

### 5.3 新增的 FP（仍需後續處理）

Combined 相比 baseline 新增 3 筆 FP：

- `bellan2020qualitative`
- `bellan2021process`
- `lopez2021challenges`

顯示仍有「看似 process extraction 但與 gold 邊界不一致」的 hard boundary case。

## 6. Spot-check（3 指定 + 2 自動替代）

> 註：你原先指定的 `leopold2018natural`、`ramos2019towards` 不在 `2409` 本地 metadata，可評估集中不存在；本輪採你同意的自動替代 key：`kourani_process_modelling_with_llm`、`grohs2023large`。

### 6.1 `etikala2021extracting`（gold=true）

- 原 criteria 下不穩定點：
  - Stage 1 `maybe (senior:3)`，在「決策模型 vs 流程模型、實驗細節可見度」之間搖擺。
- 新 criteria 後判定：
  - Stage 1 `include (junior:4,4)`；combined `include (junior:5,5)`。
- 對 gold 邊界：
  - 更符合 gold（從保留升為明確納入），反映 Stage 1 gate 對 core task 的可觀測映射更清楚。

### 6.2 `honkisz2018concept`（gold=true）

- 原 criteria 下不穩定點：
  - Stage 1 `maybe (senior:3)`，抽象層資訊不足時容易被 method/validation gate 牽制。
- 新 criteria 後判定：
  - Stage 1 `include (junior:4,4)`；combined `include (junior:5,5)`。
- 對 gold 邊界：
  - 更符合 gold，且消除過度依賴 senior 的邊界漂移。

### 6.3 `goncalves2011let`（gold=true）

- 原 criteria 下不穩定點：
  - Stage 1 `maybe (senior:3)`，雖然題名/摘要是典型 text-to-process，但被混入 fulltext 級 gate。
- 新 criteria 後判定：
  - Stage 1 `include (junior:5,4)`；combined 維持 `include (junior:5,5)`。
- 對 gold 邊界：
  - 與 gold 一致，且 Stage 1 判定更穩定。

### 6.4 `kourani_process_modelling_with_llm`（gold=false，替代 hard FP）

- 原 criteria 下不穩定點：
  - Stage 1/combined 都 `include`，易被 BPM+LLM 高相關詞誤判為核心 extraction。
- 新 criteria 理論上應判：
  - 依 negative override，若未明確指向 text-to-process extraction 目標，應偏 `exclude` 或至少 `maybe`。
- 新 criteria實跑結果：
  - 仍為 `include`（Stage 1 `include (junior:4,4)`；combined `include (junior:5,5)`）。
- 與 gold 邊界一致性：
  - 仍不一致（殘留 hard FP）。

### 6.5 `grohs2023large`（gold=false，替代 hard FP）

- 原 criteria 下不穩定點：
  - Stage 1/combined 都 `include`，BPM 任務廣泛敘述容易被當成 core extraction。
- 新 criteria 理論上應判：
  - 若只是 BPM task 一般能力展示且非核心 extraction object，應排除。
- 新 criteria實跑結果：
  - 仍為 `include`（Stage 1 `include (junior:5,4)`；combined `include (junior:5,5)`）。
- 與 gold 邊界一致性：
  - 仍不一致（殘留 hard FP）。

## 7. 結論：本輪成效與剩餘問題

### 7.1 本輪目標達成度

- 只改 criteria（無 code/prompt/policy 變更）條件下：
  - Stage 1 precision：`0.4468 -> 0.5250`
  - Combined precision：`0.5250 -> 0.6364`
  - Recall 持平：`1.0`
- 因此「提升 precision 並維持 recall」方向達成。

### 7.2 尚未達成之處

- Combined precision 尚未達 `>=0.70` 的目標帶。
- 仍有 12 筆 combined FP，且 hard FP 主要集中在：
  - process/BPM/LLM 高相關但 core extraction object 邊界模糊
  - 與 gold 標註邊界存在語義落差的 case

### 7.3 剩餘問題是否仍是 criteria

本輪顯示 criteria surgery 對 `2409` **有效**（FP 顯著下降且 recall 無損），但 hard FP 尚未完全消失。剩餘問題較像：

1. 部分樣本在 title/abstract 層面的語義可觀測性上，仍可同時支持「核心 extraction」與「topic-adjacent」兩種解讀。
2. 少數案例可能涉及 gold 邊界與 reviewer operational boundary 的張力，而不只是 criteria 文句不足。

換句話說，`2409` 的主要瓶頸確實包含 criteria stage split，但殘餘誤差不再是「只靠同一輪 criteria 文案微調即可全部解決」的型態。
