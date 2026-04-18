# SR Screening 進度更新與後續決策紀錄

日期：2026-04-15  
語言：繁體中文  
定位：進度/決策追蹤，不是新的中立文獻報告

---

## 1. 這份文件要解決什麼

這份文件是補在 `docs/brainstorming/SR_screening_4papers_route_to_f1_1_decision_report_zh.md` 後面的實驗追蹤紀錄。

目的只有三個：

1. 記錄目前實際做了哪些實驗
2. 記錄哪些方法其實還沒做完
3. 記錄接下來比較合理的先做順序

---

## 1.1 補充決議：`#2` 一律採 `paper-faithful A`

這是本文件後續閱讀的前提。

經重新查核 **Akinseloyin 2026 原 paper** 與其公開 **GitHub code** 後，對 `#2 criterion ledger` 的方法邊界做出以下決議：

- `#2` 若要稱為 `paper-faithful`，就只能走 `A`
- 這裡的 `A` 指的是：
  - 先把 review criteria 轉成對齊的 QA questions
  - 由多個 primary QA models 回答同一組問題
  - 再做 voting / debate / adjudication

以下做法從現在起一律視為 **絕對不行**：

1. 把 `Akinseloyin 2026` 說成 `2 juniors + 1 SeniorLead`
2. 用 human 或 Codex 來手工指定 `core / non-core criterion`
3. 用 `core / non-core criterion` 做 senior route gate，卻宣稱那是原 paper
4. 把 abstract-screening paper 直接改寫成 repo 的 stage1/full-text stage2，而不明說這是 extension

相關撤案文件：

- [SR_screening_criterion_ledger_only_experiment_spec_2409_2511_zh.md](/Users/xjp/Desktop/NLP_PRISMA_Reviews/docs/brainstorming/SR_screening_criterion_ledger_only_experiment_spec_2409_2511_zh.md)
- [SR_screening_criterion_ledger_multilane_flow_zh.md](/Users/xjp/Desktop/NLP_PRISMA_Reviews/docs/brainstorming/SR_screening_criterion_ledger_multilane_flow_zh.md)

paper-faithful 重寫請看：

- [Akinseloyin_2026_paper_faithful_rewrite_zh.md](/Users/xjp/Desktop/NLP_PRISMA_Reviews/docs/brainstorming/Akinseloyin_2026_paper_faithful_rewrite_zh.md)

---

## 2. 目前已經完成的實驗

本輪已完成一個新的隔離式實驗樹：

- 實驗根目錄：`single_reviewer_async_experiments/gpt5nano_all4_route_matrix_2026-04-14`
- 完整 run：`single_reviewer_async_experiments/gpt5nano_all4_route_matrix_2026-04-14/runs/20260414_full_gpt5nano_async_matrix`

本輪固定條件：

- 模型：`gpt-5-nano`
- reviewer 架構：`single reviewer`
- API 模式：`async`
- 不用 batch
- 共跑四篇 paper：`2307.05527`、`2409.13738`、`2511.13936`、`2601.19926`

本輪已完整跑完的四個 arms：

1. `direct_2stage_async`
2. `merged_ledger_2stage_async`
3. `merged_ledger_verify_async`
4. `merged_ledger_verify_retrieval_async`

完成狀態：

- `4 arms x 4 papers = 16` 組都完成
- `stage1_metrics.json`：16 份
- `combined_metrics.json`：16 份
- `final_results.json`：16 份
- `request_log.jsonl`：6591 筆
- `response_log.jsonl`：6591 筆
- `failure_log.jsonl`：不存在，視為 0 筆失敗

---

## 3. baseline 口徑修正

這一輪討論後，baseline 必須明確定義為：

- `gpt-5-nano`
- `single reviewer`
- `direct_2stage_async`

`current authority` 不是這輪實驗的 baseline。  
`current authority` 只是 repo 的正式參考分數，用來看和現行主線差多少，不該拿來當這輪 workflow 比較的基準。

---

## 4. 目前實驗結果的白話結論

如果只看這輪 `gpt-5-nano` 單審查者 baseline 的提升：

- `merged_ledger_2stage_async` 是目前最穩的改法
- `merged_ledger_verify_async` 不穩，不能當目前主線
- `merged_ledger_verify_retrieval_async` 比純 verification 好，但仍然只是小幅增益，不是質變

四篇 paper 的最佳 `combined F1`（只在本輪四個 arms 內比）：

