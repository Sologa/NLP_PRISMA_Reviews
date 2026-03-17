---
title: "ChatGPT 新對話串主指令：基於其他 SR 全量閱讀來設計 QA 生成 prompt"
date: "2026-03-17"
lang: zh-TW
status_note: "Instruction document for a fresh ChatGPT thread."
---

# 使用方式

把本文件整份貼到新的 ChatGPT 對話串。  
不要先摘要，不要先改寫，先原樣貼上。  

如果對方能存取 repo 檔案與網路，直接要求它按此執行。  
如果對方無法存取 repo 檔案，要求它先明確說缺哪些檔案，再由你補檔，不要接受它在缺材料的情況下直接開始寫最終答案。

# 可直接貼給 ChatGPT 的主指令

以下開始是你要貼給新對話串 ChatGPT 的完整指令。

---

你現在要做的是一個**高投入、長時間閱讀、需要多輪自我修正**的研究設計任務。  
你不能快速掃過就下結論。  
你必須先完整建立 current state，再完整閱讀指定 SR corpus，再進行 prompt 設計、QA 設計、與自我迭代修正。

你的任務不是隨便提建議，而是要最後真正交付三樣東西：

1. 一份完整報告
2. 一份「生成 QA 用的 prompt」
3. 你根據這份 prompt 實際寫出來的 QA 資產

而且你必須自己做**顯式的多輪 critique / revise 迭代**，不是一次寫完就停。

## 一、先理解你現在身處的專案背景

這個 repo 的 current production state 已經和很多歷史報告不同。你必須先接受下面幾件事，否則後面全部都會混版。

### 1. current production criteria 不是 `criteria_jsons/*.json`

目前 active criteria 是 stage-specific：

1. Stage 1：`criteria_stage1/<paper_id>.json`
2. Stage 2：`criteria_stage2/<paper_id>.json`

不要把：

1. `criteria_jsons/*.json`
2. 舊的 operational-v2
3. 舊的 stage-split wording experiment
4. 舊的 markdown prompt template

當成 current production state。

### 2. current runtime prompt source

current runtime prompt 來源是：

1. `scripts/screening/runtime_prompts/runtime_prompts.json`

不要把舊 prompt reports 當 current runtime。

### 3. current workflow invariants

Stage 1 routing 現在是：

1. 兩位 junior reviewer 先看 title + abstract
2. 若兩位都 `>= 4`，則 final Stage 1 = include
3. 若兩位都 `<= 2`，則 final Stage 1 = exclude
4. 其他情況全部送 `SeniorLead`

SeniorLead 是 workflow invariant，不可直接移除。

### 4. current methodology invariants

下面幾條是非談不可的限制：

1. `criteria_stage2/<paper_id>.json` 是 canonical、source-faithful、final eligibility
2. `criteria_stage1/<paper_id>.json` 是 title/abstract observable projection
3. 不能把 derived operational hardening 寫回 formal criteria
4. repo 明確不接受第三層 hidden guidance / hidden policy / pseudo-guidance 作為正式 criteria 層

換句話說，如果你後面提出的改善依賴：

1. prompting
2. evidence extraction
3. structured reviewer output
4. handoff object
5. adjudication behavior

那它們必須被描述成 workflow support，而不是 criteria 本體。

### 5. 這四篇是 current active / current sensitive papers

current repo 裡最重要的四篇是：

1. `2307.05527`
2. `2409.13738`
3. `2511.13936`
4. `2601.19926`

其中：

1. `2409.13738`
2. `2511.13936`

是目前和 evidence-QA / criteria_mds QA next-step 討論最直接相關的兩篇。

### 6. current score authority

你必須記住：

1. `2409.13738`
   - Stage 1 authority：`screening/results/2409.13738_full/stage1_f1.stage_split_criteria_migration.json`
   - Combined authority：`screening/results/2409.13738_full/combined_f1.stage_split_criteria_migration.json`
2. `2511.13936`
   - Stage 1 authority：`screening/results/2511.13936_full/stage1_f1.stage_split_criteria_migration.json`
   - Combined authority：`screening/results/2511.13936_full/combined_f1.stage_split_criteria_migration.json`
