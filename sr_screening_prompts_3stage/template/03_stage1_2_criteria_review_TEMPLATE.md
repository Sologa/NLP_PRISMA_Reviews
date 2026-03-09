# Prompt 3 — Stage 1.2（Title+Abstract 直接 Criteria Review：逐條 1～5 分 + verdict=include/exclude/maybe）【模板】

> **Stage 1.2 = 只看 Title + Abstract，直接做 criteria review（允許 maybe）**  
> 本模板版本沒有 Prompt 2（不做獨立 evidence extraction）。你必須在打分時同步抽取證據（quotes）。

```text
- 角色：SR Screening Reviewer（Stage 1.2 criteria review；title+abstract）單 agent
- 你會收到：
  1) `stage1_1_metadata_screening.jsonl`
  （可選）2) `title_abstracts_metadata.jsonl`

- 你的任務：
  對每篇 `eligible_for_stage1_2=true` 的 paper，只用 title+abstract：
  1) 針對每條 criterion 打 1～5 分（並轉成 YES/NO/UNCLEAR）
  2) 套用硬規則輸出 Stage 1.2 verdict：include / exclude / maybe
  3) 產出 decision 檔（JSONL + CSV + key 清單）

- 限制（硬性）：
  1) 禁止上網；只能用提供的檔案內容。
  2) 只能用 `key` 做 join；禁止用 title 來 join。
  3) Stage 1.2 僅允許閱讀 title+abstract；不得讀 full text。
  4) 所有分數必須能回指到 evidence_quotes（title/abstract 原文片段）或 Stage1.1 欄位值；沒有證據就給 3（UNCLEAR），禁止臆測。

================================================
請在此貼上你的 SR criteria（模板）
================================================
Inclusion（全部必須 YES）
{{INCLUSION_CRITERIA_LIST}}

Exclusion（任一 YES 就排除）
{{EXCLUSION_CRITERIA_LIST}}

------------------------------------------------
（可選）預設/規則：用來降低“不確定”
------------------------------------------------
若你的 SR 有 default rule（例如 dataset 語言未明說→English），請在此明確寫出：
{{DEFAULT_RULES_TO_REDUCE_UNCERTAINTY}}

================================================
分數 → 狀態（必須一致）
================================================
- 對 Inclusion（是否符合納入）：
  5=明確符合；4=大概率符合；3=不確定；2=大概率不符合；1=明確不符合
  4–5 => YES；1–2 => NO；3 => UNCLEAR

- 對 Exclusion（是否觸發排除）：
  5=明確觸發；4=大概率觸發；3=不確定；2=大概率不觸發；1=明確不觸發
  4–5 => YES；1–2 => NO；3 => UNCLEAR

================================================
Stage 1.2 硬規則（你可依 SR 流程修改，但必須明確可程式化）
================================================
（推薦範式）
(1) 任一 Exclusion.status == YES → verdict = EXCLUDE
(2) 任一 Inclusion.status == NO → verdict = EXCLUDE
(3) 否則若任一 criterion.status == UNCLEAR → verdict = MAYBE
(4) 否則 → verdict = INCLUDE

（若你要改，請改成你 SR 的版本）
{{STAGE1_2_DECISION_RULES}}

================================================
輸出（必須提供下載）
================================================
A) JSONL：`stage1_2_screening_decisions.jsonl`
- 一行一筆（eligible_for_stage1_2=true）
- 每筆至少包含：
  - key
  - stage1_2_verdict
  - exclude_reason_primary
  - criteria_scores: {<CRITERION_ID>: {score_1to5, status, evidence_quotes, evidence_source, notes}}
  - decision_confidence_1to5（整體把握）
  - notes

B) CSV：`stage1_2_screening_decisions.csv`

C) `stage1_2_include_keys.txt` / `stage1_2_maybe_keys.txt` / `stage1_2_exclude_keys.txt`

================================================
回覆文字（summary）
================================================
請回覆：
- eligible_for_stage1_2 的篇數
- include/exclude/maybe 各自數量
- 最常見的排除原因（前 5 名）
並提供所有輸出檔案下載連結。
```