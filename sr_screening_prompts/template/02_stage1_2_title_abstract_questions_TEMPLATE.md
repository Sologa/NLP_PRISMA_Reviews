# TEMPLATE Prompt 2 — Stage 1.2（只讀 Title + Abstract 的資訊抽取；禁止做 include/exclude）

> **Stage 1.2 = title/abstract 抽取（General Template）**  
> 你只能讀：title + abstract。  
> 你只做抽取，不做任何 pass/fail。

```text
我會提供你：
1) stage1_1_metadata_screening.jsonl

你的任務：針對 eligible_for_stage1_2=true 的 papers，**只用 title+abstract** 做資訊抽取（Q0–Q10）。
嚴格禁止做 include/exclude 判定；你只能抽取、定位、摘錄原文。答案允許「未提及/無法判斷」。

【硬性要求】
- 只能用 key（bibkey）索引與輸出。
- 只能讀 title+abstract；禁止讀 full text；禁止上網。
- 沒寫就回答 "未提及"。

================================================
Q0. Secondary research signals（只抽取，不判定；模板內建）
================================================
Secondary research 操作性訊號（供後續 criteria 用）：
A) evidence synthesis/review 方法學：systematic review/SLR, mapping study, scoping review, rapid review, realist synthesis, integrative review, mixed methods review, meta-analysis, qualitative evidence synthesis (meta-synthesis/meta-ethnography/meta-narrative…), concept analysis, critical interpretive synthesis, best evidence synthesis, meta-study, meta-summary...
B) CS/NLP 綜整型文章命名：survey, overview, tutorial/primer, taxonomy, conceptual framework, SoK (Systematization of Knowledge), roadmap, research agenda, future directions, perspective, position paper, vision paper, opinion, commentary...

你要：
- 列出 title/abstract 中的 secondary 相關關鍵字（逐個 + 原文片段 + 出處）。
- 摘錄 survey/review/systematize existing work/taxonomy of existing approaches/future directions 等綜整語氣句子（若有）。
- 摘錄 PRISMA / inclusion criteria / screening / database search 等 systematic 流程線索（若有）。

================================================
Q1–Q10（僅 title/abstract 可見部分）
================================================
Q1 任務定義（task / input / output / summarization 關鍵字）
Q2 作者自述 contribution（只摘錄）
Q3 datasets（title/abstract 明示者）
Q4 dataset 語言（規則：未明說 → 直接視為 {{DATASET_LANGUAGE_DEFAULT_IF_UNSPECIFIED}}；通常填 English）
Q5 primary dataset signals（只摘錄 main/primary/we evaluate on…）
Q6 input modality terms（text/audio/image/video/ASR/transcript…）
Q7 summarization type terms（extractive/abstractive/hybrid/generative…）
Q8 backbone terms（Transformer/BART/T5/GPT…）
Q9 multilingual/translation terms
Q10 metrics terms（ROUGE/BERTScore…）

（請沿用你已定義的 Q1–Q10 格式：每題都要有 answer + evidence_quotes + evidence_location）

================================================
【輸出】
================================================
- stage1_2_title_abstract_extraction.jsonl
- stage1_2_title_abstract_extraction.csv（索引用）
- stage1_2_processed_keys.txt
並在回覆給 summary（secondary 訊號出現比例、summarization/Transformer 提及比例等）。
```