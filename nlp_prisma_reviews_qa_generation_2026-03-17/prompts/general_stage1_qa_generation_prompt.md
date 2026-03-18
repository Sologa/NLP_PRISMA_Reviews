# General Prompt: Stage 1 QA Generation

你現在的任務不是判定某一篇候選研究是否應該納入，而是**為一篇 systematic review / survey 生成可重用、source-faithful 的 Stage 1 QA 問題集**。

## 任務定義
Stage 1 的角色是：  
只根據 **title / abstract / keywords / 首頁可直接觀測的書目訊息**，生成一組 evidence-extraction QA。  
你必須先完整閱讀整篇 SR / review PDF，理解原作者真正的 eligibility boundary；但輸出時只能保留 **Stage 1 可觀測** 的問題，並把不穩定或必須靠全文才能確認的條件 defer 給 Stage 2。

## 輸入
你會收到下列資料：
1. `SR_TITLE`
2. `SR_PDF_OR_FULLTEXT`
3. `SR_CRITERIA_TEXT`  
   - 可能是原文 eligibility / inclusion / exclusion 段落
   - 也可能是整理後的 criteria markdown / json
4. `STAGE_DEFINITION = Stage 1`
5. （可選）`CURRENT_STATE_NOTES`
6. （可選）`HISTORICAL_NOTES`  
   - 只能做背景比較，不可當 current production criteria

## 必須遵守的原則
1. **先讀完整篇 SR PDF，再生成 QA**  
   不可只看 abstract、title、criteria 摘要，或只靠 criteria_mds 就直接寫題目。
2. **source-faithful，不重寫 formal criteria**  
   你是在生成 QA workflow support，不是在改寫 criteria。
3. **Stage 1 只保留可觀測條件**  
   若某條件無法穩定由 title/abstract 判定，必須 defer 到 Stage 2；不得發明 proxy。
4. **顯式分層 metadata-only vs content-based**  
   - metadata-only：年份、語言、peer-review、venue type、page count、citation threshold、full-text availability、source reputation 等  
   - content-based：title/abstract 可以直接看到的 topic / task / modality / output / study-type 訊號
5. **不直接要求 include/exclude verdict**
6. **不可把 retrieval gate 混入 screening QA**
7. **不可把 historical hardening 偷偷回流**
8. **不可把 single-paper 的負向例子寫成 general rule**
9. **不可產生只有自由文本、卻無法支援後續 synthesis 的問題集**

## 你的工作流程
請嚴格依序做：

### Step 1 — 讀 SR 全文
- 通讀整篇 SR
- 找出正式 eligibility / inclusion / exclusion / study-selection / quality-assessment / publication-form 要求
- 區分：
  - 真正的 formal eligibility
  - corpus-construction / retrieval / search-strategy heuristics
  - historical hardening 或 performance-oriented operationalization

### Step 2 — 抽出三層條件
把條件拆成三類：
1. `metadata_only_conditions`
2. `title_abstract_observable_conditions`
3. `full_text_only_or_confirmatory_conditions`

### Step 3 — 只為前兩類生成 Stage 1 QA
- `metadata_only_conditions` 要列在獨立區塊
- `title_abstract_observable_conditions` 要列在主 QA 區塊
- `full_text_only_or_confirmatory_conditions` 不得硬塞進 Stage 1；只能在 handoff 欄位註明 defer to Stage 2

### Step 4 — 生成 synthesis-ready QA
每一題必須包含以下欄位：
- `qid`
- `criterion_family`
- `question`
- `expected_answer_form`
- `quote_requirement`
- `location_requirement`
- `state`
- `missingness_reason`
- `stage2_handoff`

其中：
- `state` 只能是：`present | absent | unclear`
- `missingness_reason` 為選填，但當 `state = unclear` 時應提供原因
- `quote_requirement` 必須要求 reviewer 引用最短、最直接的 title/abstract 證據
- `location_requirement` 必須限制在 title / abstract / keywords / 首頁 bibliographic block
- `stage2_handoff` 必須說明：若 Stage 1 不足，Stage 2 應確認什麼

## 輸出格式
請輸出為 Markdown，並且固定使用以下結構：

### 1. Stage 1 design intent
簡要說明你如何把原 SR 的單層 eligibility 投影成 Stage 1。

### 2. Metadata-only checks
使用表格，欄位如下：
`qid | criterion_family | question | expected_answer_form | quote_requirement | location_requirement | state | missingness_reason | stage2_handoff`

### 3. Title/Abstract-observable QA
同樣使用上面那組欄位。

### 4. Handoff policy
簡述：
- 哪些條件被 defer 到 Stage 2
- 為何 defer
- 遇到 mixed signals 時該如何記錄

### 5. Non-goals
至少列出：
- 不直接做 include/exclude verdict
- 不重寫 formal criteria
- 不把 paper-specific examples generalize
- 不把 retrieval / corpus-building heuristics 偽裝成 eligibility

## 額外禁止事項
- 不可把「某些 paper 常見的排除例子」當成任何新 SR 的固定模板
- 不可因為 abstract 太短，就自動把 candidate 排除
- 不可把外部 ranking、citation、source prestige 當成 topic fit 的替代品
- 不可生成第三層 hidden policy / hidden guidance
- 不可把 workflow support 說成 canonical criteria

## 品質檢查清單
在輸出前自查：
1. 我有沒有真的先讀完 SR PDF？
2. 我有沒有把 metadata-only 與 title/abstract observable 分開？
3. 我有沒有把 full-text-only 條件錯塞進 Stage 1？
4. 我有沒有暗示 include/exclude verdict？
5. 我有沒有把 historical hardening 或 retrieval gate 混進來？
6. 我的每一題是否都有結構化欄位，可供後續 synthesis 使用？

如果有任何一項答案是否定，就重寫後再輸出。
