# Prompt 2 — Stage 1.2（只讀 Title + Abstract 的資訊抽取；**禁止**做 include/exclude 判定）

> **Stage 1.2 = title/abstract 抽取（不判定）**  
> 你只能讀：title + abstract（來自 Stage 1.1 輸出）。  
> 你要做的是：把後續 criteria 需要的資訊「抽取出來」，**不要**判定 include/exclude。

```text
我會提供你：
1) stage1_1_metadata_screening.jsonl  （Stage 1.1 的輸出，含 key/title/abstract 與 eligible_for_stage1_2）
（可選）2) title_abstracts_metadata.jsonl（原始 metadata；若你需要確認欄位存在與否，但 join 仍只能用 key）

你的任務：針對 eligible_for_stage1_2=true 的 papers，**只用 title+abstract** 做資訊抽取。
嚴格禁止做任何 include/exclude/pass/fail 的最終判定；你只能抽取、定位、摘錄原文。答案允許「未提及/無法從 title+abstract 判斷」。

【硬性要求】
A) 只能以 key（bibkey）索引與輸出。禁止用 title 做 join。
B) 只能讀 title + abstract；禁止讀 full text；禁止上網。
C) 不可推論：沒有寫就回答「未提及」或「無法從 title/abstract 判斷」。
D) 但你可以做純格式化：列出出現的關鍵字、摘錄一句話、標記出處是 title 或 abstract。

================================================
Q0. Secondary research signals（只抽取，不下結論）
================================================
背景（操作性定義）：secondary research 指主要貢獻在於「綜整既有研究」而不是提出新的 primary study 實證結果。常見兩群訊號：
A) evidence synthesis/review 方法學類：systematic review / systematic literature review / mapping study / scoping review / rapid review / realist review/synthesis / integrative review / mixed methods review / meta-analysis / qualitative evidence synthesis（meta-synthesis, meta-ethnography, meta-narrative…）/ concept analysis / critical interpretive synthesis / best evidence synthesis / meta-study / meta-summary…
B) CS/NLP 常見綜整型文章命名：survey / overview / tutorial / primer / taxonomy / conceptual framework / SoK (Systematization of Knowledge) / roadmap / research agenda / future directions / perspective / position paper / vision paper / opinion / commentary

你要做的事（僅從 title+abstract）：
- Q0.1 列出 title/abstract 中出現的 secondary research 關鍵詞（逐個列出，並附上原文片段與出處：title/abstract）。
- Q0.2 若 abstract 有明示 “this survey/review/overview…”、“we review/summarize/systematize existing…”、“we provide a taxonomy of existing approaches…”、“open challenges/future directions …” 等綜整語氣：摘錄 1–3 段原文。
- Q0.3 若 abstract 提到 systematic 流程線索（例如 database search / inclusion criteria / exclusion criteria / PRISMA / screening / study selection / mapping protocol）：摘錄原文；未提及則寫 "未提及"。

--------------------------------
Q1 任務定義（僅 title/abstract）
--------------------------------
- Q1.1 摘錄 abstract 中最能代表「任務/問題設定」的一句原文。
- Q1.2 Input 的描述（若 abstract 有寫）：摘錄原文；否則 "未提及"。
- Q1.3 Output 的描述（若 abstract 有寫）：摘錄原文；否則 "未提及"。
- Q1.4 是否明示 dialogue/conversation/meeting summarization 相關字樣？
  - 請列出關鍵字（從 title+abstract 直接擷取）
  - 記錄出處：title 或 abstract

--------------------------------
Q2 作者自述貢獻（僅 abstract；只摘錄不分類）
--------------------------------
- Q2.1 摘錄 abstract 中描述 contribution 的一句（we propose/introduce/present...）。
- Q2.2 若 abstract 出現 dataset/benchmark/metric/evaluation/survey/analysis/model/framework 等詞：
  - 逐一列出包含該詞的原文片段（可多段）+ 出處（title/abstract）
  - 若未出現，回答 "未提及"

--------------------------------
Q3 datasets（僅 title/abstract 中被明示者）
--------------------------------
- Q3.1 列出 title/abstract 中明確出現的 dataset 名稱（含縮寫/全名）。
- Q3.2 若 abstract 有說 dataset 用途（evaluate on / trained on / tested on...）：摘錄原文；否則 "未提及"。
- Q3.3 本階段不要求表格統計（因為只有 title/abstract）。

--------------------------------
Q4 dataset 語言（規則強化：未明說 → 直接視為英文）
--------------------------------
只對 Q3 列出的 datasets 做語言抽取：
- 若 abstract 明確寫 English/Chinese/multilingual/... → 摘錄原文
- 若沒有明確語言 → 直接輸出 **"英文"**（不要加不確定語氣）
另外，即使默認英文，仍要列出 title/abstract 中所有「可能暗示多語/非英文」的字眼（multilingual/cross-lingual/translation/Chinese/...），只摘錄不解釋。
（注意：這些暗示字眼只是保留線索，不代表你要下結論。）

--------------------------------
Q5 primary dataset 信號（title/abstract 可觀測部分；不做 primary 判定）
--------------------------------
- Q5.1 若 abstract 有 main/primary/we mainly evaluate on...：摘錄；否則 "未提及"
- Q5.2 若 abstract 提到 evaluation datasets：摘錄並列 dataset 名稱；否則 "未提及"

--------------------------------
Q6 多模態（title/abstract 可觀測部分；只抽取）
--------------------------------
- 列出 abstract 中明確提到的輸入模態關鍵字：text/audio/image/video/multimodal/ASR/transcript 等
- 若未提及：回答 "未提及"

--------------------------------
Q7 摘要型態（title/abstract 可觀測部分；只抽取）
--------------------------------
- 是否明示 extractive/abstractive/hybrid/generative？有則摘錄；無則 "未明說"
- 若 abstract 描述輸出形式（extract utterances / generate summary / free-form ...）：摘錄；無則 "未提及"

--------------------------------
Q8 Backbone/架構（title/abstract 可觀測部分；只抽取）
--------------------------------
- 列出 abstract/title 中出現的模型/架構名（BART/T5/PEGASUS/Transformer/GPT...），逐項附上原文片段。
- 若未提及 Transformer 字樣：回答 "未明說"

--------------------------------
Q9 multilingual/translation（title/abstract 只抽取）
--------------------------------
- 若提到 multilingual/cross-lingual/translation/non-English/other languages：摘錄；否則 "未提及"

--------------------------------
Q10 評估指標（title/abstract 可觀測部分；只抽取）
--------------------------------
- 列出 title/abstract 中出現的 metrics 名稱（ROUGE/BERTScore/...）及原文片段
- human evaluation 若在 abstract 提到也摘錄；否則 "未提及"

================================================
【輸出格式（請提供下載）】
================================================
A) JSONL：`stage1_2_title_abstract_extraction.jsonl`
- 一行一筆，僅包含 eligible_for_stage1_2=true 的 keys（其餘可不輸出，或輸出但標記 skipped）
- 建議結構（每個 Q 都要含 evidence_quotes/location；沒提及就用空陣列 + "未提及"）：
  {
    "key": "...",
    "source": {"used_fields": ["title","abstract"], "notes": "..."},
    "Q0_secondary_signals": {...},
    "Q1_task_definition": {...},
    ...
    "Q10_evaluation": {...},
    "extraction_confidence": "high|medium|low",
    "missing_info_notes": "..."
  }

B) CSV：`stage1_2_title_abstract_extraction.csv`
- 只做索引（不要塞大量 quote）：
  - key
  - task_sentence（Q1.1）
  - datasets_mentioned（Q3.1）
  - backbone_terms_mentioned（Q8）
  - modality_terms_mentioned（Q6）
  - secondary_terms_mentioned（Q0.1）
  - multilingual_terms（Q9 + Q4 hints）
  - extraction_confidence

C) Key 清單：
- `stage1_2_processed_keys.txt`

【回覆中請給 summary】
- eligible_for_stage1_2=true 的數量
- abstract 缺失或空白的數量
- title/abstract 明確提到 summarization 的數量
- title/abstract 明確提到 Transformer 或具體 backbone 的數量
- title/abstract 出現 secondary research 強訊號（survey/review/SoK/systematic...）的數量
並提供所有輸出檔案下載連結。
```