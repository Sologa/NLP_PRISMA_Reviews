# Prompt 3 — Stage 1.2（用 criteria 對 Title + Abstract 抽取結果做初判：include / exclude / maybe）

> **Stage 1.2 = criteria review（允許 maybe）**  
> 輸入：Stage 1.1（metadata prefilter）+ Stage 1.2（title/abstract 抽取）。  
> 輸出：include / exclude / maybe（三分類）+ 每條 criterion 的 YES/NO/UNCLEAR + 可稽核理由。

```text
我會提供你：
1) stage1_1_metadata_screening.jsonl
2) stage1_2_title_abstract_extraction.jsonl

你的任務：依下列 criteria，對每篇 eligible_for_stage1_2=true 的 paper 做 Stage 1.2 初判：
- 輸出 include / exclude / maybe
- 對每條 criterion 輸出 status：YES / NO / UNCLEAR
- 並寫可稽核理由（必須引用 Stage1.1 欄位值或 Stage1.2 的 evidence_quotes）

================================================
【Stage 1.2 的硬規則（務必逐字遵守）】
================================================
(1) 只要任一條 Exclusion == YES → verdict = EXCLUDE
(2) 只要任一條 Inclusion == NO → verdict = EXCLUDE
(3) 若沒有觸發 EXCLUDE，但任一條 criterion == UNCLEAR → verdict = MAYBE
(4) 只有在「所有 Inclusion == YES」且「所有 Exclusion == NO」時 → verdict = INCLUDE

================================================
【本 SR 的 criteria（CADS 類型 + 新增 secondary 排除）】
================================================
Inclusion（全部必須 YES）
I1. Published in 2019 or later.            （用 Stage1.1 的 pub_ge_2019）
I2. Transformer-based methods.             （看 title/abstract 的 backbone/Transformer 字樣）
I3. In the context of summarization.       （任務與 output=summary/minutes/highlights 等）

Exclusion（任一 YES 就排除）
E1. Non-English primary dataset.           （只在 title/abstract 有明確 non-English/multilingual 證據才 YES）
E2. Multi-modal (visual/audio) as input.   （title/abstract 明確提到用 audio/image/video features 才 YES）
E3. Focus on extractive summarization.     （title/abstract 明確自稱 extractive 或輸出=extracted spans 才 YES）
E4. Non-Transformer-based methods.         （title/abstract 明確說主要方法非 Transformer 才 YES）
E5. Secondary research.                    （survey/review/SoK/taxonomy/tutorial/roadmap/... 的強訊號才 YES）

注意：E5 是 evidence base=primary studies 的常見排除政策，即使原 SR 沒明寫，也常用於避免把 review/survey 當 primary study。

================================================
【如何用 Stage1.1 + Stage1.2 抽取結果判定每條 criterion】
================================================

I1（>=2019）
- 用 Stage1.1 的 pub_ge_2019：
  - true → YES
  - false → NO
  - null → UNCLEAR
- evidence：publication_year + pub_ge_2019_reason

I2（Transformer-based）
- 用 Stage1.2 的 Q8：
  - 若 title/abstract 明確寫 Transformer / Transformer-based / 或列出明確 Transformer backbone（BART/T5/PEGASUS/LED/Longformer/GPT...）→ YES
  - 若 title/abstract 明確表述主要方法是 RNN/LSTM/GRU/CNN 等非 Transformer → NO
  - 否則 → UNCLEAR
- evidence：Q8 的 quotes

I3（Summarization context）
- 用 Stage1.2 的 Q1（task/input/output）：
  - 若 output 明確是 summary/minutes/highlights 或明示 summarization → YES
  - 若 task/output 明確不是 summarization（例如 classification/retrieval/metric/dataset paper…）→ NO
  - 否則 → UNCLEAR
- evidence：Q1.1/Q1.3/Q1.4 + Q2.1（如有）

E4（Non-Transformer methods）
- 與 I2 互補，但仍要明確輸出：
  - 若 I2==NO → E4=YES
  - 若 I2==YES → E4=NO
  - 若 I2==UNCLEAR → E4=UNCLEAR

E3（Extractive focus）
- 用 Stage1.2 的 Q7：
  - 明確自稱 extractive 或輸出定義為 extracted utterances/sentences/spans → YES
  - 明確自稱 abstractive/generative/free-form summary → NO
  - 否則 → UNCLEAR
- evidence：Q7 quotes

E2（Multi-modal as input）
- 用 Stage1.2 的 Q6：
  - 只有在 title/abstract 明確說模型輸入包含 audio/image/video（例如 audio features / visual features / multimodal encoder 等）→ YES
  - 若只提到 transcript / text / dialogue logs，且未提 audio/image/video 特徵 → NO（title/abstract 階段通常只到 NO/UNCLEAR；這裡採保守但不亂排除）
  - 若有模糊字眼（例如只寫 multimodal 但不清楚是否作為模型輸入）→ UNCLEAR
- evidence：Q6 quotes

E1（Non-English primary dataset）
- Stage 1.2 只能用 title/abstract，通常難以判 primary dataset；本階段規則如下：
  - 若 title/abstract 明確寫 non-English / Chinese / Arabic / multilingual / cross-lingual / translation 且語境是 dataset/語料/評估語言 → YES
  - 若完全未提語言（依 Q4 規則：未明說→視為英文）→ NO（高確定度 not-triggered）
  - 若只有“可能暗示”字眼（如 dataset 名稱看起來像非英文，但 abstract 沒明說）→ NO（不要用名稱硬推論）；但可在 notes 記錄 hints
  - 若 abstract 同時提到 multilingual/translation 但不清楚是否 primary dataset → UNCLEAR
- evidence：Q4（language quotes or default English）+ Q9（multilingual terms）+ Q3（dataset mentions）

E5（Secondary research）
- 用 Stage1.2 的 Q0 + Q2：
  - 若 title 或 abstract **明確自述**：survey / review / systematic review / mapping / scoping / meta-analysis / SoK / tutorial / overview / roadmap / position/vision/perspective/opinion/commentary → YES
  - 若只有 “taxonomy” 字樣：
    - 若 abstract 同時出現綜整語氣（we review/systematize existing work / comprehensive overview / future directions）→ YES
    - 否則 → UNCLEAR（不要僅憑 taxonomy 一詞就 YES）
  - 若完全沒有 secondary 訊號 → NO
- evidence：Q0.1/Q0.2/Q0.3 quotes（必要時也可引用 Q2 中出現 survey/overview 等詞的片段）

================================================
【輸出檔案（請提供下載）】
================================================
A) JSONL：`stage1_2_screening_decisions.jsonl`
- 一行一筆（只需包含 eligible_for_stage1_2=true 的 keys）
- 每筆至少包含：
  - key
  - stage1_1_decision（帶過來）
  - criteria_status：
    * I1/I2/I3/E1/E2/E3/E4/E5：{status:"YES|NO|UNCLEAR", evidence:[...], notes:"..."}
  - stage1_2_decision：include/exclude/maybe
  - exclude_reasons：若 exclude，列出觸發的條件（例如 ["E5","I2"]）
  - maybe_reasons：若 maybe，列出 UNCLEAR 的條件 key
  - decision_confidence_1to5：1–5（可選；**是對整體判定把握**，不是對單條 criterion）
  - decision_reason：中文，必須引用 evidence（Stage1.1 欄位值或 Stage1.2 quotes）

B) CSV：`stage1_2_screening_decisions.csv`
- 至少包含：key, stage1_2_decision, I1,I2,I3,E1,E2,E3,E4,E5, exclude_reasons, maybe_reasons, decision_confidence_1to5, decision_reason（可略縮）

C) Key 清單（供 Stage 2 用）
- `stage1_2_include_keys.txt`
- `stage1_2_maybe_keys.txt`
- `stage1_2_exclude_keys.txt`

【回覆中請給 summary】
- include/maybe/exclude 各多少
- 最常見的 exclude 原因（列前 5）
- maybe 最常見來自哪些 UNCLEAR criterion
並提供所有輸出檔案下載連結。
```