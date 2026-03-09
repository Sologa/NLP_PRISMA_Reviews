# Prompt 3 — Stage 1.2（Title+Abstract 直接 Criteria Review：逐條 1～5 分 + verdict=include/exclude/maybe）

> **Stage 1.2 = 只看 Title + Abstract，直接做 criteria review（允許 maybe）**  
> 注意：本版本沒有 Prompt 2（不做獨立 evidence extraction）。你必須在打分時同步把證據（quotes）抽出來。

```text
- 角色：SR Screening Reviewer（Stage 1.2 criteria review；title+abstract）單 agent
- 你會收到：
  1) `stage1_1_metadata_screening.jsonl`（Stage 1.1 輸出；含 key/title/abstract/eligible_for_stage1_2）
  （可選）2) `title_abstracts_metadata.jsonl`（原始 metadata；若 Stage1.1 內文缺 title/abstract 可用 key 回填）

- 你的任務：
  對每篇 `eligible_for_stage1_2=true` 的 paper，只用 title+abstract：
  1) 針對每條 criterion 打 1～5 分（並轉成 YES/NO/UNCLEAR）
  2) 套用硬規則輸出 Stage 1.2 verdict：include / exclude / maybe
  3) 產出可下載的 decision 檔（JSONL + CSV + key 清單）

- 限制（硬性）：
  1) 禁止上網；只能用提供的檔案內容。
  2) 只能用 `key` 做 join；禁止用 title 來 join。
  3) Stage 1.2 僅允許閱讀 **title + abstract**；不得讀 full text（fulltexts_text_only.zip 在 Stage 2 才能用）。
  4) 所有分數必須能回指到 evidence_quotes（title/abstract 的原文片段）或 Stage1.1 的欄位值；沒有證據就給 3（UNCLEAR），禁止臆測。
  5) 不要先假設「最後會有幾篇 include」；test-time 只能依現有資料判斷。

================================================
本 SR criteria（CADS 類型 + Secondary 排除）
================================================
Inclusion（全部必須 YES）
I1. Published in 2019 or later.            （來自 Stage1.1: pub_ge_2019）
I2. Transformer-based methods.
I3. In the context of summarization.

Exclusion（任一 YES 就排除）
E1. Non-English primary dataset.
E2. Multi-modal input (visual/audio as model input).
E3. Focus on extractive rather than abstractive summarization.
E4. Non-Transformer-based methods.
E5. Secondary research.

------------------------------------------------
重要預設/規則（用來降低“不確定”）
------------------------------------------------
(1) Dataset 語言預設（對應 E1）：
- 若 title/abstract 沒有明確寫 dataset/語言（English/Chinese/…），依 CADS 規則 **直接視為 English**。
- 只有在 title/abstract 明確指向非英文（例如 Chinese/Arabic/…、non-English、multilingual、cross-lingual、translation… 且語境是 dataset/corpus）時，才提高 E1 分數。

(2) Multi-modal（對應 E2）：
- 只有當 title/abstract 明確提到 audio/video/image/multimodal 且語境是「模型輸入」時，才提高 E2 分數。
- 若只看到 “speech transcript / ASR transcript” 等，且未提音訊特徵 → 不可直接判 multi-modal；通常給 3（UNCLEAR）或 1（NO）需看文字是否清楚。

(3) Secondary research（對應 E5）：
- 若 title/abstract 明確自稱 survey/review/systematic review/scoping/mapping/meta-analysis/SoK/tutorial/overview/roadmap/taxonomy/future directions 等「綜整既有工作」型態 → E5 高分。
- 若只有 “taxonomy” 但 abstract 沒有綜整語氣 → 不可直接當成 secondary；可給 3（UNCLEAR）。

================================================
分數 → 狀態（必須一致）
================================================
- Inclusion：4–5 => YES；1–2 => NO；3 => UNCLEAR
- Exclusion：4–5 => YES（觸發排除）；1–2 => NO；3 => UNCLEAR

================================================
Stage 1.2 硬規則（務必逐字遵守）
================================================
(1) 只要任一條 Exclusion.status == YES → verdict = EXCLUDE
(2) 只要任一條 Inclusion.status == NO → verdict = EXCLUDE
(3) 若未觸發 EXCLUDE，但任一條 criterion.status == UNCLEAR → verdict = MAYBE
(4) 只有在「所有 Inclusion.status == YES」且「所有 Exclusion.status == NO」時 → verdict = INCLUDE

================================================
你需要做的事（流程）
================================================
Step 0) 讀入 Stage 1.1 檔，取得 eligible keys
- 以 key 為主鍵
- 只處理 eligible_for_stage1_2=true 的 records

Step 1) 對每篇 paper，建立 Stage 1.2 的 evidence pack（只限 title+abstract）
- 你必須把每條 criterion 的 evidence_quotes 抽出來（1–3 段短 quote）
- quote 來源只能是 title 或 abstract；並記錄來源：title / abstract

Step 2) 逐條 criterion 打分（1–5）並給出 status
- I1：直接用 Stage1.1 的 pub_ge_2019（不用 quote）
- I2/I3/E2/E3/E4/E5：用 title/abstract 的 evidence_quotes
- E1：若未明說語言 → 依規則視為 English → E1_score=1（NO）並在 notes 註明「未明說→預設 English」
      若明確提 non-English/multilingual/translation 且語境是 dataset/corpus → 提高分數

Step 3) 套用硬規則輸出 verdict（include/exclude/maybe）
- 同時輸出 `exclude_reason_primary`：
  - 若因 Exclusion=YES 排除：列出觸發的 exclusion id（可多個）
  - 若因 Inclusion=NO 排除：列出不符合的 inclusion id

================================================
輸出（必須提供下載）
================================================
A) JSONL：`stage1_2_screening_decisions.jsonl`
- 一行一筆（只包含 eligible_for_stage1_2=true 的 papers）
- 每筆至少包含：
  - key
  - stage1_2_verdict: "include"|"exclude"|"maybe"
  - exclude_reason_primary: ["E2", ...] 或 ["I2", ...]
  - criteria_scores: 
      {
        "I1": {"score_1to5": int, "status": "YES|NO|UNCLEAR", "evidence_quotes": [], "evidence_source": "stage1_1"},
        "I2": {... "evidence_source": "title|abstract"},
        ...
        "E5": {...}
      }
  - decision_confidence_1to5（整體把握；不是逐條）
  - notes（可空）

B) CSV：`stage1_2_screening_decisions.csv`
- 至少包含：key, stage1_2_verdict, I1_score,I2_score,I3_score,E1_score,E2_score,E3_score,E4_score,E5_score, decision_confidence_1to5

C) key 清單：
- `stage1_2_include_keys.txt`
- `stage1_2_maybe_keys.txt`
- `stage1_2_exclude_keys.txt`

================================================
回覆文字（summary）
================================================
請在回覆中提供：
- eligible_for_stage1_2 的篇數
- stage1_2 include/exclude/maybe 各自數量
- 最常見的排除原因（E? 或 I?）前 5 名（按次數）
- 以及 `mapping_ambiguous=true`（若你需要用 title 做 debug） 的 key 清單

最後提供所有輸出檔案下載連結。
```