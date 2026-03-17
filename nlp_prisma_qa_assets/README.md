# NLP_PRISMA current-state-aligned QA 資產包

這個資產包是依照 `docs/ChatGPT/next_experiments_criteria_mds_qa_deep_analysis_zh.md` 的建議直接落地出的第一輪可用資產。

## 這包資產做了什麼

1. 以 **current active** `criteria_stage1/` 與 `criteria_stage2/` 作為唯一 criteria source，
   為 `2409.13738` 與 `2511.13936` 各自重生兩份 stage-specific QA spec。
2. 把 metadata-only 規則與 screening QA 拆開，不再混在同一份 question set。
3. 定義一份最小可用的 `evidence_synthesis_schema` 與 `stage_handoff_object_schema`。
4. 提供每篇每階段的空白 evidence template，方便直接串 pipeline。
5. 補上一份三臂比較矩陣，對應 `baseline vs QA-only vs QA+synthesis`。

## 重要原則

- **沒有**把任何新的 operational hardening 寫回 formal criteria。
- `criteria_mds/` 只拿來學 question-set 的表達形式，不當 current production 規格來源。
- `2511` 的 2020+ / citation gate / arXiv gate **沒有**被帶進 current screening QA。
- `2409` 的 Stage 1 **沒有**提前引入 Stage 2 才該判的 metadata gate。
- 所有 QA spec 都是 **抽取型**：要求 quote + location，不直接做 include/exclude 決策。

## 目錄

- `specs/`
  - 四份 stage-specific QA spec（兩篇 paper × 兩個 stage）
- `metadata/`
  - 兩份 metadata filter spec
- `schemas/`
  - `evidence_synthesis_schema.json`
  - `stage_handoff_object_schema.json`
  - `criterion_traceability.csv`
- `templates/`
  - 四份 per-paper / per-stage evidence template
- `plans/`
  - `experiment_matrix.md`

## 建議使用順序

1. 先讀對應 paper / stage 的 `specs/*.md`
2. 再用 `templates/*.json` 初始化 extraction 輸出物件
3. 把 raw QA answers 正規化到 `schemas/evidence_synthesis_schema.json`
4. 最後按 `plans/experiment_matrix.md` 進行 baseline / QA-only / QA+synthesis 比較

## 對 current repo state 的對齊方式

- current active criteria: `criteria_stage1/*.json` + `criteria_stage2/*.json`
- `2409` / `2511` current score authority: `stage_split_criteria_migration`
- `criteria_jsons/*.json` 與舊 `criteria_mds/*.md` 均未被當成 current production criteria

## 備註

這包資產偏重「可直接拿來做實驗」的初版落地，因此內容上優先滿足：
- stage-specific
- extraction-first
- source-faithful
- traceable
- 可 handoff