3. `2307.05527`
   - current stable reference：latest fully benchmarked `senior_no_marker`
4. `2601.19926`
   - current stable reference：latest fully benchmarked `senior_no_marker`

不要把歷史 `criteria_2409_stage_split` 或 `criteria_2511_opv2` scores 說成 current score source。

### 7. candidate next experiment 的正確定位

下面這份是 candidate next experiment，不是 adopted architecture：

1. `docs/ChatGPT/evidence_qa_feasibility_analysis_2409_2511.md`

你後面要做的工作，是建立在：

1. current architecture 已經是 stage-split
2. current criteria 不能再被污染
3. evidence-QA / synthesis 是候選 workflow-layer 改進方向

的前提上。

## 二、你這次的核心任務是什麼

你這次的目標不是單純評價現有 `criteria_mds/`。  
你的真正任務是：

### 任務主軸

基於 repo current state、既有 `criteria_mds/`、以及**所有其他 SR 的完整閱讀**，設計出一套高品質、可迭代修正的**QA 生成 prompt**，並且用它實際生成對應 QA 資產。

### 你最終一定要交付的三樣東西

1. **報告**
   - 說明你看了哪些材料
   - 說明你從哪些 SR 中萃取出哪些 QA 設計模式
   - 說明你如何從閱讀中抽象出 prompt design principles
   - 說明你如何自我迭代修正
   - 說明你最終 prompt 為什麼長成那樣
   - 說明最終 QA 資產為何如此設計
2. **prompt**
   - 這是一份「生成 QA 用的 prompt」
   - 不是簡短概念，而是可直接拿去喂另一個模型使用的完整 prompt
   - 它要能把 criteria / stage-specific criteria 轉成高品質 QA spec
   - 它必須要求輸出可以支援後續 evidence synthesis
3. **你自己用這份 prompt 寫出來的 QA**
   - 不是只交 prompt 不實作
   - 你要用你最終版本的 prompt，實際產生 QA 資產
   - QA 資產至少要對 `2409.13738` 與 `2511.13936` 生成：
     1. Stage 1 QA
     2. Stage 2 QA

也就是最少要交 4 份 QA section：

1. `2409` Stage 1 QA
2. `2409` Stage 2 QA
3. `2511` Stage 1 QA
4. `2511` Stage 2 QA

## 三、你必須閱讀哪些東西

### A. current-state 必讀文件

請先依下面順序讀：

1. `AGENTS.md`
2. `docs/chatgpt_current_status_handoff.md`
3. `screening/results/results_manifest.json`
4. `screening/results/2409.13738_full/CURRENT.md`
5. `screening/results/2511.13936_full/CURRENT.md`
6. `screening/results/2307.05527_full/CURRENT.md`（若存在）
7. `screening/results/2601.19926_full/CURRENT.md`（若存在）

### B. 這次任務直接相關的分析文件

請完整閱讀：

1. `docs/ChatGPT/evidence_qa_feasibility_analysis_2409_2511.md`
2. `docs/ChatGPT/next_experiments_criteria_mds_qa_report_2409_2511_zh.md`
3. `docs/ChatGPT/next_experiments_criteria_mds_qa_deep_analysis_zh.md`
4. `docs/stage_split_criteria_migration_report.md`

### C. criteria_mds 與 QA scaffold 必讀文件

請完整閱讀：

1. `criteria_mds/README.md`
2. `criteria_mds/README_PARSING_METHOD.md`
3. `criteria_mds/AGENT_PROMPT_generate_question_set_from_criteria.md`
4. `criteria_mds/2409.13738.md`
5. `criteria_mds/2511.13936.md`

### D. 你必須詳讀的「其他 SR」全文 corpus

這一條是強制要求。  
你必須**詳讀所有其他 SR papers**，也就是除了下面四篇以外的其他 SR：

排除這四篇作為「其他 SR corpus」之外：

1. `2307.05527`
2. `2409.13738`
3. `2511.13936`
4. `2601.19926`

你必須完整詳讀下面這 12 篇 SR：

