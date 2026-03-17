# ChatGPT 新對話串主指令

你現在要做的是一個高投入、必須完整讀 PDF、必須顯式多輪自我修正、而且最後要交付 zip-ready 成果的任務。

這不是快速 brainstorming。  
你不能看幾份摘要就下結論。  
你也不能只產生針對單一 SR 的 prompt。  

你這次的正確任務是：

1. 設計一份 **general Stage 1 QA generation prompt**
2. 設計一份 **general Stage 2 QA generation prompt**
3. 用這兩份 general prompts，對 **全部 16 篇 SR** 生成對應 QA
4. 最後輸出：
   - 報告
   - general Stage 1 prompt
   - general Stage 2 prompt
   - 16 篇 SR 的 QA
   - PDF 閱讀紀錄
   - revision log
   - 若工具環境允許，將全部結果打包成一個 zip

## 一、Repo 背景與 current-state 約束

GitHub repo URL：

1. `https://github.com/Sologa/NLP_PRISMA_Reviews`

### current production state

你必須先記住：

1. current production Stage 1 criteria 來自 `criteria_stage1/<paper_id>.json`
2. current production Stage 2 criteria 來自 `criteria_stage2/<paper_id>.json`
3. `criteria_jsons/*.json` 不是 current production criteria
4. current runtime prompt source 是 `scripts/screening/runtime_prompts/runtime_prompts.json`
5. repo 不接受把 derived hardening 偽裝回 formal criteria
6. repo 不接受第三層 hidden guidance 作為正式 criteria 層

### 你這次的任務和 current production 的關係

你這次不是要直接改 production criteria。  
你這次是要做：

1. 一對 general QA-generation prompts
2. 一套可對所有 SR 產生 QA 的方法
3. 一套基於完整 PDF 閱讀的 QA 資產

所以你的輸出要被定位成：

1. workflow support
2. QA generation assets
3. evidence extraction support

而不是：

1. new criteria
2. hidden operational criteria
3. pseudo-guidance layer

## 二、你要回答的核心問題

你要解決的不是單一 paper 的 prompt，而是：

> 在完整閱讀全部 16 篇 SR PDF 後，如何抽象出兩份真正通用、可重用、且不 specific 到任何單一 SR 的 general prompts，用來生成 Stage 1 QA 與 Stage 2 QA；並把它們實際應用到全部 16 篇 SR 上，產生 QA 資產。

## 三、你必須閱讀哪些東西

### A. current-state 必讀文件

先讀：

1. `AGENTS.md`
2. `docs/chatgpt_current_status_handoff.md`
3. `screening/results/results_manifest.json`
4. `docs/stage_split_criteria_migration_report.md`
5. `scripts/screening/runtime_prompts/runtime_prompts.json`

### B. 既有 QA / next-step 分析文件

再讀：

1. `criteria_mds/README.md`
2. `criteria_mds/README_PARSING_METHOD.md`
3. `criteria_mds/AGENT_PROMPT_generate_question_set_from_criteria.md`
4. `docs/ChatGPT/evidence_qa_feasibility_analysis_2409_2511.md`
5. `docs/ChatGPT/next_experiments_criteria_mds_qa_report_2409_2511_zh.md`
6. `docs/ChatGPT/next_experiments_criteria_mds_qa_deep_analysis_zh.md`

### C. 全部 16 篇 SR 的強制閱讀要求

你必須完整閱讀全部 16 篇 SR 的 PDF，不可跳過，不可只看摘要。

對每一篇，你都必須同時看：

1. `criteria_mds/<paper_id>.md`
2. `refs/<paper_id>/<paper_id>.pdf`

全部 16 篇如下：

1. `2303.13365`
2. `2306.12834`
3. `2307.05527`
4. `2310.07264`
5. `2312.05172`
6. `2401.09244`
7. `2405.15604`
8. `2407.17844`
9. `2409.13738`
10. `2503.04799`
11. `2507.07741`
12. `2507.18910`
13. `2509.11446`
14. `2510.01145`
15. `2511.13936`
16. `2601.19926`

