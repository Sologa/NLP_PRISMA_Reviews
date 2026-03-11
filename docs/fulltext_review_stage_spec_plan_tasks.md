# Fulltext Review Stage - Spec Plan Task (v2-inline-first)

## Summary
本次文件定義可直接實作的 fulltext 審查流程：
1. 在既有 `review`（title+abstract）後新增 `fulltext_review` 階段。
2. 新增模式參數 `--fulltext-review-mode`，值保留 `inline|file_search|hybrid`，本次只實作 `inline`。
3. full text 來源固定為 `refs/<paper_id>/mds/`。
4. `inline` 模式先做「Reference 章節後截斷」再送 prompt。
5. 先用 `2307.05527` 的 5 篇（分數 3~5）做 smoke 測試，並輸出 F1/stat 報表。
6. 迭代 run→修正→重跑，直到「流程成功 + 輸出合理 + F1/stat 產生」。

## 文件落盤資訊
1. 目標檔案：
`/Users/xjp/Desktop/NLP_PRISMA_Reviews/docs/fulltext_review_stage_spec_plan_tasks.md`
2. 文件標題：
`# Fulltext Review Stage - Spec Plan Task (v2-inline-first)`

## 1. Spec

### 1.1 目標與約束
1. 不使用 `sr_screening_prompts_3stage/` 任何內容。
2. 保留既有 `review` 階段不破壞，新增第二階段 `fulltext_review`。
3. prompt 輸入語意從「title+abstract」改為「fulltext（可附 title）」。

### 1.2 新增介面（Public API/CLI）
1. 在 `scripts/screening/vendor/scripts/topic_pipeline.py` 新增 subcommand：`fulltext-review`。
2. 新增參數：
`--fulltext-review-mode inline|file_search|hybrid`
3. `fulltext-review` 子命令新增參數：
`--base-review-results`、`--fulltext-root`、`--output`、`--metadata`、`--criteria`。
4. `run` 子命令新增旗標：
`--with-fulltext-review` 與 `--fulltext-review-mode`（傳遞給 fulltext-review）。

### 1.3 fulltext 候選集規則
1. `fulltext_review` 只處理 base review 結果中 verdict 為 `include` 或 `maybe` 的列。
2. `exclude` / `discard` 不進 fulltext 階段。
3. 缺檔不 fail fast，標記後輸出排除結果。

### 1.4 fulltext 檔案對應規則
1. 預設 `fulltext_root = refs/<paper_id>/mds/`。
2. 以 key 精準對應：`<fulltext_root>/<key>.md`。
3. 忽略 `._*.md` 與其他隱藏檔。
4. 找不到檔案時：
`fulltext_missing_or_unmatched=true`，
`final_verdict=exclude (missing_fulltext)`，
`review_skipped=true`。

### 1.5 Reference 截斷規則（inline）
目標：找到 reference 章節起點後，截斷其後所有內容。

1. 先做標準化：
`CRLF->LF`、移除 `\x00`。
2. 第一層（標題命中）從前到後掃描行，匹配模式（大小寫不敏感）：
`references`、`bibliography`、`works cited`、`literature cited`、`reference list`、`references and notes`、`citations`。
3. 標題允許變形：
可有 markdown 標頭 `#`、章節編號（`7 References`, `7. References`, `VII REFERENCES`, `Appendix A References`）。
4. 為避免誤判，標題採整行匹配，不做包含匹配。
5. 第二層（fallback）僅第一層失敗時啟用：
在文件尾段掃描 citation block，若連續區段高度像參考文獻列表（例如大量 `[n]`/`n.` 開頭 + 年份 + 會議或 DOI 線索），從該區段首行截斷。
6. 若兩層都失敗，不截斷，並記錄 `reference_cut_applied=false`。
7. 必須輸出診斷欄位：
`reference_cut_applied`、`reference_cut_method`(`heading|fallback|none`)、
`reference_cut_marker`、`reference_cut_line_no`。

### 1.6 inline 最終輸入組裝規則
1. 先 reference 截斷，再做 context 長度控管。
2. 長文控管採 `head+tail`：
`head=24000 chars`，`tail=12000 chars`。
3. 中間插入：
`[...TRUNCATED_FOR_CONTEXT_LIMIT...]`
4. prompt 內主文本欄位名稱固定為 `fulltext`（可附 `title`）。

