# General Prompt: Stage 2 QA Generation

你現在的任務不是做最終納入判定，而是**為一篇 systematic review / survey 生成 source-faithful 的 Stage 2 canonical / confirmatory QA 問題集**。

## 任務定義
Stage 2 的角色是：  
在完整閱讀候選研究全文之後，用**full-text evidence** 關閉 Stage 1 未解決的欄位，並確認原 SR 的 canonical eligibility。  
你必須先完整閱讀整篇 SR / review PDF，理解原作者真正的 eligibility boundary；然後根據該邊界生成 Stage 2 QA。  
Stage 2 可以引用 Stage 1 handoff，但**不能把 workflow support、historical hardening 或 hidden guidance 偽裝成新的 formal criteria**。

## 輸入
你會收到：
1. `SR_TITLE`
2. `SR_PDF_OR_FULLTEXT`
3. `SR_CRITERIA_TEXT`
4. `STAGE_DEFINITION = Stage 2`
5. `STAGE1_QA_OR_HANDOFF`（可選，但建議提供）
6. （可選）`CURRENT_STATE_NOTES`
7. （可選）`HISTORICAL_NOTES`

## 必須遵守的原則
1. **先讀完整篇 SR PDF，再生成 QA**
2. **Stage 2 是 canonical / confirmatory，不是自由發揮**
3. **承接 Stage 1 unresolved fields**
4. **不直接要求 include/exclude verdict**
5. **metadata gate 與全文語義確認必須分開**
6. **允許 paper-specific negative families，但只能留在該 SR 的 QA 裡**
7. **不可把 retrieval gate、source prestige、citation heuristics 偽裝成 canonical eligibility**
8. **不可把 historical operational hardening 回寫成 current criteria**
9. **必須能記錄衝突，而不是掩蓋衝突**

## 你的工作流程

### Step 1 — 讀 SR 全文並恢復 canonical eligibility
- 找出原 SR 的正式 inclusion / exclusion / study-selection / quality-assessment 條件
- 若原 SR 本來就是單層 eligibility，則用 source-faithful 方式將其投影成 Stage 2 confirmatory QA
- 若 repo 已有 current Stage 1 / Stage 2 criteria，應優先尊重 current Stage 2 canonical file

### Step 2 — 接住 Stage 1 handoff
將 Stage 1 中的 unresolved / deferred items 整理為：
- publication-form confirmation
- language / date / venue / page-count / peer-review / citation / quality-score 等 metadata closure
- task centrality / modality / output form / primary-study status / empirical validation 等 full-text closure
- abstract 與正文之間的衝突

### Step 3 — 生成 Stage 2 QA
每一題必須包含：
- `qid`
- `criterion_family`
- `question`
- `expected_answer_form`
- `quote_requirement`
- `location_requirement`
- `state`
- `missingness_reason`
- `conflict_note`
- `resolves_stage1`

其中：
- `state` 只能是：`present | absent | unclear`
- `missingness_reason` 在 `unclear` 時必須填
- `conflict_note` 用來記錄摘要 vs 正文、方法 vs 實驗、或 metadata vs 正文的衝突
- `resolves_stage1` 要說明這題在承接哪個 Stage 1 unresolved family

## 輸出內容的強制分層
你必須固定拆成兩個區塊：

### A. Metadata and bibliographic confirmation
這裡放：
- year / date window
- language
- venue / peer-review
- page count
- publication type
- full-text availability
- citation threshold
- venue ranking
- quality assessment threshold
- source reputation / corpus note  
但要注意：**若這些不是 canonical eligibility，只能明確標成 note，不得冒充 hard criterion。**

### B. Full-text / confirmatory QA
這裡放：
- primary study vs review
- exact task centrality
- modality / input / output confirmation
- model / method family confirmation
- empirical validation
- learning-vs-evaluation distinction
- subtle boundary cases
- paper-specific negative family resolution

## 輸出格式
請輸出為 Markdown，並固定使用：

### 1. Stage 2 design intent
說明你如何從原 SR eligibility 得到 Stage 2 canonical / confirmatory QA。

### 2. Metadata and bibliographic confirmation
表格欄位：
`qid | criterion_family | question | expected_answer_form | quote_requirement | location_requirement | state | missingness_reason | conflict_note | resolves_stage1`

### 3. Full-text / confirmatory QA
同樣使用上面那組欄位。

### 4. Conflict-handling policy
至少說明：
- 摘要與正文衝突時怎麼記
- metadata 與正文衝突時怎麼記
- 不足以判定時何時保留 `unclear`

### 5. Non-goals
至少列出：
- 不直接做 include/exclude verdict
- 不把 workflow support 偽裝成 criteria
- 不把 historical hardening / retrieval gate 偷渡成 canonical eligibility
- 不把 paper-specific negative families 升級成 general policy

## 額外禁止事項
- 不可把 Stage 2 做成自由散文摘要
- 不可只寫「請確認全文是否符合 criteria」這種空泛題
- 不可省略 `conflict_note`
- 不可把 title/abstract proxy 當成全文 confirmation
- 不可把 metadata 的缺失直接轉成 topic-level exclusion
- 不可把 current-state 以外的 historical criteria 說成正式權威

## 品質檢查清單
輸出前自查：
1. 我有沒有真的先讀完 SR PDF？
2. 我有沒有把 metadata closure 與 full-text semantics 分開？
3. 我有沒有承接 Stage 1 unresolved fields？
4. 我有沒有避免直接輸出 include/exclude verdict？
5. 我有沒有避免把 historical hardening、retrieval heuristics、source prestige 假裝成 canonical criteria？
6. 我是否為每一題提供了能支援後續 synthesis 的結構化欄位？
7. 我是否提供了明確的 conflict handling？

如果任何一項答案是否定，就重寫後再輸出。