| Paper | 本輪最佳 arm | Combined F1 |
| --- | --- | ---: |
| `2307.05527` | `merged_ledger_verify_async` | `0.8477` |
| `2409.13738` | `merged_ledger_2stage_async` | `0.8936` |
| `2511.13936` | `merged_ledger_verify_retrieval_async` | `0.9062` |
| `2601.19926` | `merged_ledger_2stage_async` | `0.9412` |

但這裡要注意：

- 這些結果只是在 `gpt-5-nano` 上比較 workflow
- 不代表這條線已經能逼近最終的 `F1 = 1`
- `gpt-5-nano` 的角色比較像便宜 baseline，不是最終上限模型

---

## 5. 第八章方法，目前到底做到哪裡

以下對照的是 `SR_screening_4papers_route_to_f1_1_decision_report_zh.md` 第八章的 1-5。

### 先把幾個名詞講死

#### `multi-lane` 是什麼

白話：不是所有 case 都走同一條判定路。

最簡單的理解是：

- 低風險 case：走便宜、快速、直接結案的 lane
- 高風險 case：走更慢、更貴、但更可靠的 lane

所以 `multi-lane` 的重點不是「一定要很多模型互相聊天」，而是：

- 先分流
- 不同類型的 case 走不同決策路

`multi-lane` 可以用多個 reviewer 實作，也可以用同一個模型的不同 pass 實作。  
但如果目標是高可靠 final path，通常最後會長成多 reviewer 或 senior adjudication 的形式。

#### `SeniorLead` 是什麼

白話：不是神祕的 judge，而是 repo 現行 production workflow 裡明確存在的第三位 reviewer 角色。

它在 repo 目前的定義是：

- 先有兩個 junior reviewer 做第一輪判斷
- 只有邊界 case 才送 `SeniorLead`
- `SeniorLead` 看的是：
  - 原始輸入
  - 兩個 juniors 的輸出
  - 兩個 juniors 的分數
- 然後由 senior 直接做最後裁決

所以 `SeniorLead` 的本質是：

- adjudicator
- tie-breaker
- boundary-case resolver

不是：

- 自由辯論 agent
- 額外的 hidden criteria
- 任意改 criteria 的角色

#### `判定標準` 在這裡是什麼

目前 repo 有兩層判定標準：

1. `criteria_stage1/<paper_id>.json`
2. `criteria_stage2/<paper_id>.json`

workflow 只能在這兩層 criteria 上做 support，不能偷偷再加第三套正式 criteria。

分數對應固定是：

- `1-2 -> exclude`
- `3 -> maybe`
- `4-5 -> include`

在 merged ledger 線裡，每條 criterion 另外會被標成：

- `YES`
- `NO`
- `UNCLEAR`

然後再由這張 criterion ledger 推出 `stage_score`。

### `#1 verification routing`

白話：把危險 case 挑出來，不讓它在第一輪太早被判死。

目前簡單版已做：

- 在 `merged_ledger_verify_async`
- 在 `merged_ledger_verify_retrieval_async`
- routed case 會進 second pass

完整版還沒做：

- 還沒有真正的 `multi-lane / senior adjudication` 版本
- 還沒有更精細的 route policy 比較
- 目前只是同一個 `gpt-5-nano` 再看一次，不算高可靠複核

### `#4 paper-specific semantic assets`

白話：每篇 paper 都有自己的語義地雷，先把容易搞混的邊界整理出來。

目前簡單版已做：

- 有 `assets/paper_profiles/*.json`
- 內含 `core_fit_terms`
- `non_target_terms`
- `semantic_traps`
- `retrieval_priority_terms`
- `verification_focus`

完整版還沒做：

- 還沒有更厚的正例/反例庫
- 還沒有 criterion-level 的 near-miss 整理
- 還沒有把典型誤判句型與邊界案例做成更完整資產

### `#5 stage-aware calibration`

白話：第一關、第二關、verification 不該用同一種判法，要故意調成不同保守度。

目前狀態：

- 還沒有正式跑
- 這次雖然有 `stage1 / stage2 / verification` 三個 phase
- 但這不等於已經做了 calibration 實驗

什麼才算真的做了 `#5`：

- 明確比較不同 stage 的保守度設定
- 明確比較不同 route/overturn 規則
- 至少有 2-3 組可比設定，不是只有一組 prompt

結論：

- `#5` 目前是「概念上存在」
- 不是「實驗上已完成」