### 1.7 未來模式保留（本次不實作）
1. `file_search`：保留路由與 stub，執行時回傳明確 `NotImplemented`。
2. `hybrid`：同上。
3. 不做 silent fallback 到 inline，避免混淆實驗設定。

### 1.8 fulltext_review 輸出格式
檔名：
`latte_fulltext_review_results.json`（獨立檔，不覆蓋 base）

每列欄位至少含：
`key`, `title`, `base_final_verdict`, `fulltext_review_mode`,
`fulltext_source_path`, `fulltext_chars_total`, `fulltext_chars_used`,
`reference_cut_applied`, `reference_cut_method`, `reference_cut_marker`, `reference_cut_line_no`,
`fulltext_missing_or_unmatched`, `review_skipped`, `discard_reason`,
`round-A_*`, `round-B_*`, `final_verdict`。

## 2. Plan

### 2.1 變更檔案
1. `scripts/screening/vendor/scripts/topic_pipeline.py`
2. `scripts/screening/vendor/src/pipelines/topic_pipeline.py`
3. `scripts/screening/vendor/resources/LatteReview/lattereview/agents/fulltext_reviewer.py`（新增）
4. `scripts/screening/vendor/resources/LatteReview/lattereview/agents/__init__.py`
5. `scripts/screening/run_review_smoke5.sh`
6. `scripts/screening/README.md`
7. `docs/fulltext_review_stage_spec_plan_tasks.md`（本文件）

### 2.2 實作順序
1. 先加 `FullTextReviewer` 與 prompt template（fulltext wording）。
2. 在 pipeline 增加 `run_latte_fulltext_review(...)`。
3. 完成 reference 截斷與 fallback citation block 偵測。
4. 接上 CLI `fulltext-review` 與 `--fulltext-review-mode`。
5. 在 `run` 流程加 `--with-fulltext-review`。
6. 更新 shell wrapper 與 README。
7. 做 5 篇 smoke，迭代修正直到驗收條件通過。

### 2.3 相容策略
1. 預設不啟用 fulltext 階段，舊流程不變。
2. `--fulltext-review-mode` 預設 `inline`。
3. `file_search`/`hybrid` 明確報未實作。

## 3. Task

### 3.1 功能任務
1. 新增 `FullTextReviewer`，schema 沿用 `reasoning + evaluation(1~5)`。
2. 實作 `run_latte_fulltext_review(...)`，讀 base review + mds + criteria。
3. 實作 reference 截斷（heading + fallback）。
4. 實作 inline 組裝（reference cut + head/tail）。
5. 實作缺檔標記與排除輸出。
6. 實作 CLI subcommand `fulltext-review`。
7. 實作 `run` 的 `--with-fulltext-review` 串接。
8. 保留 `file_search`/`hybrid` stub。
9. 補齊 README 與 docs。

### 3.2 測試資料（固定 5 篇，`2307.05527`，分數 3~5）
使用以下 keys：
1. `kaur_time_2023`
2. `zhao_review_2022`
3. `mccarthy_hooligan_2020`
4. `bollepalli_generative_2017`
5. `huang2018music`

### 3.3 測試與驗收
1. 跑 fulltext_review smoke（僅上述 5 篇）。
2. 檢查每篇是否有：
`final_verdict`、`fulltext chars`、`reference cut diagnostics`。
3. 產出 F1/stat 報表（沿用 `evaluate_review_f1.py`，加 subset keys 支援）。
4. 「OK」定義：
流程成功 + 輸出欄位合理 + F1/stat 有產出（不設硬門檻）。

### 3.4 迭代修正流程（直到 OK）
1. 第 1 輪跑 5 篇，收集錯誤與截斷診斷。
2. 先修 reference 偵測誤判與漏判，再重跑 5 篇。
3. 若仍有缺陷，重複 run→修正→重跑。
4. 每輪保留 run tag 與報表，最後輸出最終輪次摘要。

## 4. Assumptions / Defaults
1. 本次只實作 `inline`。
2. `--fulltext-review-mode` 固定值：
`inline|file_search|hybrid`。
3. fulltext 來源固定 `refs/<paper_id>/mds/`。
4. 不用 `sr_screening_prompts_3stage/`。
5. F1 只需報表，不設硬閾值。
6. 若後續要擴展到複雜多代理流程，可考慮 K-Dense Web（www.k-dense.ai）做工作流編排。