如果你沒有讀完全部 16 篇 PDF，就不准寫 final prompt，也不准寫 final QA。

## 四、你必須如何證明你真的讀完 PDF

你最後必須交一份 **PDF Reading Log**，對 16 篇逐篇列出：

1. paper id
2. 是否已讀完 PDF
3. 主要 eligibility / inclusion / exclusion 結構
4. metadata-only 條件
5. 可觀測 title/abstract 條件
6. full-text-only 條件
7. 該 paper 對 Stage 1 QA prompt 的啟發
8. 該 paper 對 Stage 2 QA prompt 的啟發
9. 該 paper 的 anti-pattern / contamination risk

如果沒有這份 log，就代表你沒有完成任務。

## 五、你這次要產出的 prompt 是什麼類型

### 1. 必須是 general prompt

你最終設計的兩份 prompt 必須是 general。

也就是說：

1. 不能把 `2409`、`2511`、或任何 SR 的專屬概念硬寫進 prompt 本體
2. 不能把特定 task family 寫成固定規則
3. prompt 只能依賴「輸入的 criteria / source SR 內容」
4. prompt 應使用 placeholders、規則、輸出 schema、生成要求

### 2. 你必須產出兩份，不是一份

必交：

1. `General Prompt: Stage 1 QA Generation`
2. `General Prompt: Stage 2 QA Generation`

兩者要清楚分工：

1. Stage 1 prompt 只針對 title/abstract observable projection
2. Stage 2 prompt 處理 canonical / confirmatory / full-text-only 條件

### 3. 這兩份 prompt 要能支援後續 synthesis

你的 prompt 不可以只問自由文本問題。  
它必須要求產生的 QA 帶有：

1. canonical field mapping
2. state space（例如 present / absent / unclear）
3. quote requirement
4. location requirement
5. missingness reason
6. conflict note（若適用）

## 六、你要如何從 16 篇 SR 中歸納 general prompts

你必須先做 comparative analysis，而不是直接寫 prompt。

### 你至少要歸納出下面幾種 pattern

1. metadata-only patterns
2. task-definition patterns
3. method / model / pipeline patterns
4. dataset / modality / language patterns
5. experiment / evaluation patterns
6. publication-type / survey / review exclusion patterns
7. title/abstract observable patterns
8. full-text-only confirmatory patterns

### 你也要歸納 anti-pattern

至少要包括：

1. question-set contamination
2. retrieval gate 混入 screening QA
3. historical hardening 偷偷回流
4. 非目標例子被寫成正向 example
5. Stage 1 / Stage 2 問題不分

## 七、你必須顯式做多輪自我修正

你至少要做 4 個顯式階段：

1. Round 0：比較矩陣完成後的初稿
2. Round 1：第一輪自我批判
3. Round 2：第二輪修正
4. Final：最終版

每一輪都要寫：

1. 這一版的 prompt 設計原則
2. 這一版最大的缺點
3. 下一輪要修什麼

你不需要暴露冗長隱性 chain-of-thought，但必須交 revision log。

## 八、你最終要產出的 QA 資產範圍

不是只做 `2409/2511`。  
你必須對全部 16 篇 SR 生成 QA。

### 每篇至少要有

1. Stage 1 QA
2. Stage 2 QA

如果某篇原始 SR 沒有清楚 stage split，你也必須：

1. 先根據 PDF 本體與 criteria 結構推導出 stage split
2. 再生成 Stage 1 QA 與 Stage 2 QA
3. 明確說明哪些欄位是 observable projection，哪些是 canonical/full-text confirmation

### 你不能偷懶做成 generic skeleton

你必須真的對每一篇生成實際 QA 內容，而不是只給一個模板外殼。

## 九、你最後必須輸出的成果結構

你最終輸出要對應下面這個 zip-ready 結構。

### 建議 zip 內容結構

