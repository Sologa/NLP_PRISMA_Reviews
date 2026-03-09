# Prompt 5 — Stage 2（Final Criteria Review on Full Text：逐條 1～5 分 + final verdict=include/exclude）

> **Stage 2 = 讀 Full text，直接做最終 criteria review（不允許 maybe）**  
> 注意：本版本沒有 Prompt 4（不做獨立 evidence extraction）。你必須在打分時同步把證據（quotes）抽出來。

```text
- 角色：SR Screening Reviewer（Stage 2 final criteria review；full text）單 agent

- 你會收到：
  1) `stage1_1_metadata_screening.jsonl`
  2) `stage1_2_screening_decisions.jsonl`
  3) `fulltexts_text_only.zip`（多篇 paper 的全文 md）

- 你的任務：
  只針對 Stage 1.2 verdict 為 include 或 maybe 的 keys：
  1) 讀取 full text（md）
  2) 依 SR criteria 逐條打 1～5 分（並轉 YES/NO/UNCLEAR）
  3) 套用硬規則輸出最終 verdict：include / exclude（Stage 2 不允許 maybe）
  4) 產出可下載的最終 decision 檔（JSONL + CSV + key 清單）

- 限制（硬性）：
  1) 禁止上網；只能用提供檔案。
  2) 只能用 key 做 join。
  3) 每條 criterion 的分數都必須引用 evidence_quotes（full text 原文片段；必要時可補引用 title/abstract）。
  4) Stage 2 不允許 maybe：若任何 criterion = UNCLEAR（score=3）→ 必須保守排除並標 needs_manual_review=true。
  5) 不要先假設最後 include 幾篇；test-time 只能依提供資料判斷。

================================================
本 SR criteria（CADS 類型 + Secondary 排除）
================================================
Inclusion（全部必須 YES）
I1. Published in 2019 or later.            （Stage1.1: pub_ge_2019）
I2. Transformer-based methods.
I3. In the context of summarization.

Exclusion（任一 YES 就排除）
E1. Non-English primary dataset.
E2. Multi-modal input (visual/audio as model input).
E3. Focus on extractive rather than abstractive summarization.
E4. Non-Transformer-based methods.
E5. Secondary research.

------------------------------------------------
Dataset 語言預設（對應 E1；在 Stage 2 也要遵守）
------------------------------------------------
- 若全文沒有明確寫 dataset/corpus 語言：依規則 **直接視為 English**（E1_score=1，NO）
- 只有在全文明確寫 non-English / Chinese / Arabic / multilingual / cross-lingual / translation，
  且語境是 dataset/corpus 或主要評估資料，才提高 E1 分數。

================================================
分數 → 狀態（必須一致）
================================================
- Inclusion：4–5 => YES；1–2 => NO；3 => UNCLEAR
- Exclusion：4–5 => YES（觸發排除）；1–2 => NO；3 => UNCLEAR

================================================
Stage 2 硬規則（務必逐字遵守）
================================================
(1) 只要任一條 Exclusion.status == YES → final_verdict = EXCLUDE
(2) 只要任一條 Inclusion.status == NO → final_verdict = EXCLUDE
(3) Stage 2 不允許 MAYBE：
    - 若未觸發 EXCLUDE，但任一條 criterion.status == UNCLEAR → final_verdict = EXCLUDE 且 needs_manual_review=true
(4) 只有在「所有 Inclusion.status == YES」且「所有 Exclusion.status == NO」時 → final_verdict = INCLUDE

================================================
你需要做的事（流程）
================================================
Step 0) 取得 Stage 2 待審 keys
- 從 `stage1_2_screening_decisions.jsonl` 選出 stage1_2_verdict in {include, maybe}

Step 1) 在 fulltexts_text_only.zip 中找到對應 md
- 最優先：檔名（去掉副檔名）== key
- 若找不到：在 md 內文開頭尋找可定位資訊（如 Bibkey/ID/Title）
- 若仍無法對應：標記 `fulltext_missing_or_unmatched=true`，並直接輸出 final_verdict=EXCLUDE + needs_manual_review=true（因為無法完成 Stage 2）

Step 2) 逐條 criterion 打分（1～5）+ evidence_quotes
- I1：直接引用 Stage1.1 的 pub_ge_2019（不用 quote）
- I2（Transformer-based）：
  - 找模型/架構描述（如 Transformer/BART/T5/PEGASUS/Longformer/LED/GPT/encoder-decoder）
  - 若主要方法明確是 RNN/LSTM/非 Transformer → I2 低分，且 E4 高分
- I3（Summarization）：
  - 找 task/goal/output 定義（summary/minutes/highlights/summarization）
- E3（Extractive focus）：
  - 找 “extractive/abstractive/hybrid/generative” 自述或輸出定義/例子
- E2（Multi-modal input）：
  - 只看「模型輸入」是否包含 audio/image/video features；若只用 transcript 文字需引用原文支持
- E1（Non-English primary dataset）：
  - 若全文明確指出主要 dataset/corpus 語言為非英文 → E1 高分
  - 若未明說 → 依規則視為 English → E1=1（NO），並在 notes 註明
- E5（Secondary research）：
  - 看是否自稱 survey/review/systematic review/scoping/mapping/meta-analysis/SoK/tutorial/overview/roadmap 等
  - 或是否描述文獻檢索/篩選/inclusion-exclusion/PRISMA flow（secondary 的強訊號）

Step 3) 套用 Stage 2 硬規則輸出 final verdict（include/exclude）
- 並輸出：
  - `exclude_reason_primary`：觸發的 exclusion id 或不符合的 inclusion id
  - `needs_manual_review`：若任何 criterion=UNCLEAR 或 fulltext 缺失/對不上 key，則 true

================================================
輸出（必須提供下載）
================================================
A) JSONL：`stage2_final_decisions.jsonl`
- 一行一筆（只包含 stage1_2_verdict in {include, maybe} 的 keys）
- 每筆至少包含：
  - key
  - stage1_2_verdict
  - final_verdict: "include"|"exclude"
  - needs_manual_review: true/false
  - exclude_reason_primary: ["E2", ...] 或 ["I2", ...]
  - criteria_scores（同 Prompt 3 的格式；但 evidence_quotes 主要來自 fulltext）
  - decision_confidence_1to5（整體把握；不是逐條）
  - fulltext_file（對應到哪個 md 檔）
  - fulltext_missing_or_unmatched（true/false）
  - notes

B) CSV：`stage2_final_decisions.csv`
- 至少包含：key, final_verdict, needs_manual_review, I1_score,I2_score,I3_score,E1_score,E2_score,E3_score,E4_score,E5_score, decision_confidence_1to5

C) key 清單：
- `final_include_keys.txt`
- `final_exclude_keys.txt`

================================================
回覆文字（summary）
================================================
請在回覆中提供：
- Stage 2 審查篇數（從 Stage1.2 include/maybe 來的）
- final include/exclude 各自數量
- needs_manual_review 的數量與 key 清單（若太多，只列前 50；完整另存檔）
- 最常見的排除原因前 5 名（按次數）
並提供所有輸出檔案下載連結。
```