---

## 5.1 這次簡單版實驗到底測了什麼

這次四個 arms 測的東西如下。

### `direct_2stage_async`

白話：最普通的單審查者兩階段直審。

它做的事：

- Stage 1：只看 title/abstract，直接給一個 `1-5`
- Stage 2：只讓 Stage 1 的 `include/maybe` 進全文，再直接給一個 `1-5`
- 不做 ledger
- 不做 verification
- 不做 targeted retrieval

它測的是：

- 最便宜、最直觀的 single-reviewer baseline 到底有多強

### `merged_ledger_2stage_async`

白話：先逐條填 criteria 檢查表，再決定收不收。

它做的事：

- Stage 1：對每條 criterion 回 `YES/NO/UNCLEAR`
- Stage 2：全文再做一次同樣的 criterion ledger
- 最後根據 ledger 推 `stage_score`
- 不做 verification

它測的是：

- 單審查者如果不靠整體印象，而是先逐條檢查，會不會更穩

### `merged_ledger_verify_async`

白話：先做 ledger，遇到危險 case 再讓同一個模型複核一次。

它做的事：

- 先跑 `merged_ledger_2stage_async`
- 如果 case 符合 route 規則，就再進 verification pass
- verification pass 還是同一個 `gpt-5-nano`
- verification 結果會覆蓋原 verdict

它測的是：

- 在不增加第二個 reviewer 的情況下，光靠 second pass 值不值得

### `merged_ledger_verify_retrieval_async`

白話：先做 ledger，危險 case 複核時不看整段 head/tail，而改看精選段落。

它做的事：

- 先跑 `merged_ledger_verify_async`
- 但 verification 時不給整段截斷全文
- 改給 snippet pack
- snippet pack 由 unresolved criterion 與 paper profile 來挑段落

它測的是：

- routed case 若改成看較精準的證據片段，會不會比直接塞全文更好

### 這四個 arms 沒有測什麼

這四個 arms 都沒有測：

- 真正的多 reviewer routed multi-lane
- 真正的 `SeniorLead` adjudication
- 正式的 stage-aware calibration sweep

所以這次實驗的本質是：

- `single reviewer`
- `gpt-5-nano`
- workflow 元件的簡化版比較

不是：

- production multi-reviewer 的重建
- 高可靠 final path 的完整實作

---

## 5.2 這次 simple verification 的 route 規則是什麼

這次簡單版會把 case 送進 verification，只要出現下面任一情況：

1. `manual_review_needed = true`
2. 任一 criterion 是 `UNCLEAR`
3. inclusion / exclusion evidence 彼此衝突
4. Stage 1 先判 `exclude`，但仍有未解的 inclusion QA 衝突或明顯證據不足
5. 命中該 paper 的 `semantic_traps`

白話：

- 模型自己說「我不確定」
- ledger 裡還有條件判不清
- 證據互相打架
- 看起來像過早排除
- 或者踩到這篇 paper 最常見的語義地雷

就會被送去第二次看。

但要再次強調：

- 這個第二次看，仍然是同一個 `gpt-5-nano`
- 所以它是 `single-reviewer multi-pass`
- 不是 `multi-reviewer multi-lane`

---

## 5.3 `#1 verification routing` 的完整細節與發想

### 來源依據到底是什麼

這一項不是我自己瞎編 prompt。

它的來源是四塊拼起來的：

1. `Nama 2021`  
   核心訊息：不是所有排除都要同樣處理；要看排除理由決定哪些必須 second-review verification。
2. `Noel-Storr 2021`  
   核心訊息：便宜前哨站 + 更可靠後續 lane 的 hybrid workflow 是合理的。
3. `Akinseloyin 2026`  
   核心訊息：若要做 multi-agent，不該先自由辯論，而是先回答對齊的 criterion questions，再聚合或 adjudicate。
4. repo 目前已存在的 `SeniorLead` production pattern  
   核心訊息：兩個 juniors + 一個 senior adjudicator，本來就是現有 repo 的正式結構。

所以 `#1` 的完整版不是某一篇 paper 的逐字 prompt 複製。  
它是：

- 方法上對齊 `Nama 2021` 的 verification routing
- 結構上對齊 `Akinseloyin 2026` 與 repo 既有 `SeniorLead`
- 再把它翻譯成適合 NLP / Speech criteria 的 workflow

### 哪些部分是 paper-faithful，哪些是我們的延伸

