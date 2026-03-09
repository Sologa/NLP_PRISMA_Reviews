# Prompt 4 — Stage 2（讀 Full Text 的資訊抽取；**禁止**做 include/exclude 判定）

> **Stage 2 = full-text 抽取（不判定）**  
> 你只對 Stage 1.2 判定為 include/maybe 的 papers 讀 full text。  
> 這一步仍然 **只做資訊抽取**（Q0–Q10），不做 include/exclude 最終判定。

```text
我會提供你：
1) stage1_2_screening_decisions.jsonl   （Stage 1.2 的 include/maybe/exclude 結果）
2) fulltexts_text_only.zip               （254 篇 paper 的全文 md）
（可選）3) stage1_1_metadata_screening.jsonl（若你想保留 metadata 欄位，但 join 仍只能用 key）

你的任務：只針對 Stage 1.2 決策為 include 或 maybe 的 keys，
讀取 fulltexts_text_only.zip 中對應的 md 全文，並完成 Q0–Q10 的「全文級資訊抽取」。
嚴格禁止做 include/exclude/pass/fail 的最終判定；你只能抽取、定位、摘錄原文。答案允許不確定，但必須說明是因為 paper 沒寫或你找不到明示句。

【硬性要求】
A) 以 key（bibkey）做唯一索引；檔名若不等於 key，必須記錄 mapping 規則與是否 ambiguous。
B) 可用程式做：解壓縮、列檔、搜尋 Table/Figure/Section 位置、輸出 JSONL/CSV、統計 table 數量。
C) 不可用程式做：自動關鍵詞分類後直接下結論。你必須閱讀並摘錄原文作證。
D) 每個 Q 的輸出都要包含：
   - answer（結構化）
   - evidence_quotes（至少 1 段原文；若未提及則空陣列）
   - evidence_location（例如 Abstract / Introduction / Section 2 / Experiments / Table 1 / Appendix ...）

================================================
Q0. Secondary research signals（全文版；只抽取不判定）
================================================
你要從全文抽取能判斷 paper 是否屬於 secondary research 的“可觀測證據”，但你不能下 verdict。

Q0.1 Self-identification（作者是否自稱綜整研究？）
- 摘錄 paper 自稱 survey/review/systematic review/scoping/mapping/meta-analysis/SoK/tutorial/overview/taxonomy/roadmap/position/vision/perspective/opinion/commentary 的句子（若有）。
- 若未提及，回答 "未提及"。

Q0.2 Evidence synthesis methodology signals（若有，通常很強）
- 是否出現：PRISMA、database search、search strings/queries、screening、study selection、inclusion criteria、exclusion criteria、quality assessment、flow diagram、systematic mapping protocol…？
- 有則逐項摘錄原文 + 位置（通常在 Method/Appendix）；無則 "未提及"。

Q0.3 “Taxonomy/SoK” 類綜整語氣
- 若 paper 有 taxonomy / systematization / categorize existing approaches / comprehensive overview / future directions/open challenges 等敘述：
  - 摘錄 1–3 段原文，並標位置（Intro/Related Work/Conclusion 等）

Q0.4 兼具資源釋出（仍然只抽取）
- 若 paper 同時提出 dataset/benchmark/metric/evaluation protocol：摘錄作者自述 “we release/provide a dataset/benchmark/metric…” 的句子（這不代表不是 secondary；你只負責抽取）

================================================
Q1–Q10（依你先前定義；全文抽取）
================================================
Q1 任務定義
- (1) 任務/問題設定一句原文（Abstract/Introduction/Task Definition）
- (2) Input 描述原文（dialogue transcript / multi-party conversation / meeting / chat ...）
- (3) Output 描述原文（summary/minutes/highlights ...）
- (4) 是否明示 dialogue/conversation/meeting summarization 字樣？列出關鍵字 + 段落/小節名

Q2 作者自述主要貢獻（只摘錄，不分類、不下結論）
- (1) Abstract 中 contribution 句（we propose/introduce/present...）
- (2) 若明示 dataset/benchmark/metric/evaluation/survey/analysis/model/framework 等詞：逐一列出原文片段（可多段）+ 位置

Q3 datasets（只列舉與定位，不判定 primary）
- (1) 列出所有 dataset 名稱（含縮寫/全名）+ 出現位置（Abstract/Experiments/Table/Figure/Appendix）
- (2) 每個 dataset 的用途：training/validation/test/evaluation/case study/human eval data（用原文支持）
- (3) 若有主要結果表：列出每張主要表用到哪些 dataset（表號 + dataset）

Q4 dataset 語言（規則強化：未明說 → 直接視為英文）
- (1) 對每個 dataset：若 paper 明確寫語言，摘錄原文
- (2) 若沒寫語言：直接回答「英文」（不要加不確定語氣），並標記是 default rule
- (3) 仍要額外摘錄所有可能暗示非英文/多語的字眼（dataset 名稱含 Chinese/... 或 multilingual/cross-lingual/translation 段落），只摘錄不推論

Q5 primary dataset 可觀測信號（只提供信號，後續 prompt 才決策）
- (1) 是否出現 primary/main/we mainly evaluate on...？摘錄
- (2) Abstract 是否提到特定 dataset 用於 evaluation？摘錄 + dataset 名稱
- (3) 統計：每個 dataset 出現在多少張「主要結果表」中（只要數字）
- (4) 若 paper 是 metric/evaluation 類：列出 metric/eval → datasets 的對應（原文支持）

Q6 多模態（只抽取 input modality，不下 multi-modal 結論）
- (1) 列出輸入模態 text/audio/image/video/other（逐項附原文）
- (2) audio：是否用音訊特徵作輸入？摘錄；若只用 transcript，摘錄並明確寫「僅使用文字轉錄」
- (3) image/video：是否用視覺特徵作輸入？摘錄；若輸入仍是文字，摘錄並明確寫「輸入仍為文字」
- (4) dataset 含影音但只用文字部分：摘錄支持句

Q7 摘要型態（extractive/abstractive/hybrid：只取作者自述與輸出定義）
- (1) 是否明確自稱 extractive/abstractive/hybrid/generative？摘錄；無則「未明說」
- (2) 系統輸出形式原文：free-form summary / extracted utterances / hybrid two-stage ...
- (3) 若有 output example：指出位置並摘錄代表性片段（不解釋）

Q8 Backbone（Transformer 與否：只列模型與作者用詞）
- (1) 列出 backbone/model 名稱（BART/T5/PEGASUS/LED/Longformer/GPT/...），每個附原文片段
- (2) 是否明寫 Transformer-based/Transformer architecture/encoder-decoder/decoder-only？摘錄；無則「未明說」
- (3) 若比較非 Transformer baseline：列出名稱與原文片段

Q9 multilingual/translation（只摘錄）
- (1) 是否提到 multilingual/cross-lingual/translation/non-English/...？有則摘錄；無則「未提及」
- (2) 若提到：逐項摘錄“哪些部分是多語”（dataset/model/training/eval/application）

Q10 評估方式與指標（只抽取）
- (1) 列出 automatic metrics（ROUGE/BERTScore/...）+ 原文片段
- (2) human eval 若有：摘錄（面向 + 設定）
- (3) 若提出新 metric / 新 evaluation protocol：摘錄命名與定義句

================================================
【輸出檔案（請提供下載）】
================================================
A) JSONL：`stage2_fulltext_extraction.jsonl`
- 一行一筆，只包含 Stage 1.2 include/maybe 的 keys
- 建議結構：
  {
    "key": "...",
    "mapping": {...},
    "Q0_secondary_signals": {...},
    "Q1_task_definition": {...},
    ...
    "Q10_evaluation": {...},
    "extraction_confidence": "high|medium|low",
    "notes": "..."
  }

B) CSV：`stage2_fulltext_extraction.csv`
- 作為索引用：key +（任務一句話、output、backbone terms、datasets list、modality terms、extractive/abstractive terms、secondary terms、multilingual terms、confidence）

C) `dataset_table_index_stage2.csv`
- 每篇 paper 的主要表格索引：key, table_id, table_context, datasets_mentioned

【回覆中請給 summary】
- Stage 1.2 include/maybe 的總數，以及實際成功讀到 full text 的數量
- 找不到對應 md 的 key 清單（若有）
- extraction_confidence=low 的 key 清單（若有）
並提供所有輸出檔案下載連結。
```