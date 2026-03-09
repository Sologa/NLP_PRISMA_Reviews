# Prompt 5 — Stage 2（Final Criteria Review on Full Text：逐條 1～5 分 + final verdict=include/exclude）【模板】

> **Stage 2 = 讀 Full text，做最終 criteria review（不允許 maybe）**  
> 本模板版本沒有 Prompt 4（不做獨立 evidence extraction）。你必須在打分時同步抽取證據（quotes）。

```text
- 角色：SR Screening Reviewer（Stage 2 final criteria review；full text）單 agent
- 你會收到：
  1) `stage1_1_metadata_screening.jsonl`
  2) `stage1_2_screening_decisions.jsonl`
  3) `fulltexts_text_only.zip`

- 你的任務：
  只針對 Stage 1.2 verdict in {include, maybe} 的 papers：
  1) 讀取 full text（md）
  2) 依 SR criteria 逐條打 1～5 分（並轉 YES/NO/UNCLEAR）
  3) 套用硬規則輸出最終 verdict：include / exclude
  4) 輸出可下載檔案

- 限制（硬性）：
  1) 禁止上網
  2) 只能用 key 做 join
  3) 每條 criterion 分數都必須引用 full text 的 evidence_quotes（必要時可補引用 title/abstract）
  4) Stage 2 不允許 maybe：若任何 criterion == UNCLEAR → 必須保守排除並標 needs_manual_review=true

================================================
請在此貼上你的 SR criteria（模板）
================================================
Inclusion（全部必須 YES）
{{INCLUSION_CRITERIA_LIST}}

Exclusion（任一 YES 就排除）
{{EXCLUSION_CRITERIA_LIST}}

（可選）default rule（例如 dataset 語言未明說→English）：
{{DEFAULT_RULES_TO_REDUCE_UNCERTAINTY}}

================================================
分數 → 狀態（必須一致）
================================================
- Inclusion：4–5 => YES；1–2 => NO；3 => UNCLEAR
- Exclusion：4–5 => YES；1–2 => NO；3 => UNCLEAR

================================================
Stage 2 硬規則（必須明確可程式化）
================================================
（推薦範式）
(1) 任一 Exclusion.status == YES → final_verdict = EXCLUDE
(2) 任一 Inclusion.status == NO → final_verdict = EXCLUDE
(3) Stage2 不允許 MAYBE：若任一 criterion.status == UNCLEAR → final_verdict = EXCLUDE + needs_manual_review=true
(4) 否則 → final_verdict = INCLUDE

（若你要改，請改成你 SR 的版本）
{{STAGE2_DECISION_RULES}}

================================================
輸出（必須提供下載）
================================================
A) JSONL：`stage2_final_decisions.jsonl`
- 一行一筆（只包含 stage1_2_verdict in {include, maybe}）
- 每筆至少包含：
  - key
  - stage1_2_verdict
  - final_verdict
  - needs_manual_review
  - exclude_reason_primary
  - criteria_scores: {<CRITERION_ID>: {score_1to5, status, evidence_quotes, evidence_source, notes}}
  - decision_confidence_1to5（整體把握）
  - fulltext_file / fulltext_missing_or_unmatched
  - notes

B) CSV：`stage2_final_decisions.csv`

C) `final_include_keys.txt` / `final_exclude_keys.txt`

================================================
回覆文字（summary）
================================================
請回覆：
- Stage2 審查篇數
- final include/exclude 各自數量
- needs_manual_review 數量與 key 清單（若太多只列前 50；完整另存）
- 最常見排除原因前 5 名
並提供所有輸出檔案下載連結。
```