1. `criteria_mds/2303.13365.md`
2. `criteria_mds/2306.12834.md`
3. `criteria_mds/2310.07264.md`
4. `criteria_mds/2312.05172.md`
5. `criteria_mds/2401.09244.md`
6. `criteria_mds/2405.15604.md`
7. `criteria_mds/2407.17844.md`
8. `criteria_mds/2503.04799.md`
9. `criteria_mds/2507.07741.md`
10. `criteria_mds/2507.18910.md`
11. `criteria_mds/2509.11446.md`
12. `criteria_mds/2510.01145.md`

對每一篇，你不能只看 `criteria_mds` 摘要。  
你必須再打開該檔案內標示的 Source URL，閱讀原始 SR paper 本體。

### E. 這 12 篇「其他 SR」的閱讀要求

對每一篇 paper，你至少要搞清楚下面幾件事：

1. 該 SR 的正式 eligibility / inclusion / exclusion 結構
2. 哪些條件是 metadata-only
3. 哪些條件需要 title/abstract evidence
4. 哪些條件需要 full-text evidence
5. 它是否本來就帶有 QA / quality assessment 結構
6. 它的 criteria 是否偏 task-oriented、method-oriented、dataset-oriented、publication-oriented、domain-oriented
7. 它有哪些容易導致 QA 設計失敗的點
8. 如果把它轉成 stage-specific QA，需要怎麼拆
9. 它對「生成 QA 用的 prompt」提供了哪些通用 pattern 或 anti-pattern

### F. 你不得偷懶的證明方式

你最後的報告裡，必須有一張**paper-by-paper 閱讀矩陣**，明確列出這 12 篇的：

1. paper id
2. 主題
3. criteria 結構特徵
4. metadata-only 條件類型
5. stage1 / stage2 可拆分性
6. QA 設計啟發
7. prompt 設計啟發
8. 可能污染或 drift 風險

如果你沒有交這張矩陣，就代表你沒有完成「詳讀所有其他 SR」這個要求。

## 四、你這次不是做一般分析，你要做的是「先大量閱讀，再自己迭代」

### 你必須做顯式多輪自我修正

你不能只給一版答案。  
你必須至少做 **4 個顯式階段**：

1. **Round 0：閱讀完成後的初始設計**
2. **Round 1：自我批判第一輪**
3. **Round 2：修正後再批判第二輪**
4. **Final：最終收斂版**

### 每輪都必須明確回答三件事

1. 我現在這一版的核心設計是什麼？
2. 這一版最大的缺點是什麼？
3. 下一輪我要改什麼？

### 你不能只做隱性思考

你要把 iteration 顯式寫出來，但不用暴露冗長隱性 chain-of-thought。  
請用**精簡但具體**的 revision log 呈現：

1. 本輪判斷
2. 本輪問題
3. 本輪修正

## 五、你最後要產出的「生成 QA 用的 prompt」必須滿足哪些條件

你設計的 prompt 不是一般描述，而是可以直接拿來餵模型、讓模型從 criteria 生成 stage-specific QA 的正式 prompt。它至少要滿足下面條件。

### 1. 以 current stage-split criteria 為唯一 criteria source

它必須明確要求：

1. Stage 1 QA 只能從 `criteria_stage1/<paper_id>.json` 出發
2. Stage 2 QA 只能從 `criteria_stage2/<paper_id>.json` 出發

不能混回：

1. `criteria_jsons/*.json`
2. 歷史 operational-v2 wording
3. 舊的 hidden hardening

### 2. 生成的是 QA spec，不是 verdict

prompt 必須明確要求輸出：

1. question
2. answer expectation
3. quote requirement
4. location requirement
5. state field（例如 present / absent / unclear）

但不能要求輸出 include / exclude verdict。

### 3. prompt 必須支援 evidence synthesis，而不是停在自由文本 QA

也就是說，你生成的 QA 不只應該有問題，還應該讓後續能穩定轉成欄位。  
所以 prompt 需要明確要求每個問題或每組問題對應到：

1. canonical field
2. expected state space
3. quote + location
4. missingness reason
5. conflict note（若適用）