#### paper-faithful 的部分

- 依排除理由決定是否複核
- 先便宜過濾，再把高風險 case 送去更可靠 lane
- 若有多 reviewer，應先對齊 criterion questions，再做 adjudication

#### 我們自己的延伸

- 把生醫 exclusion category 翻成 NLP / Speech 的風險類別
- 把 repo 既有 `SeniorLead` 接到這個 routing 思路裡
- 把 routed case 的輸入換成 criterion ledger + focused evidence，而不是自由文字

### 完整版應該長什麼樣

完整版的 `#1`，白話流程應該是：

1. `cutoff / metadata gate`
   - 先排掉時間窗不符、明顯 publication form 不符、明顯非 primary research 之類的低風險排除
2. `cheap first-pass lane`
   - 先讓便宜 reviewer 做第一輪 title/abstract 或 stage1 ledger
3. `routing decision`
   - 看這篇是低風險排除、語義邊界模糊、關鍵 evidence 缺失、還是 reviewer 之間有分歧
4. `reliable verification lane`
   - 高風險 case 才送去更可靠 lane
   - 這裡的更可靠 lane 可以是 `SeniorLead`
   - 也可以是多 reviewer 後再由 senior 收斂
5. `final adjudication`
   - verification 結果覆蓋 cheap lane
   - 同時保存 audit trail

### 在 NLP / Speech 這裡，什麼 case 應該 route

白話地說，應該 route 的不是「所有不確定」，而是這些危險 case：

- 看起來 topic 很像，但核心 task boundary 不清
- output modality 看起來可能不符，但不能只憑關鍵字判死
- paper 提到 preference、ranking、syntax、process 等字，但關係不清楚
- stage1 想排除，但仍有未解的 inclusion QA 衝突或明顯證據不足
- reviewer 之間分歧明顯

### `SeniorLead` 在完整版 `#1` 裡到底做什麼

`SeniorLead` 不是第二個 criteria。  
它的工作應該只有三件事：

1. 看便宜 lane 留下來的 ledger 與 evidence
2. 決定哪些 criterion 真的成立、哪些只是 topic similarity
3. 對 routed case 做 final adjudication

所以完整版 `#1` 的重點不是「再加一個很強的 prompt」，而是：

- 什麼 case 才配進 senior lane
- senior 看什麼
- senior 可以覆蓋什麼

### 這次簡單版已做了什麼

這次只做了最小版：

- routed case 會進 second pass
- 但 second pass 還是同一個 `gpt-5-nano`
- 沒有真正獨立的 senior lane
- 沒有真正多 reviewer aggregation

所以這次做的是：

- `single-reviewer multi-pass verification`

不是：

- `full routed multi-lane adjudication`

---

## 5.4 `#2 criterion ledger` 的完整細節與發想

### 來源依據到底是什麼

這一項也不是我自己亂發明。

主要來源是：

1. `Akinseloyin 2024`
   - 把 criteria 拆成最多幾個 QA 問題
2. `ReviewCopilot 2025`
   - 先抽結構化 evidence，再做決策
3. `Akinseloyin 2026`
   - 若有多 agent，先讓大家回答同一組 criterion questions，再做 aggregation

所以 `#2` 的核心不是 prompt 文采，而是：

- criteria 要先拆開
- 每條 criterion 都要留下 evidence
- 最後決策應該從 ledger 推出，不是直接靠 impression

### 哪些部分是 paper-faithful，哪些是我們的延伸

#### paper-faithful 的部分

- 把 eligibility 拆成多個明確問題
- 每題分開回答
- 再由這些回答推到整體判斷

#### 我們自己的延伸

- 把 QA 改成 repo 友善的 `criterion_assessments[]`
- 用 `YES / NO / UNCLEAR` 而不是醫學 paper 的原始標籤
- 強制保留 `supporting_quotes / counter_quotes / missingness_reason`

### 完整版應該長什麼樣

完整版 `#2` 的 ledger，至少要有：

- `criterion_id`
- `criterion_type`（inclusion / exclusion）
- `stage_observability`（stage1 可看 / stage2 才能確認）
- `supporting_quotes`
- `counter_quotes`
- `missingness_reason`
- `local_status`
- `criterion_notes`
- `decision_policy link`

白話：不是只說「這篇像不像」，而是逐條記錄：

- 哪條 criteria 有證據
- 哪條 criteria 被反證
- 哪條 criteria 只是目前還看不到

