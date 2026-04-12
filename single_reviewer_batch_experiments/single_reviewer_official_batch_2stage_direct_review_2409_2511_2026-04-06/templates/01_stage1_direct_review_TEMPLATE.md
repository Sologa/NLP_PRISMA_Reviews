# 單審查者官方 Batch 兩階段直審：Stage 1

你正在執行 experiment-only 的 `{{WORKFLOW_ARM}}`。

## 不可違反的約束

- current production runtime prompts 仍是：`scripts/screening/runtime_prompts/runtime_prompts.json`
- 這個實驗不修改 production runtime path，也不沿用 preserved-workflow
- Stage 1 只使用 `criteria_stage1/<paper_id>.json`
- 只能根據提供的 title、abstract、metadata 與 Stage 1 criteria JSON 判斷
- 不可使用 full text、外部知識、常識補完、作者名聲、venue 名聲或模型家族印象
- 如果必要條件沒有被 title/abstract 明確文字支持，不可自行假設成立

## 審查目標

- `paper_id`: `{{PAPER_ID}}`
- `candidate_key`: `{{CANDIDATE_KEY}}`
- `candidate_title`: `{{CANDIDATE_TITLE}}`
- `workflow_arm`: `{{WORKFLOW_ARM}}`
- `stage`: `stage1`

## Stage 1 Criteria JSON

```json
{{STAGE_CRITERIA_JSON_CONTENT}}
```

## Inputs

### Metadata
```json
{{METADATA_JSON}}
```

### Source Record Provenance
```json
{{SOURCE_RECORD_PROVENANCE_JSON}}
```

### Title
```text
{{TITLE}}
```

### Abstract
```text
{{ABSTRACT}}
```

## 任務

請回傳一個 Stage 1 reviewer 的 JSON 物件。

評分規則：

- `1` = 強排除
- `2` = 偏排除
- `3` = 證據不足、混合或不確定
- `4` = 偏納入
- `5` = 強納入

判斷規則：

- 只有在 Stage 1 納入條件被 title/abstract 明確正向支持時，才可給 `4` 或 `5`
- 當 Stage 1 排除條件成立，或核心納入條件被 title/abstract 明確否定時，給 `1` 或 `2`
- 核心 fit plausible 但 title/abstract 仍缺關鍵資訊時，給 `3`
- 所有 evidence 都必須可追溯到 title/abstract 文字

## 輸出格式

請回傳一個 JSON 物件，形狀必須與下列範例一致：

```json
{{REVIEW_OUTPUT_JSON_SCHEMA_HINT}}
```

## 硬規則

- `decision_recommendation` 必須與 `stage_score` 對齊：
  - `1-2 => exclude`
  - `3 => maybe`
  - `4-5 => include`
- `satisfied_inclusion_points`、`triggered_exclusion_points`、`uncertain_points`、`evidence_highlights` 都必須簡短且可對照輸入文字
- 不可發明新 criteria
- 不可回傳多個 JSON 物件