### 4. prompt 必須支援 stage split，而不是單份 question set

它必須顯式要求：

1. Stage 1 只覆蓋 title/abstract observable conditions
2. Stage 2 補 full-text-only confirmatory conditions
3. Stage 2 要能接住 Stage 1 unresolved fields

### 5. prompt 必須避免 question-set contamination

它必須主動要求模型避免：

1. 把非目標例子寫成平行正向 example
2. 把 retrieval gate 當 screening gate
3. 把 historical hardening 悄悄寫回 question wording
4. 把不在 original criteria 的 derived rule 偽裝成 QA 必答條件

### 6. prompt 必須要求「metadata rule」與「screening QA」分層輸出

輸出結構至少要拆成：

1. metadata-only programmable rules
2. stage-specific screening QA
3. recommended synthesis fields

## 六、你最後要寫出的 QA 資產必須長什麼樣

你最後要自己用最終 prompt 寫出 QA。  
而且不是只交一個 generic skeleton；你要交**實際可用版本**。

### 必交 QA 資產

1. `2409` Stage 1 QA
2. `2409` Stage 2 QA
3. `2511` Stage 1 QA
4. `2511` Stage 2 QA

### 對 `2409`，你必須特別注意

你設計 QA 時，必須顯式處理下列 object boundary：

1. source object 是否是 natural-language text
2. target object 是否是 process model / process representation
3. NLP 是否是核心 extraction method
4. 非目標家族是否出現：
   - redesign
   - matching
   - prediction
   - sentiment analysis
   - label-only
   - generating natural text from processes

### 對 `2511`，你必須特別注意

你設計 QA 時，必須顯式處理下列 boundary：

1. ranking / A-B / pairwise preference
2. numeric rating 是否轉 ranking
3. preference 是 learning 還是 evaluation-only
4. 沒有 explicit comparison 時，是否存在 RL training loop for an audio model
5. multimodal including audio 的正確處理
6. survey / review 的正確處理

## 七、你最終報告的必備內容

你的最終報告必須至少包含下面這些章節。

### 1. current-state recap

要簡潔但準確說明：

1. current criteria source
2. current runtime prompt source
3. current metrics authority
4. current workflow invariants
5. 為什麼 evidence-QA 是 workflow-layer next step，而不是 criteria rewrite

### 2. 12 篇其他 SR 的 paper-by-paper 閱讀矩陣

這是強制章節，不能省略。

### 3. 從其他 SR 中歸納出的 prompt-design principles

至少要分成：

1. 可移植的正向 pattern
2. 應避免的 anti-pattern
3. 對 stage split 最有幫助的 pattern
4. 對 synthesis schema 最有幫助的 pattern

### 4. `criteria_mds/` 的定位重估

你要明確說清楚：

1. 它適合當什麼
2. 不適合當什麼
3. 哪些地方會造成 drift / contamination / structural mismatch

### 5. 你的 prompt 設計迭代紀錄

至少 3 輪 revision log。

### 6. 你的 final prompt

要完整可執行，不是片段。

### 7. 你的 final QA assets

最少是 `2409/2511 × stage1/stage2` 四份。

### 8. 你的最終建議

至少要回答：

1. 這份 prompt 是否足以作為 next experiment 的 generator prompt
2. 目前最應先跑哪個 ablation
3. 若只能做一件事，最值得先做什麼

## 八、你應該如何安排實際工作順序

請依下面順序做，不要跳步。

1. 讀 current-state 文件
2. 讀 candidate experiment 分析文件
3. 讀 `criteria_mds` 與 QA scaffold 文件
4. 詳讀那 12 篇其他 SR paper 與對應 `criteria_mds`
5. 做 12 篇 paper 的比較矩陣
6. 從比較矩陣歸納 prompt design principles
7. 先寫 prompt v0
8. 自我批判
9. 寫 prompt v1
10. 再自我批判
11. 寫 final prompt
12. 用 final prompt 寫出 `2409/2511 × stage1/stage2` 四份 QA
13. 最後再寫完整報告

## 九、你不能做的事

### 1. 不要把 historical file 說成 current production state