### 完整版還應該多什麼

- Stage 1 與 Stage 2 的 handoff 必須對齊
- `UNCLEAR` 不能直接混成 `NO`
- routed case 要能讓 senior 直接看到哪幾條最關鍵
- 若有多 reviewer，大家必須共用同一張 ledger schema

### 這次簡單版已做了什麼

這次已經做了基本版：

- 每條 criterion 都有 `YES / NO / UNCLEAR`
- 有 `supporting_quotes`
- 有 `counter_quotes`
- 有 `missingness_reason`
- 最後再推 `stage_score`

但還沒做到：

- 真正的 multi-reviewer shared ledger
- 更成熟的 stage1 -> stage2 handoff 規格
- 更強的 criterion-level error analysis 迭代

---

## 5.5 `#3 targeted full-text retrieval` 的完整細節與發想

### 來源依據到底是什麼

這一項沒有對應單一篇 paper 的逐字 prompt。

它的主要依據是：

1. `ReviewCopilot 2025`
   - 強調要先抽 evidence，再做決策
2. `A4SLR 2025`
   - 強調 evidence pipeline 是模組化的，不是全文一把梭
3. 本 repo 與本報告對四篇 paper 的錯誤分析
   - 已知很多錯誤不是因為模型不會想，而是根本沒看到對的段落

所以 `#3` 更像：

- method-faithful 的 evidence-pipeline 延伸

不是：

- 某篇 paper 可直接複製的 exact retrieval prompt

### 哪些部分是 paper-faithful，哪些是我們的延伸

#### paper-faithful 的部分

- evidence extraction 應該先於最終 decision
- 不同模組處理不同 evidence 任務

#### 我們自己的延伸

- 不是用 PICOS，而是用 criteria unresolved state 來決定抓哪些段落
- 加入 section priors，如 `method / experiment / evaluation`
- 讓 verification lane 優先吃 snippet pack，而不是整段 head/tail

### 完整版應該長什麼樣

完整版 `#3` 的流程應該是：

1. 先看哪幾條 criterion 還沒解開
2. 根據這些 unresolved criteria 產生 retrieval query
3. 在全文中優先找：
   - methods
   - experiments
   - evaluation
   - task definition
4. 再把這些片段組成帶 provenance 的 snippet pack
5. verification 或 stage2 reviewer 只看這包高價值證據

白話：

- 不是讓模型看更長
- 而是讓模型看更對

### 這次簡單版已做了什麼

這次只做了窄版：

- 只在 `merged_ledger_verify_retrieval_async` 做
- 只對 routed 的 Stage 2 case 啟用
- 用 unresolved criterion + paper profile keyword 打分
- 固定把 title/abstract 帶進去
- 額外偏好 `method / experiment / evaluation`

但還沒做到：

- 比較不同 retrieval selector
- 比較不同 section priors
- 更完整的 provenance / snippet audit
- 在 stage2 主路徑而不只 verification 路徑使用

---

## 5.6 `#4 paper-specific semantic assets` 的完整細節與發想

### 來源依據到底是什麼

`#4` 最不是「某一篇 paper 可直接抄 prompt」的項目。

它的主要依據是：

1. `SR_screening_ultradeep_report_2026_zh.pdf` 對每種方法與每篇 paper 的診斷
2. `SR_screening_4papers_route_to_f1_1_decision_report_zh.md` 第 6 章的逐篇診斷
3. 這次實驗與 repo 歷史結果的 error pattern

所以 `#4` 的本質是：

- 研究導向的 repo-specific knowledge asset

不是：

- 某篇外部 paper 已經替你寫好的模板

### 為什麼它不是亂編

因為這四篇的錯誤邊界本來就不一樣：

- `2409`：`process extraction` vs `redesign / matching / prediction`
- `2511`：`preference enters learning loop` vs `preference only for evaluation`
- `2307`：`output entirely audio`
- `2601`：`Transformer LM + empirical syntax analysis`

這些不是任意想像，而是報告與結果分析反覆指出的主戰場。

### 完整版應該長什麼樣

完整版 `#4` 不應只有幾個 keyword，而應至少包含：

- `core_fit_terms`
- `non_target_terms`
- `semantic_traps`
- `near_miss_families`
- `positive_evidence_cues`
- `negative_evidence_cues`
- `criterion_specific_probes`
- `retrieval_priority_terms`
- `verification_focus`
- `example include patterns`
- `example exclude patterns`

