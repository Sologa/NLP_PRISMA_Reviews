# TEMPLATE Prompt 5 — Stage 2（用 criteria 對 Full Text 抽取結果做最終判定：include / exclude）

> **Stage 2 = final decision（General Template；不允許 maybe）**  
> 輸入：Stage 1.1 + Stage 1.2 decision + Stage 2 full-text extraction  
> 輸出：include/exclude（二分類）+ 每條 criterion YES/NO/UNCLEAR。  
> 若仍 UNCLEAR：採保守策略 → EXCLUDE 並標 needs_manual_review=true。

```text
我會提供你：
1) stage1_1_metadata_screening.jsonl
2) stage1_2_screening_decisions.jsonl
3) stage2_fulltext_extraction.jsonl

================================================
【Stage 2 硬規則（務必逐字遵守）】
================================================
(1) 任一 Exclusion == YES → EXCLUDE
(2) 任一 Inclusion == NO → EXCLUDE
(3) Stage 2 不允許 MAYBE：
    - 若仍有任何 criterion == UNCLEAR → EXCLUDE，並 needs_manual_review=true
(4) 只有所有 Inclusion==YES 且所有 Exclusion==NO → INCLUDE

================================================
【把你的 SR criteria 填在這裡】
================================================
Inclusion（全部必須 YES）：
{{INCLUSION_CRITERIA}}

Exclusion（任一 YES 就排除）：
{{EXCLUSION_CRITERIA}}

可選（若 evidence base=primary studies，建議啟用）：
- Exclusion: Secondary research（survey/review/scoping/mapping/meta-analysis/SoK/taxonomy/tutorial/roadmap/position/vision/perspective/commentary…）
  - 是否啟用：{{EXCLUDE_SECONDARY_RESEARCH}}（TRUE/FALSE）

================================================
【如何判定（只用 Stage1/Stage2 抽取到的 evidence）】
================================================
- 逐條 criterion 輸出 status YES/NO/UNCLEAR + evidence_quotes。
- dataset language restriction 若存在：
  - 未明說語言 → 依規則直接視為 {{DATASET_LANGUAGE_DEFAULT_IF_UNSPECIFIED}}（通常 English），不要用不確定語氣。
- multimodal：以“模型輸入模態”為準（transcript-only 不算 multimodal input）。
- secondary research：以 Q0 的 self-identification + PRISMA/screening/inclusion-exclusion 流程等為強訊號。

================================================
【輸出】
================================================
- stage2_final_decisions.jsonl
- stage2_final_decisions.csv
- stage2_include_keys.txt / stage2_exclude_keys.txt

每筆至少包含：
- key
- final_decision
- needs_manual_review
- criteria_status（每條 YES/NO/UNCLEAR + evidence）
- exclude_reasons
- decision_reason（中文，可稽核）

回覆請給 summary（include/exclude 分布、needs_manual_review keys、最常見排除原因）。
```