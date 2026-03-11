請你深入分析這個 GitHub repository。目標是診斷並提出修正方案，處理目前 screening workflow 中過多的 false negatives，特別是 `title + abstract` 階段的 false negatives。

你必須先讀這份 handoff 文件：

- `docs/chatgpt_gpt54pro_handoff.md`

然後嚴格依照 handoff 裡指定的閱讀順序進行分析。

最重要的基礎分析文件是：

- `docs/reviewer_error_analysis.md`
- `docs/detailed_reviewer_fn_analysis.md`
- `docs/taxonomy_root_cause_qa.md`

接著請讀實際 run 結果：

- `screening/results/2307.05527_full/run01/latte_review_results.run01.json`
- `screening/results/2307.05527_full/latte_fulltext_review_from_run01.json`
- `screening/results/2307.05527_full/latte_fulltext_from_run01_combined_f1.json`

- `screening/results/2409.13738_full/run01/latte_review_results.run01.json`
- `screening/results/2409.13738_full/latte_fulltext_review_from_run01.json`
- `screening/results/2409.13738_full/latte_fulltext_from_run01_combined_f1.json`

- `screening/results/2511.13936_full/run01/latte_review_results.run01.json`
- `screening/results/2511.13936_full/latte_fulltext_review_from_run01.json`
- `screening/results/2511.13936_full/latte_fulltext_from_run01_combined_f1.json`

- `screening/results/2601.19926_full/run01/latte_review_results.run01.json`
- `screening/results/2601.19926_full/latte_fulltext_review_from_run01.json`
- `screening/results/2601.19926_full/latte_fulltext_from_run01_combined_f1.json`

接著請讀 criteria 檔案：

- `criteria_jsons/2307.05527.json`
- `criteria_jsons/2409.13738.json`
- `criteria_jsons/2511.13936.json`
- `criteria_jsons/2601.19926.json`

接著請檢查實際 runtime pipeline 與 reviewer implementation：

- `scripts/screening/vendor/src/pipelines/topic_pipeline.py`
- `scripts/screening/vendor/resources/LatteReview/lattereview/agents/title_abstract_reviewer.py`
- `scripts/screening/vendor/resources/LatteReview/lattereview/agents/fulltext_reviewer.py`
- `scripts/screening/vendor/resources/LatteReview/lattereview/agents/basic_reviewer.py`
- `scripts/screening/vendor/resources/LatteReview/lattereview/workflows/review_workflow.py`

最後再對照 markdown prompt templates：

- `sr_screening_prompts_3stage/sr_specific/03_stage1_2_criteria_review.md`
- `sr_screening_prompts/sr_specific/05_stage2_criteria_review.md`

你的任務：

1. 驗證、補強，或反駁目前 repo 內已經完成的本地分析。
2. 清楚區分以下幾類問題：
   - criteria 問題
   - prompt 問題
   - reviewer 行為問題
   - arbitration / aggregation 問題
   - retrieval / full-text 問題
3. 說明目前五大 root-cause buckets 分別主要是由什麼造成的：
   - criteria 寫不好
   - prompt 設計不好
   - criteria serialization 有問題
   - runtime workflow policy 有問題
   - missing full-text retrieval
4. 特別注意以下幾點：
   - 為什麼 `2307.05527` 看起來被收窄成「paper 必須明確討論 ethics 才能納入」
   - 為什麼 Stage 1 在證據不足時過度使用 `exclude`
   - 為什麼 `2511.13936` 可能有過窄的 operational definition
   - 為什麼 disagreement cases 會被壓成 `exclude`
   - `missing_fulltext` 的 case 到底是真的拿不到，還是 pipeline failure
5. 提出具體 redesign 建議：
   - criteria serialization
   - Stage 1 prompt
   - Stage 2 prompt
   - arbitration logic
   - sparse metadata handling
   - missing full-text handling
6. 依照「預期 recall 改善幅度 / 實作複雜度」來排序修正優先級。

輸出要求：

1. 全程使用中文回答。
2. 先給一段簡短 executive summary。
3. 再按照 root-cause buckets 做系統性分析。
4. 再逐篇分析以下四個 review：
   - `2307.05527`
   - `2409.13738`
   - `2511.13936`
   - `2601.19926`
5. 再提出具體 implementation recommendations，並盡量指出對應 repo 中應修改的檔案。
6. 如果你不同意目前 repo 內已有的分析，請明確指出：
   - 不同意哪一點
   - 原因是什麼
   - 你認為更合理的解釋是什麼

不要只給泛泛而談的高層建議。每個重要結論都必須盡量以以上檔案中的內容作為依據。
