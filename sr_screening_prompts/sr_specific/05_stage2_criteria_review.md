# Prompt 5 — Stage 2（用 criteria 對 Full Text 抽取結果做最終判定：include / exclude）

> **Stage 2 = final decision（不允許 maybe）**  
> 輸入：Stage 1.1 + Stage 1.2（decision）+ Stage 2（full text 抽取）。  
> 輸出：include / exclude（二分類）+ 每條 criterion 的 YES/NO/UNCLEAR + 可稽核理由。  
> 若仍 UNCLEAR：採保守策略 → EXCLUDE，並標 `needs_manual_review=true`。

```text
我會提供你：
1) stage1_1_metadata_screening.jsonl
2) stage1_2_screening_decisions.jsonl
3) stage2_fulltext_extraction.jsonl

你的任務：只針對 Stage 1.2 決策為 include 或 maybe 的 keys，
依下列 criteria 做 Stage 2 最終判定（include/exclude）：

================================================
【Stage 2 的硬規則（務必逐字遵守）】
================================================
(1) 只要任一條 Exclusion == YES → verdict = EXCLUDE
(2) 只要任一條 Inclusion == NO → verdict = EXCLUDE
(3) Stage 2 不允許 MAYBE：
    - 若沒有觸發 (1)(2)，但任一條 criterion == UNCLEAR → verdict = EXCLUDE，並 `needs_manual_review=true`
(4) 只有在「所有 Inclusion == YES」且「所有 Exclusion == NO」時 → verdict = INCLUDE

================================================
【本 SR 的 criteria（CADS 類型 + Secondary 排除）】
================================================
Inclusion（全部必須 YES）
I1. Published in 2019 or later.
I2. Transformer-based methods.
I3. In the context of summarization（主要任務/輸出是 summarization）。

Exclusion（任一 YES 就排除）
E1. Non-English primary dataset.
E2. Multi-modal studies incorporating visual or audio elements as model input.
E3. Focus on extractive rather than abstractive summarization.
E4. Non-Transformer-based methods.
E5. Secondary research（survey/review/systematic mapping/scoping/meta-analysis/SoK/taxonomy/tutorial/roadmap/position/vision/...）

================================================
【如何用 Stage1.1/Stage1.2/Stage2 抽取結果判定 criteria】
================================================

先做“繼承規則”：
- 若 stage1_1_decision=="exclude" 或 stage1_2_decision=="exclude"：本階段直接 final_decision="exclude"（並寫明是前序已排除）。
  （不需要再算所有 criterion，但仍可填 criteria_status 為 null 並寫 reason。）

I1（>=2019）
- 用 Stage1.1 pub_ge_2019：
  - true → YES
  - false → NO
  - null → UNCLEAR

I2（Transformer-based）
- 用 Stage2-Q8：
  - 若 paper 明確寫 Transformer-based / Transformer architecture / encoder-decoder Transformer / decoder-only，或主要 backbone 明確為 Transformer 家族（BART/T5/PEGASUS/LED/Longformer/GPT...）→ YES
  - 若 paper 明確以非 Transformer 作為主要方法（RNN/LSTM/GRU/CNN/graph model… 且非只是 baseline）→ NO
  - 否則 → UNCLEAR
- 同時更新 E4（互補）：
  - I2==NO → E4=YES
  - I2==YES → E4=NO
  - I2==UNCLEAR → E4=UNCLEAR

I3（Summarization）
- 用 Stage2-Q1（任務/輸出定義）：
  - output 明確是 summary/minutes/highlights 或明示 summarization → YES
  - 明確不是 summarization → NO
  - 否則 → UNCLEAR

E3（Extractive focus）
- 只在 I3==YES 時評估：
  - 若 Stage2-Q7 明確自稱 extractive，或輸出定義為 extracted utterances/sentences/spans → YES
  - 若明確自稱 abstractive/generative/free-form summary → NO
  - 若未明說但 output example/輸出格式可判定 → 依原文決定 YES/NO
  - 仍無法判定 → UNCLEAR

E2（Multi-modal as model input）
- 用 Stage2-Q6（以“模型輸入模態”為準）：
  - 若模型輸入包含 audio features / spectrogram / MFCC / prosody，或包含 image/video features / vision encoder outputs → YES
  - 若只用 ASR transcript / text transcript，且有原文支持 “transcripts only” → NO
  - 若 dataset 含影音但 paper 明確只用文字部分 → NO
  - 否則 → UNCLEAR

E1（Non-English primary dataset）
- 用 Stage2-Q3/Q4/Q5（注意：規則強化：未明說語言 → 直接視為英文）：
  1) 先用 Q5 的 signals 選出 `primary_dataset_candidate`（可多個並列，但必須引用信號：main/primary 語句、abstract 指名、主要結果表出現次數等）
  2) 再用 Q4 的語言資訊判定：
     - 若 primary_dataset_candidate 的語言明確非英文（Chinese/Arabic/...）或明確寫 multilingual/cross-lingual/non-English 且語境是 primary dataset → E1=YES
     - 若 paper 沒有明確寫語言（依 Q4 規則默認英文），且全文也未明示 non-English/multilingual/cross-lingual 作為 dataset 語言 → E1=NO（高確定度）
     - 若 paper 明確談 multilingual/cross-lingual/translation，但無法釐清 primary dataset 語言 → E1=UNCLEAR
  3) 若完全選不出 primary_dataset_candidate：
     - 不要因為“選不出 primary”就把 E1 當 YES
     - 只有在明確證據指向 non-English dataset 時才 YES；否則 NO 或 UNCLEAR（依是否提到 multilingual/translation）

E5（Secondary research）
- 用 Stage2-Q0 + Q2（作者自述）：
  - 若 paper 自稱 survey/review/systematic review/scoping/mapping/meta-analysis/SoK/tutorial/overview/roadmap/position/vision/perspective/opinion/commentary → YES
  - 若 paper 出現 evidence synthesis 方法學線索（PRISMA、database search、screening、inclusion/exclusion criteria、flow diagram…）→ YES
  - 若 paper 只有 taxonomy 字眼，但全文大量是整理既有方法、提出 taxonomy、future directions（非提出 primary empirical study）→ YES
  - 若完全無此類訊號 → NO
  - 若訊號矛盾或不足（少見）→ UNCLEAR
（注意：就算 paper 同時釋出 dataset/benchmark/metric，若整體仍是綜整型 secondary research，E5 仍可為 YES；但你只依 paper 自述與方法描述下結論。）

================================================
【輸出檔案（請提供下載）】
================================================
A) JSONL：`stage2_final_decisions.jsonl`
- 一行一筆（只包含 Stage1.2 include/maybe 的 keys）
- 每筆至少包含：
  - key
  - final_decision: "include" / "exclude"
  - needs_manual_review: true/false（若任何 criterion==UNCLEAR 且因此被保守排除 → true）
  - criteria_status：
    * I1/I2/I3/E1/E2/E3/E4/E5：{status:"YES|NO|UNCLEAR", evidence:[...], notes:"..."}
  - primary_dataset_candidate：[...]
  - exclude_reasons：若 exclude，列出觸發的條件（E 或 I）
  - decision_confidence_1to5：1–5（可選；整體把握，不是逐條打分）
  - decision_reason：中文，逐條交代 I 與 E 的狀態與最關鍵 evidence quote

B) CSV：`stage2_final_decisions.csv`
- 至少包含：key, final_decision, needs_manual_review, I1,I2,I3,E1,E2,E3,E4,E5, primary_dataset_candidate, exclude_reasons, decision_reason（可略縮）

C) Key 清單：
- `stage2_include_keys.txt`
- `stage2_exclude_keys.txt`

【回覆中請給 summary】
- include / exclude 各多少
- needs_manual_review=true 的數量與 key 清單
- 最常見的 exclude 觸發原因（I 不滿足 or 哪個 E==YES / UNCLEAR）
並提供所有輸出檔案下載連結。
```