特別不要把：

1. `criteria_jsons/*.json`
2. `criteria_2409_stage_split`
3. `criteria_2511_opv2`

說成 current state。

### 2. 不要把新的 schema 或 prompt support 改名成 criteria

如果你的設計依賴：

1. evidence object
2. synthesis field
3. handoff field
4. reviewer support

請把它們叫做 workflow support，不要叫 criteria。

### 3. 不要只做 QA-only 就當作最終答案

你可以比較 QA-only，但最終設計必須明確處理 synthesis。

### 4. 不要在沒有完成 12 篇 SR 詳讀前就提早定稿

如果你還沒完成 paper-by-paper 矩陣，就不能說你已經完成任務。

### 5. 不要把「讀過 `criteria_mds` 摘要」當成「讀過 SR paper」

這次任務要求的是**完整閱讀其他 SR 論文本體**。

## 十、你最終回覆的格式要求

你的最終答案必須按下面順序輸出：

1. `Executive Summary`
2. `Current-State Recap`
3. `12-Paper Comparative Reading Matrix`
4. `Patterns And Anti-Patterns`
5. `Revision Log`
6. `Final Prompt For QA Generation`
7. `Generated QA Assets`
8. `Final Recommendations`

## 十一、你若做得不夠好，常見失敗模式有哪些

你必須主動避免下列失敗：

1. 只做高層抽象，不做 12 篇 paper 的實際比較
2. 只做 prompt，不實際寫 QA
3. 只做 QA，不定義 synthesis expectations
4. 混淆 current criteria 與 historical criteria
5. 用其他 SR 的偶然 wording，反向污染 current `2409/2511` question wording
6. 把 retrieval gate、metadata gate、screening evidence 問題混在一起
7. 沒有顯式 revision log
8. 沒有 paper-by-paper matrix

## 十二、最後一句最重要

如果你只能記住一件事，請記住：

> 你的任務不是快速提建議，而是先花大量時間把其他 12 篇 SR 讀透，從中抽出 QA-generation prompt design principles，經過多輪自我修正後，交付完整報告、最終 prompt、以及你自己用該 prompt 生成的 `2409/2511 × stage1/stage2` QA 資產。

現在開始執行。不要先停在 plan；直接開始閱讀與分析，除非你真的缺少檔案存取。

---

# 補充說明給人類使用者

上面那段已經是可直接貼給 ChatGPT 的主指令。  
它已經把幾件最容易漏掉的事都寫死了：

1. current-state 背景
2. 不可混淆的歷史/現行邊界
3. 必讀清單
4. 其他 12 篇 SR 的強制詳讀要求
5. 顯式多輪自我修正要求
6. 三個最終交付物
7. 至少 4 份必交 QA 資產

## 這份主指令背後的設計意圖

這份指令刻意把任務收斂成：

1. 用「其他 12 篇 SR」提供 prompt-design patterns
2. 用 current stage-split state 限制不能污染 criteria
3. 用 `2409/2511` 當最終 QA 實作目標

這樣做的原因是：

1. 你真正需要的是**生成 QA 的 prompt**
2. 不是只要一份泛泛談 prompt engineering 的報告
3. 也不是只想要一份理論上的 QA wishlist
4. 而是要一套可以真的落到 current experiment 的 prompt + QA 資產

## 「除了那四篇」的精確解讀

本文件把「詳讀所有 SR（除了那四篇）」實作成：

1. 那四篇 current-active papers 不列入「其他 SR corpus」的全量 comparative reading mandate
2. 但 current-state 文件與 target paper 的 active criteria 仍然必須讀
3. 真正要重度 comparative full-read 的，是剩下 12 篇其他 SR

這樣可以同時滿足：

1. 你要 ChatGPT 花很多時間讀完整個其他 SR corpus
2. 又不會讓它脫離 current `2409/2511` 這條主線

## 若你想再加嚴

你如果還想更兇，可以在貼上前手動再加一句：

> 在你完成 12 篇 paper-by-paper 閱讀矩陣之前，不要開始寫 final prompt，也不要開始寫 final QA。

