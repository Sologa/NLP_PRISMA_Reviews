# 單審查者官方 Batch 兩階段直審：Stage 2

你正在執行 experiment-only 的 `{{WORKFLOW_ARM}}`。

## 不可違反的約束

- current production runtime prompts 仍是：`scripts/screening/runtime_prompts/runtime_prompts.json`
- 這個實驗不修改 production runtime path，也不沿用 preserved-workflow
- Stage 2 只使用 `criteria_stage2/<paper_id>.json`
- 只能根據提供的 title、abstract、full text、metadata 與 Stage 2 criteria JSON 判斷
- `PRIOR_STAGE_REVIEW_JSON` 只是 handoff context；Stage 2 必須依 Stage 2 criteria 與全文證據重新下判斷
- 不可使用外部知識、常識補完、作者名聲、venue 名聲或模型家族印象
- 如果必要條件沒有被全文明確文字支持，不可自行假設成立

## 審查目標

- `paper_id`: `{{PAPER_ID}}`
- `candidate_key`: `{{CANDIDATE_KEY}}`
- `candidate_title`: `{{CANDIDATE_TITLE}}`
- `workflow_arm`: `{{WORKFLOW_ARM}}`
- `stage`: `stage2`

## Stage 2 Criteria JSON

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

### Prior Stage Review
```json
{{PRIOR_STAGE_REVIEW_JSON}}
```

### Fulltext Resolution
```json
{{FULLTEXT_RESOLUTION_JSON}}
```

### Title
```text
{{TITLE}}
```

### Abstract
```text
{{ABSTRACT}}
```

### Full Text
```text
{{FULLTEXT_TEXT}}
```

## 任務

請回傳一個 Stage 2 reviewer 的 JSON 物件。

評分規則：

- `1` = 強排除
- `2` = 偏排除
- `3` = 證據不足、混合或不確定
- `4` = 偏納入
- `5` = 強納入

判斷規則：

- 只有在 Stage 2 納入條件被全文明確正向支持時，才可給 `4` 或 `5`
- 當排除條件成立，或必要納入條件被全文明確否定時，給 `1` 或 `2`
- 全文仍不足以支撐明確納排時，給 `3`
- 每個判斷都必須可追溯到 title/abstract/full text 文字

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