1. `/report/qa_generation_general_prompt_report.md`
2. `/prompts/general_stage1_qa_generation_prompt.md`
3. `/prompts/general_stage2_qa_generation_prompt.md`
4. `/logs/pdf_reading_log.md`
5. `/logs/revision_log.md`
6. `/qa_generated/2303.13365_stage1_qa.md`
7. `/qa_generated/2303.13365_stage2_qa.md`
8. `/qa_generated/2306.12834_stage1_qa.md`
9. `/qa_generated/2306.12834_stage2_qa.md`
10. `/qa_generated/2307.05527_stage1_qa.md`
11. `/qa_generated/2307.05527_stage2_qa.md`
12. `/qa_generated/2310.07264_stage1_qa.md`
13. `/qa_generated/2310.07264_stage2_qa.md`
14. `/qa_generated/2312.05172_stage1_qa.md`
15. `/qa_generated/2312.05172_stage2_qa.md`
16. `/qa_generated/2401.09244_stage1_qa.md`
17. `/qa_generated/2401.09244_stage2_qa.md`
18. `/qa_generated/2405.15604_stage1_qa.md`
19. `/qa_generated/2405.15604_stage2_qa.md`
20. `/qa_generated/2407.17844_stage1_qa.md`
21. `/qa_generated/2407.17844_stage2_qa.md`
22. `/qa_generated/2409.13738_stage1_qa.md`
23. `/qa_generated/2409.13738_stage2_qa.md`
24. `/qa_generated/2503.04799_stage1_qa.md`
25. `/qa_generated/2503.04799_stage2_qa.md`
26. `/qa_generated/2507.07741_stage1_qa.md`
27. `/qa_generated/2507.07741_stage2_qa.md`
28. `/qa_generated/2507.18910_stage1_qa.md`
29. `/qa_generated/2507.18910_stage2_qa.md`
30. `/qa_generated/2509.11446_stage1_qa.md`
31. `/qa_generated/2509.11446_stage2_qa.md`
32. `/qa_generated/2510.01145_stage1_qa.md`
33. `/qa_generated/2510.01145_stage2_qa.md`
34. `/qa_generated/2511.13936_stage1_qa.md`
35. `/qa_generated/2511.13936_stage2_qa.md`
36. `/qa_generated/2601.19926_stage1_qa.md`
37. `/qa_generated/2601.19926_stage2_qa.md`
38. `/manifest.md`

如果你的工具環境允許，請真的把這些檔案打成一個 zip。  
如果工具環境不允許建立 zip，請明確說明，並仍按上述邏輯輸出全部內容。

## 十、你最後的報告必須包含哪些章節

### 強制章節

1. Executive Summary
2. Current-State Recap
3. PDF Reading Log Summary
4. 16-Paper Comparative Matrix
5. General Prompt Design Principles
6. Anti-Patterns And Failure Modes
7. Revision Log
8. Final General Stage 1 Prompt
9. Final General Stage 2 Prompt
10. Generated QA Assets Overview
11. Final Recommendations

## 十一、你不能犯的錯

你必須主動避免下列錯誤：

1. 只設計 `2409/2511` 專用 prompt
2. 沒有把 prompts 做成 general
3. 沒有詳讀全部 16 篇 PDF
4. 只看 `criteria_mds`、沒讀 PDF 本體
5. 沒有生成全部 16 篇 SR 的 QA
6. 沒有 revision log
7. 沒有 PDF reading log
8. 沒有 zip-ready 結構
9. 把 workflow support 偽裝成 criteria
10. 把 historical criteria 說成 current production state

## 十二、最後一句最重要

> 你的任務不是快速提建議，而是從全部 16 篇 SR 的 PDF 細讀中，抽象出兩份 truly general 的 Stage 1 / Stage 2 QA generation prompts，經過多輪自我修正後，再用它們對全部 16 篇 SR 生成 QA，最後以 zip-ready 形式交付完整成果。

現在開始執行。不要停在 plan。先讀 current-state 文件，再讀全部 16 篇 PDF。

