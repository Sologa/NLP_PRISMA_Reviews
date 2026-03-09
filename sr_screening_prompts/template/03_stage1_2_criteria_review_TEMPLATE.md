# TEMPLATE Prompt 3 — Stage 1.2（用 criteria 對 Title + Abstract 抽取結果做初判：include / exclude / maybe）

> **Stage 1.2 = criteria review（General Template）**  
> 輸入：Stage 1.1（metadata）+ Stage 1.2（title/abstract 抽取）。  
> 輸出：include / exclude / maybe（三分類）+ 每條 criterion 的 YES/NO/UNCLEAR。

```text
我會提供你：
1) stage1_1_metadata_screening.jsonl
2) stage1_2_title_abstract_extraction.jsonl

你要用下列 SR criteria 做 Stage 1.2 初判。

================================================
【Stage 1.2 硬規則（務必逐字遵守）】
================================================
(1) 只要任一條 Exclusion == YES → verdict = EXCLUDE
(2) 只要任一條 Inclusion == NO → verdict = EXCLUDE
(3) 若沒有觸發 EXCLUDE，但任一條 criterion == UNCLEAR → verdict = MAYBE
(4) 只有在「所有 Inclusion == YES」且「所有 Exclusion == NO」時 → verdict = INCLUDE

================================================
【把你的 SR criteria 填在這裡（請用 YES/NO/UNCLEAR 評估）】
================================================
Inclusion（全部必須 YES）：
{{INCLUSION_CRITERIA}}

Exclusion（任一 YES 就排除）：
{{EXCLUSION_CRITERIA}}

可選（建議，若你的 evidence base 只想要 primary studies）：
- Exclusion: Secondary research（survey/review/scoping/mapping/meta-analysis/SoK/taxonomy/tutorial/roadmap/position/vision/perspective/commentary…）
  - 是否啟用：{{EXCLUDE_SECONDARY_RESEARCH}}（填 TRUE/FALSE）
  - 若你做的是 umbrella review/tertiary synthesis，請填 FALSE（避免衝突）。

================================================
【如何使用 Stage1.1 + Stage1.2 的抽取結果】
================================================
- 你必須對每條 criterion 輸出：
  - status: YES / NO / UNCLEAR
  - evidence: 引用 stage1.1 欄位值或 stage1.2 evidence_quotes
  - notes: 為何是 YES/NO/UNCLEAR

模板建議（若你的 SR 與 summarization/Transformer 類似，可參考）：
- 年份門檻：用 stage1.1 的 pub_ge_year_threshold
- 方法/架構：用 stage1.2 Q8（Transformer/模型名）
- 任務是否 summarization：用 Q1（output=summary）、Q1.4 關鍵字
- extractive vs abstractive：用 Q7
- multimodal：用 Q6（只在 title/abstract 明確說有 audio/image/video features 才 YES）
- dataset 語言：
  - 若你的 SR 有 “primary dataset language restriction”：
    - 請使用 Q4（未明說→依規則直接視為 {{DATASET_LANGUAGE_DEFAULT_IF_UNSPECIFIED}}，通常 English）
    - 僅在 title/abstract 明確寫 non-English/multilingual/cross-lingual/translation 且語境是 dataset 語言時，才把 exclusion 判 YES
- secondary research：
  - 用 Q0（title/abstract 的 survey/review/SoK/taxonomy/systematic… 訊號）
  - taxonomy 只有在 abstract 同時出現“綜整語氣”才可 YES；否則用 UNCLEAR（避免誤殺）

================================================
【輸出檔案】
================================================
- stage1_2_screening_decisions.jsonl
- stage1_2_screening_decisions.csv
- stage1_2_include_keys.txt / stage1_2_maybe_keys.txt / stage1_2_exclude_keys.txt

每筆至少包含：
- key
- criteria_status（每條 criterion: YES/NO/UNCLEAR + evidence）
- stage1_2_decision（include/exclude/maybe）
- exclude_reasons / maybe_reasons
- decision_reason（中文，可稽核）

回覆請給 summary（include/maybe/exclude 分布與最常見原因）。
```