白話：

- 哪些詞看起來像，但其實不是
- 哪些句型一看到就知道要更小心
- 哪些關係一定要被明確證明
- 哪些 paper 一看就該 route，不該直接判死

### 這次簡單版已做了什麼

這次只做了輕量版 `paper_profiles/*.json`：

- `core_fit_terms`
- `non_target_terms`
- `semantic_traps`
- `retrieval_priority_terms`
- `verification_focus`

這已經比完全沒有好，但還不是完整版。  
完整版還缺：

- 更厚的正反例
- near-miss 類型整理
- criterion 級別 probe questions
- 與 stage1/stage2/verification 明確綁定的使用規則

---

## 5.7 `#1~#4` 到底哪些來自 paper，哪些是我們自己的設計

| 方法 | 直接來源 | 不是直接照抄的部分 | 目前判斷 |
| --- | --- | --- | --- |
| `#1 verification routing` | `Nama 2021` + `Noel-Storr 2021` + `Akinseloyin 2026` + repo `SeniorLead` | NLP / Speech 的 route 類別設計、senior lane 接法 | 有明確方法依據，不是亂編 |
| `#2 criterion ledger` | `Akinseloyin 2024/2026` + `ReviewCopilot 2025` | ledger schema 的具體欄位與 repo 對接方式 | 有明確方法依據，不是亂編 |
| `#3 targeted full-text retrieval` | `ReviewCopilot 2025` + `A4SLR 2025` + repo error analysis | unresolved-criterion retrieval、section priors、snippet pack 規則 | 有方法依據，但工程細節主要是我們自己的延伸 |
| `#4 paper-specific semantic assets` | 深度報告逐篇診斷 + 決策報告逐篇診斷 + repo error analysis | 資產結構、欄位設計、如何餵給 ledger/retrieval/verification | 主要是我們自己的研究綜合，不是外部 paper 的現成模板 |

---

## 6. 為什麼這次會這麼花錢

本輪完整 run 的可見成本約為：

- `$16.95`

這個數字來自 `response_log.jsonl` 內每筆 `usage.cost` 的總和。

白話原因如下：

1. 總 request 太多：6591 筆
2. `stage2_review` 很肥，平均每筆輸入很長
3. verification 額外多了 1608 筆 request
4. 輸出不是只有 yes/no，而是很長的結構化 JSON
5. `2601.19926` 的候選數量特別大，單篇就吃掉約 `$9.46`

目前看起來，主因不是單純「thinking token 爆掉」，而是：

- request 數量多
- full text / snippet pack 長
- 結構化輸出長
- verification 會把總 request 再往上堆

也就是說，成本大頭主要是明面上的輸入輸出體積與重跑次數，不是目前可直接證明的 hidden reasoning token。

---

## 7. 若只做 `2409 + 2511`，預估成本

若後續只針對：

- `2409.13738`
- `2511.13936`

且維持：

- `gpt-5-nano`
- `single reviewer`
- `async`

那預估如下：

### 只做一組整合版 `#1 + #4`

- 約 `$1.2 ~ $1.5`

### 若把 `#5` 也當成正式 calibration 去做

因為 calibration 至少要跑 2-3 組可比設定，預估：

- 小 sweep：`$3.8 ~ $4.8`
- 若組數再多：`$6+`

所以若目前重點是先省錢，最合理的順序是：

1. 先做 `2409 + 2511`
2. 先做 `#1 + #4`
3. 先不要正式開 `#5` sweep

---

## 8. 目前決策

截至 2026-04-15，當前較合理的決策是：

1. 不再把 `current authority` 當這輪 `gpt-5-nano` single-reviewer 實驗的 baseline
2. 承認第八章的 1-5 目前只做了縮小版，不是完整版
3. 若要先控制成本，下一步優先考慮只打 `2409 + 2511`
4. 在 `2409 + 2511` 上優先做：
   - `#1 verification routing`
   - `#4 paper-specific semantic assets`
5. `#5 stage-aware calibration` 先不當下一步主軸，除非願意接受額外的實驗成本

---

## 9. 下一步追蹤用的簡短結論

一句話版：

- `#1` 做過簡單版，還沒做完整版
- `#4` 做過輕量版，還沒做完整版
- `#5` 還沒有正式跑過

下一步若以成本優先，建議先做：

- `2409 + 2511`
- `#1 + #4`
- 暫緩 `#5`
