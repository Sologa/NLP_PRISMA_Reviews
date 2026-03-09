# TEMPLATE Prompt 4 — Stage 2（讀 Full Text 的資訊抽取；禁止做 include/exclude）

> **Stage 2 = full-text 抽取（General Template）**  
> 只對 Stage 1.2 的 include/maybe 讀 full text。  
> 只抽取（Q0–Q10），不判定。

```text
我會提供你：
1) stage1_2_screening_decisions.jsonl
2) fulltexts_text_only.zip

你的任務：只針對 Stage 1.2 include/maybe 的 keys，讀對應 md 全文並完成 Q0–Q10 資訊抽取（只抽取不判定）。

硬性要求：
- 只能用 key 做索引；若檔名不是 key 要記錄 mapping。
- 可以用程式做檔案讀寫/表格索引；不可用程式做自動分類下結論。
- 每個 Q 都要有 answer + evidence_quotes + evidence_location。

Q0 Secondary research signals（全文版）
- self-identification（survey/review/SoK/...）
- evidence synthesis methodology signals（PRISMA / screening / database search / inclusion/exclusion …）
- taxonomy/roadmap/position/vision 等綜整語氣
- 若同時釋出 dataset/benchmark/metric：只摘錄不判定

Q1–Q10：沿用你既有的抽取規格（task、contribution、datasets、dataset language、primary signals、modality、summary type、backbone、multilingual、metrics）
- dataset language 規則：未明說 → 直接視為 {{DATASET_LANGUAGE_DEFAULT_IF_UNSPECIFIED}}（通常 English）

輸出：
- stage2_fulltext_extraction.jsonl
- stage2_fulltext_extraction.csv（索引）
- dataset_table_index_stage2.csv（表格索引）
並在回覆給 summary（讀到全文的數量、mapping 問題、low confidence keys）。
```