請全程使用中文回答。

在開始任何分析前，先依照這個順序閱讀：

1. 根目錄 `AGENTS.md`
2. `docs/chatgpt_current_status_handoff.md`
3. `screening/results/results_manifest.json`
4. 你要處理的 paper 對應 `screening/results/<paper>_full/CURRENT.md`

非常重要：

- current active criteria 是：
  - `criteria_stage1/<paper_id>.json`
  - `criteria_stage2/<paper_id>.json`
- `criteria_jsons/*.json` 不是 current production criteria
- current score authority 是：
  - `2409` / `2511` -> `stage_split_criteria_migration`
  - `2307` / `2601` -> latest fully benchmarked `senior_no_marker`

不要在讀完上面四項之前就推論 current state。

如果你引用歷史報告，請明確標記它是 `historical context`，不要把它當 current production state。
