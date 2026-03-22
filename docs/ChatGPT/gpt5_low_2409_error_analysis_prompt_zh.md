請你直接分析這個 GitHub repo 裡，`gpt-5` 單模型、`reasoning_effort=low`、`paper_id=2409.13738` 的單審查者官方 Batch 實驗結果，但只分析 `error cases`，不要重講全部正確案例。

先遵守這個 read order，不要跳步：

1. `AGENTS.md`
2. `docs/chatgpt_current_status_handoff.md`
3. `screening/results/results_manifest.json`
4. `screening/results/2409.13738_full/CURRENT.md`
5. `docs/batch/single_reviewer_official_batch_experiments_usage_zh.md`

重要背景：

- 目前 production criteria 是 stage-specific：
  - Stage 1: `criteria_stage1/<paper_id>.json`
  - Stage 2: `criteria_stage2/<paper_id>.json`
- `2409.13738` 的 current score authority 是：
  - Stage 1: `screening/results/2409.13738_full/stage1_f1.stage_split_criteria_migration.json`
  - Combined: `screening/results/2409.13738_full/combined_f1.stage_split_criteria_migration.json`
- 這次你要分析的不是 current production score authority，而是額外的 experimental line：
  - single-reviewer official batch baseline
  - model = `gpt-5`
  - reasoning_effort = `low`
  - run_id = `20260322_094235Z`
- 這個實驗固定使用 `criteria_stage2/2409.13738.json`
- 請不要把歷史 criteria 或歷史 score authority 誤當成 current production state
- 改進建議只能落在 prompting、workflow support、evidence extraction、adjudication / handoff 設計或 reviewer output 結構
- 不可以把 performance-oriented hardening 重新寫回 formal criteria

請你讀以下檔案：

- `criteria_stage2/2409.13738.json`
- `refs/2409.13738/metadata/title_abstracts_metadata.jsonl`
- `refs/2409.13738/metadata/title_abstracts_metadata-annotated.jsonl`
- `screening/results/single_reviewer_official_batch_gpt5_all4_2026-03-22/runs/20260322_094235Z/run_manifest.json`
- `screening/results/single_reviewer_official_batch_gpt5_all4_2026-03-22/runs/20260322_094235Z/batch_jobs/review/gpt-5/batch_latest.json`
- `screening/results/single_reviewer_official_batch_gpt5_all4_2026-03-22/runs/20260322_094235Z/REPORT_zh.md`
- `screening/results/single_reviewer_official_batch_gpt5_all4_2026-03-22/runs/20260322_094235Z/papers/2409.13738/single_reviewer_batch_f1.json`
- `screening/results/single_reviewer_official_batch_gpt5_all4_2026-03-22/runs/20260322_094235Z/papers/2409.13738/single_reviewer_batch_results.json`

請先自行 cross-check error cases。你算出來的結果應該要是：

- `3` 個 false positives
- `4` 個 false negatives

預期 error keys 如下，請自行驗證，不要盲信：

- False positives:
  - `neuberger_data_augment`
  - `bellan_gpt3_2022`
  - `bellan2022extracting`
- False negatives:
  - `lopez_assisted_declarative_process`
  - `halioui2018bioinformatic`
  - `neuberger2023beyond`
  - `qian2020approach`

很重要：

- GitHub repo 上沒有上傳全文；`refs/2409.13738/mds/*.md` 不在 GitHub
- 所以你不能因為 repo 裡沒有全文就停止分析
- 對每個 error case，如果需要確認 publication venue、peer review status、是否為 preprint、是否其實已有正式出版版本、方法與實驗細節，請你自行上網搜尋原文、DOI、OpenAlex、DBLP、出版社頁、arXiv、會議頁或其他可靠來源
- 特別是所有和「是不是 preprint」「是否 peer-reviewed」「是否已有正式 conference/journal 版本」有關的 case，必須主動搜尋，不可只靠 repo 內的單次模型判讀

你要回答的核心問題：

1. 每個 error case 真正錯在哪裡？
2. 是 gold label / evidence-base definition 的問題，還是模型判斷的問題？
3. 模型錯誤主要屬於哪一類：
   - publication-status checking failure
   - duplicate-record handling failure
   - topic-scope over-inclusion
   - topic-scope over-exclusion
   - empirical-validation threshold misread
   - source-faithful criteria interpretation failure
   - evidence retrieval failure
   - 其他
4. 哪些錯誤是 `gpt-5 low` 特別容易犯、但不應該透過修改 formal criteria 來修？
5. 在不改 criteria semantics 的前提下，最值得做的 prompt / workflow 支援改動是什麼？

請生成兩份報告。

第一份給我看，請命名為：

- `2409_gpt5_low_error_analysis_user_report.pdf`

如果你有能力直接產出檔案，請直接產出 PDF。
如果你的環境不能直接輸出 PDF，請至少輸出一份「可直接匯出成 PDF 的完整內容」，並明確標示這是 PDF 版正文。

這份 PDF 版請遵守：

- 全文用繁體中文
- 口語化、好懂，不要寫得像審稿意見
- 每個專有名詞、縮寫、技術名詞第一次出現時都要解釋
- 每個 error case 都要附上：
  - `paper title`：保留原英文標題，並附中文譯名
  - `abstract`：除了專有名詞與必要縮寫外，盡量翻成中文
  - 這篇為什麼被模型判錯
  - 你怎麼確認它其實應該被納入或排除
  - 這個錯誤對整體結果代表什麼
- 先給總結，再進入 case-by-case
- 最後請有一段「如果下一輪只做 2 到 4 個最划算修正，應該先做什麼」

第二份給 Codex / 工程分析看，請命名為：

- `2409_gpt5_low_error_analysis_codex.md`

這份 MD 版請遵守：

- 用 markdown
- 風格技術化、精簡、結論導向
- 一開始先給：
  - run summary
  - metrics summary
  - FP/FN counts
  - error taxonomy summary
- 每個 error case 請列出：
  - key
  - title
  - repo 內可用證據
  - repo 外補搜到的證據
  - gold 是否合理
  - model rationale 為何失真
  - 建議修正方向
- 請把 `bellan_gpt3_2022` 和 `bellan2022extracting` 是否屬於重複記錄單獨討論
- 請把所有「publication-status / peer-review」相關誤判整理成一個共通模式
- 最後請給一個只包含「不改 criteria semantics」的行動清單，依優先級排序

輸出要求：

- 先輸出一小段 `Executive Summary`
- 接著輸出 PDF 版內容
- 再輸出 MD 版內容
- 不要把時間花在正確案例
- 不要只停留在表面描述，要做 forensic-style analysis
