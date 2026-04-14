# 四篇 SR 一起把 Screening 推向 F1=1 的決策報告

日期：2026-04-14  
定位：決策報告，不是中立文獻綜述  
語言：繁體中文 Markdown  
範圍：只討論路線、workflow、評估口徑、方法重疊與研究排序；不實作 code，不改 repo 邏輯，不產生 prompt bundle。

---

## 1. 執行摘要

這份報告要直接回答三件事。

第一，現在最卡的不是模型名字，而是 `workflow support layer`。  
白話講：不是因為模型不夠大，而是因為目前很多 case 被要求在錯的階段、用錯的證據、走錯的決策路徑做判斷。

第二，如果目標是四篇 SR 一起穩定進步，而且最後逼近 `final post-verification F1 = 1`，主路徑應該是：

1. `verification routing`  
   白話解釋：先把「可以放心快速排掉的 case」和「很容易誤殺的 case」分開，後者送去更嚴格的複核路徑。
2. `criterion ledger`  
   白話解釋：不要先問模型「收不收」，先逼它逐條填一張 criteria 檢查表，再做最後決定。
3. `targeted full-text retrieval`  
   白話解釋：不要把固定截斷的全文一股腦塞進去；要根據「現在缺哪條證據」去抓對的段落。

第三，最不值得先做的不是 `reviewer 數量`，而是把希望押在：

- 只換更大模型
- 只拉高 reasoning effort
- 讓多個 agent 自由辯論但沒有共用 evidence schema

因為這些做法有時會在單一 paper 上出現漂亮 run，但很難四篇一起穩定，不足以支撐你要的最終目標。

本報告的核心判斷如下：

- `2307.05527` 與 `2601.19926` 目前觀察上仍是 current multi-reviewer 最強，不應為了救低分 paper 去全域改壞它們。
- `2409.13738` 的主戰場是語義邊界，不是單純 recall。
- `2511.13936` 的主戰場是 relation 判斷，不是關鍵字檢索。
- `single reviewer` 適合 baseline、cheap triage、comparison arm。
- `three-reviewer / routed multi-lane` 才是高可靠 final path。

---

## 2. 先把目標定義清楚

如果不先定義清楚「你到底要哪一種 F1=1」，後面會一直在不同口徑之間打架。

### 2.1 三種不同的目標

#### `current authority F1`
術語版：repo 目前採納的現行參考分數。  
白話解釋：這是 repo 當下認可的正式對照值，但不一定是所有歷史 full run 裡最好的單次表現。

#### `best observed full-run F1`
術語版：在完整 paper set、非 smoke/probe/offline 條件下，歷史上實際觀察到的最高 full-run F1。  
白話解釋：這是「目前真的跑出來過的最好一次」，但不代表已經穩定，也不代表應該直接升格為 production truth。

#### `final post-verification F1`
術語版：經過 routed verification 或人工/高可靠 lane 複核後的最終決策 F1。  
白話解釋：如果你真的要追 `F1 = 1`，這才是最接近任務本質的目標，因為它承認高風險 case 不該由單一路徑直接終判。

### 2.2 為什麼不能只看 `current authority`

不能只看 `current authority`，因為：

- 它是 repo 的現行採納口徑，不等於所有實驗裡的最好 observed run。
- 對 `2409.13738` 而言，current authority combined F1 是 `0.7500`，但歷史 full run 裡確實有更高的單模型 single-reviewer run。
- 對 `2511.13936` 而言，current authority combined F1 是 `0.90625`，但 raw F1 最高的 full run 已變成 `20260408_full_gpt54mini_xhigh_2stagedirect_2409_2511` 的 `0.9123`。

### 2.3 為什麼也不能只看單次最佳單模型

不能只看單次最佳單模型，因為：

- 單次最佳 run 可能只是在某一篇、某一族 workflow、某一個 operating point 特別剛好。
- 它不一定能四篇一起穩定。
- 它不一定在 recall-sensitive 指標上更好。

`2511.13936` 就是典型例子：

- best observed full-run F1：`0.9123`
- current authority F1：`0.9063`

但如果看 recall-sensitive 指標：

- best observed full-run F2 / F3：約 `0.8844 / 0.8754`
- current authority F2 / F3：約 `0.9416 / 0.9539`

也就是說，best observed full-run 在 raw F1 上略贏，但 current authority 其實更符合高召回 screening 的風險結構。

### 2.4 `include_or_maybe` 口徑的意義

目前多數評估檔案的 `positive_mode` 都是 `include_or_maybe`。

術語版：`maybe` 在 confusion matrix 內被視為 positive。  
白話解釋：只要系統判成「值得人工再看」，目前就會被當成抓到正例。

這不是錯，但它代表：

- 目前的 F1 不是「全自動最終 include/exclude」的 F1
- 而是「include 或至少不應該太早排除」的 F1

所以這個口徑更適合：

- 高召回 screening
- triage
- routed verification

不適合被誤讀成：

- 單一路徑全自動 final decision 的真實 automation yield

---

## 3. 四篇 SR 的真實現況盤點

### 3.1 先看 current authority

| Paper | Current authority family | Precision | Recall | F1 | 註記 |
| --- | --- | ---: | ---: | ---: | --- |
| `2307.05527` | current multi-reviewer / `senior_no_marker` | 0.9593 | 0.9649 | 0.9621 | 目前觀察上仍最強 |
| `2409.13738` | current multi-reviewer / `stage_split_criteria_migration` | 0.6000 | 1.0000 | 0.7500 | current combined 文件敘述曾不一致，但 metrics file 本體是 `0.7500` |
| `2511.13936` | current multi-reviewer / `stage_split_criteria_migration` | 0.8529 | 0.9667 | 0.9063 | recall-sensitive 指標仍強 |
| `2601.19926` | current multi-reviewer / `senior_no_marker` | 0.9731 | 0.9731 | 0.9731 | 目前觀察上仍最強 |

### 3.2 再看 best observed full run

這裡的原則是：

- 只算完整資料集
- 不納入 smoke / probe / offline contract runs
- 只看實際存在的 repo artifact

| Paper | Best observed full run | Precision | Recall | F1 | 解讀 |
| --- | --- | ---: | ---: | ---: | --- |
| `2307.05527` | current multi-reviewer / `senior_no_marker` | 0.9593 | 0.9649 | 0.9621 | 目前沒有更高 full-run 觀察值 |
| `2409.13738` | historical one-stage direct-review `gpt-5.4 low` | 0.8400 | 1.0000 | 0.9130 | 目前 raw F1 最高，且 FN = 0 |
| `2511.13936` | `20260408_full_gpt54mini_xhigh_2stagedirect_2409_2511` | 0.9630 | 0.8667 | 0.9123 | raw F1 最高，但 recall 比 current authority 低 |
| `2601.19926` | current multi-reviewer / `senior_no_marker` | 0.9731 | 0.9731 | 0.9731 | 目前沒有更高 full-run 觀察值 |

### 3.3 best single-reviewer family

| Paper | Best single-reviewer family | 代表 run / 觀察 | 核心訊息 |
| --- | --- | --- | --- |
| `2307.05527` | historical one-stage direct-review | 最好約 `0.9169` | 單 reviewer 明顯落後 current multi-reviewer |
| `2409.13738` | historical one-stage direct-review | `gpt-5.4 low` 最好約 `0.9130` | 單 reviewer 目前 raw F1 最好，但不代表是最穩路線 |
| `2511.13936` | 2stage direct-review | `gpt-5.4-mini xhigh` 最好約 `0.9123` | 兩階段單 reviewer 已逼近或略超 current authority F1 |
| `2601.19926` | historical one-stage direct-review | 最好約 `0.9594` | 單 reviewer 仍落後 current multi-reviewer |

### 3.4 哪種錯誤最致命

| Paper | 最致命的錯誤類型 | 白話解釋 |
| --- | --- | --- |
| `2307.05527` | modality / output purity 誤判 | 看起來和 audio 有關，但最終輸出不是純 audio |
| `2409.13738` | semantic boundary 誤判 | 看起來像 process mining，但不是你要的 process extraction |
| `2511.13936` | relation 誤判 | paper 談到 preference，但 preference 沒真的進 learning loop |
| `2601.19926` | concept-word false positive | abstract 裡有 syntax、transformer 字樣，但不是 empirical syntax analysis |

### 3.5 關於 `2409` current combined score 的不一致

這點必須明講，否則報告會混亂。

- `AGENTS.md` 的表格曾把 `2409` combined F1 寫成 `0.8235`
- 但 `docs/chatgpt_current_status_handoff.md`
- `screening/results/2409.13738_full/CURRENT.md`
- `screening/results/results_manifest.json`
- `screening/results/2409.13738_full/combined_f1.stage_split_criteria_migration.json`

實際都對齊在 `0.7500`

所以這份報告採用 metrics file 本體作為最終數值依據。

---

## 4. 文獻方法家族與 repo 重疊圖

這一節不只講 paper 本身，而是講它們跟 repo 現況有哪些真正重疊、哪些只是表面相似。

| Paper / workflow | 術語版方法 | 白話版解釋 | 主要適用架構 | 對 repo 的實際對應 / 缺口 |
| --- | --- | --- | --- | --- |
| `Wang 2024` | monolithic yes/no prompt with calibration | 用很短的 prompt 直接判 yes/no，重點是調 operating point，不是把判斷拆開 | single reviewer / cheap triage | repo 的 historical one-stage direct-review 很接近；缺口是它不夠 criterion-aware |
| `Akinseloyin 2024` | criterion decomposition via QA | 先把 criteria 拆成問題，再逐題回答，不先問整體收不收 | 兩者皆可 | repo 的 `QA-first`、`merged criterion QA` 就是在走這條線；缺口是還沒有穩定的高品質 criterion ledger |
| `Sanghera 2025` | prompt as threshold / recall calibration | prompt 不是單一人格，而是不同保守程度的 decision threshold | 兩者皆可 | repo 有不同 senior prompt 與 direct-review 家族，但還沒有明確把 calibration 當第一級設計物 |
| `ReviewCopilot` | extract-then-decide / structured evidence | 先抽欄位，再比對 criteria，不先做 impression-based verdict | 兩者皆可，放在 three-reviewer 更有價值 | repo 已有 `evidence_highlights`，但缺少 first-class `structured evidence object` 與跨 reviewer 共用 ledger |
| `A4SLR` | agentic orchestration across the whole review pipeline | 不只 screening，而是把 search、screening、extraction、assessment、report 串成模組化流程 | three-reviewer / multi-lane | repo 有多段流程雛形，但尚未形成完整 orchestrated evidence pipeline |
| `Akinseloyin 2026` | multi-agent aggregation over decomposed criteria | 多 agent 不是自由聊天，而是先回答同一組 criterion questions，再聚合 | three-reviewer / multi-lane | repo 的 `two juniors + SeniorLead` 已接近，但 reviewer 還不是 criterion-specialized agents |
| `Nama 2021` | exclusion-class-aware verification routing | 不是所有排除都要同樣處理；看排除理由決定是否要複核 | three-reviewer / routed multi-lane | repo 已有 cutoff-first，但還沒有 reason-specific verification routing |
| `Noel-Storr 2021` | ML + crowd hybrid high-recall workflow | 先用便宜系統過濾，再用更可靠的人或 crowd 接手高風險樣本 | three-reviewer / routed multi-lane | repo 還缺一個真正的 cheap-gate + reliable-lane 明確分層 |
| `Shemilt 2022` | recall-calibrated classifier for living evidence | 先建立高召回前哨站，接受 moderate precision 換 workload reduction | 兩者皆可，但主要是 front gate | repo 缺的是一個面向 living update 的穩定 sentinel classifier 設計 |
| `ASReview v2` | active learning + shared model + crowd of experts | 不是每個 case 都平均審；讓 shared model 和多人標註共同縮小搜尋空間 | 兩者皆可，偏 multi-expert | repo 還沒有 active learning / prioritization layer，也沒有 shared model + expert loop |

### 4.1 這些文獻對 repo 最重要的共同訊息

共同訊息不是「多 agent 就會變強」，而是：

1. 把 criteria 拆成可追溯的最小單元
2. 把高風險 case 路由到更貴但更可靠的 lane
3. 把 decision 變成可審計的 evidence object
4. 不要讓所有 case 都走同一種處理方式

目前 repo 已經有：

- cutoff-first
- two juniors + senior adjudication
- direct-review families
- QA-first / merged criterion QA experiments
- fulltext-direct experiments

目前 repo 還缺：

- reason-specific verification routing
- first-class criterion ledger
- targeted full-text retrieval
- shared structured evidence object
- active learning / prioritization layer

---

## 5. 方法到底套 single reviewer 還是 three-reviewer

這一節直接回答你的第二個問題。

### 5.1 方法架構矩陣

| 方法 | 主要適用架構 | 為什麼 | 若硬套到另一種架構會出什麼問題 |
| --- | --- | --- | --- |
| `verification routing` | three-reviewer / routed multi-lane | 它的核心就是讓不同風險的 case 走不同路，而不是所有 case 同步終判 | 若硬塞進純 single reviewer，最後常只剩「多一個分支名稱」，沒有真正的複核價值 |
| `criterion ledger` | 兩者皆可，但在 three-reviewer 更有價值 | single reviewer 可用來自我約束；three-reviewer 可讓 senior 真正比對分歧點 | 若沒有共用 schema，multi-reviewer 還是只是在比三段自由敘述 |
| `structured evidence object` | 兩者皆可，但在 three-reviewer 更有價值 | 它是可審計與可 debug 的基礎資料結構 | 若單 reviewer 不保留 evidence object，後面很難做錯誤分析；若 multi-reviewer 沒共用 object，senior 很難整合 |
| `targeted full-text retrieval` | 兩者皆可 | 這本質上是證據取得策略，不是 reviewer 數量策略 | 若沒有 routing，它可能只是把更多 token 丟進去，卻沒有更好判斷 |
| `paper-specific semantic assets` | 兩者皆可 | 每篇 review 的語義地雷不同，無論 single 或 multi-reviewer 都需要 | 若強迫全域共用同一套語義資產，常會救一篇、傷另一篇 |
| `prompt calibration` | 兩者皆可 | 不同階段需要不同 operating point | 若把 calibration 當成唯一解法，常只能局部移動 precision/recall，解不了 criteria semantics |
| `disagreement mining` | three-reviewer / multi-lane 更有價值，但 single reviewer 也能做 | 只研究 hard cases 才會真的拉分 | 若只在 easy cases 上做 calibration，通常會得到看起來平順但無法救真正錯誤的設定 |

### 5.2 核心結論

結論必須講得很直接：

- `single reviewer` 適合 baseline、cheap triage、comparison arm。
- `three-reviewer or routed multi-lane` 才是高可靠 final path。

白話講：

- single reviewer 很適合當「第一眼判斷」或「便宜對照組」
- 但如果你要的是四篇一起穩定、而且最後真的逼近 `F1 = 1`，高風險 case 就不應該只走單一路徑

---

## 6. 四篇逐篇診斷

### 6.1 `2409.13738`

#### 為什麼難

術語版：主戰場是 `process extraction` vs `redesign / matching / prediction` 的 semantic boundary。  
白話解釋：很多 paper 看起來都和 process mining 很有關，但真正符合你 criteria 的其實只有其中一部分。

它至少同時涉及：

- natural-language text 是否真的是輸入來源
- 輸出是不是 process representation / model
- 是否是 extraction，而不是 redesign、matching、prediction
- 是否有 concrete method
- 是否有 empirical validation

#### 現有最好方法是哪種 family

- 若只看目前 observed raw F1：historical one-stage direct-review family 最好
- 若看與未來共用骨架的相容性：merged criterion QA family 最值得接續

也就是說：

- `historical one-stage direct-review` 代表「這篇其實可以被單 reviewer 判得很好」
- `merged criterion QA` 代表「這篇需要更好的 criteria ledger，而不是更少的結構」

#### 最不該亂動的全域設定

- 不要把所有 paper 的 senior 一起改成更嚴、更窄的全域 strict mode
- 不要把所有 `maybe` 一起壓成 `exclude`

因為 `2409` 的問題不是「不夠嚴」，而是「嚴在哪裡才對」。

#### 最值得新增的 paper-specific asset

最值得新增的是 `process-extraction boundary ledger`。

它至少要顯式列出：

- 正向欄位：`natural-language text input`
- 正向欄位：`process representation/model extraction target`
- 正向欄位：`concrete NLP method`
- 正向欄位：`empirical validation`
- 反向欄位：`redesign`
- 反向欄位：`matching`
- 反向欄位：`prediction`
- 反向欄位：`secondary research`

### 6.2 `2511.13936`

#### 為什麼難

術語版：主戰場是 `preference enters learning loop` vs `preference only for evaluation`。  
白話解釋：paper 裡提到 preference 不夠，關鍵是這個 preference 到底有沒有拿去訓練模型。

這個 review 難的地方在於：

- preference 可能是 human 或 synthetic
- preference 可能透過 ranking、A/B comparison、numeric ratings 轉 ranking
- 有些 paper 會在 abstract 大談 preference，但只是拿來做 evaluation

#### 現有最好方法是哪種 family

- 若只看 observed raw F1：2stage direct-review family 目前最好
- 若看 recall-sensitive 指標：current multi-reviewer authority 仍更穩

這代表：

- 這篇不是沒有辦法做高 precision
- 但若一味追求 raw F1，會很容易把 recall 和 F2/F3 拉低

#### 最不該亂動的全域設定

- 不要把全域 workflow 改成「只要看到 preference 就傾向 include」
- 也不要把全域 strict senior 一起加強到會壓掉 RL / implicit preference 類 case

#### 最值得新增的 paper-specific asset

最值得新增的是 `learning-signal relation ledger`。

它應至少顯式記錄：

- preference source 是什麼
- preference 是否進 training objective
- 是否有 RL training loop
- 是否只是 evaluation
- numeric rating 是否真的被轉成 ranking signal

### 6.3 `2307.05527`

#### 為什麼難

術語版：主戰場是 `output entirely audio`。  
白話解釋：不是只要和 audio 有關就算，重點是最後輸出是不是純 audio。

這篇容易出錯的地方在於：

- paper 可能碰 audio，但最後輸出是 text
- 可能是 multimodal 但不是純 audio output
- 可能是 metric、tooling、增量方法，不是 generative audio model/application 主體

#### 現有最好方法是哪種 family

- current multi-reviewer family 目前觀察上最強

#### 最不該亂動的全域設定

- 不要為了救 `2409 / 2511` 去全域加一大堆 strict senior 規則
- 不要把 `2307` 從目前穩定的 multi-reviewer 路線拖去追單 reviewer 的漂亮數字

#### 最值得新增的 paper-specific asset

最值得新增的是 `audio-output purity ledger`。

核心欄位包括：

- main topic 是否 generative audio
- final output 是否 entirely audio
- 是否 ASR / speech-to-text
- 是否 video generation
- 是否 mixed primary output

### 6.4 `2601.19926`

#### 為什麼難

術語版：主戰場是 `Transformer LM + empirical syntax analysis` 的 conjunction。  
白話解釋：不是 paper 同時出現 transformer 和 syntax 兩個詞就算，還要真的做 empirical syntax analysis。

它看似簡單，但容易有三種假陽性：

- 談 transformer，但不是 language model 重點
- 談 syntax，但不是 empirical analysis
- 是 survey / position paper，沒有 empirical component

#### 現有最好方法是哪種 family

- current multi-reviewer family 目前觀察上最強

#### 最不該亂動的全域設定

- 不要全域強化 strict senior 到影響高召回

repo 既有狀態已明示：`2601` 對 overly strict senior behavior 很敏感。

#### 最值得新增的 paper-specific asset

最值得新增的是 `syntax-analysis conjunction ledger`。

核心欄位包括：

- 是否 Transformer-based language model
- 是否 empirical syntax analysis
- 是否 non-transformer architecture
- 是否 MT-oriented encoder-decoder
- 是否缺乏 empirical component

---

## 7. 推薦的共用骨架

這裡的前提是：不改 formal criteria，只改 workflow support layer。

### 7.1 推薦骨架

1. `cutoff / metadata gate`  
   白話解釋：先處理時間窗、語言、全文可得性、明顯 publication form 問題，不要把昂貴 lane 浪費在低價值樣本。

2. `criterion decomposition`  
   白話解釋：把 criteria 拆成 reviewer 真能逐條核對的最小 obligations。

3. `cheap high-recall lane`  
   白話解釋：先用便宜 lane 把可疑正例保留下來，目標是少漏，不是一次做對所有排除。

4. `verification routing`  
   白話解釋：把不同風險等級的排除送去不同深度的驗證，不要所有 `exclude` 都同權處理。

5. `targeted full-text lane`  
   白話解釋：只有 unresolved criterion 才觸發全文或長上下文，而且抓的是對的段落，不是固定截全文。

6. `senior adjudication`  
   白話解釋：senior 不是再看一次整體 impression，而是整合 typed evidence ledger，對高風險 case 做最後裁決。

7. `audit trail`  
   白話解釋：所有重要判斷都要留下 criteria version、evidence span、route、verification reason。

### 7.2 哪些東西全域共用

應該全域共用的東西：

- route 類型
- evidence object schema
- adjudication contract
- evaluation dashboard
- stop conditions

### 7.3 哪些東西必須 paper-specific

必須 paper-specific 的東西：

- criterion asset
- semantic boundary definitions
- exclusion-risk classes
- section-target map
- calibration wording

白話講：

- 骨架可以共用
- 但每篇 review 的「哪裡最容易誤判」不能共用

---

## 8. 研究路線排序

這一節分兩種排序：

- 四篇一起提分的排序
- 逼近 `final F1 = 1` 的排序

### 8.1 四篇一起提分的排序

| 排名 | 方法 | 術語版描述 | 白話版描述 | 最可能先救哪一篇 | 最可能傷到哪一篇 |
| --- | --- | --- | --- | --- | --- |
| 1 | `verification routing` | exclusion-class-aware routed verification | 先把簡單排除和危險排除分開處理 | `2409`, `2511` | 若亂設 direct-exclude 規則，最先傷 `2409` |
| 2 | `criterion ledger` | typed criterion-conditioned evidence ledger | 先逐條填 criteria 檢查表，再做 final decision | `2409`, `2511` | 若 ledger 設計太差，會拖累 `2307`, `2601` 的 coverage |
| 3 | `targeted full-text retrieval` | criterion-triggered evidence retrieval | 只抓解 unresolved criterion 所需的段落 | `2409`，其次 `2511` | 若全球濫用，會增加 `2307`, `2601` 的噪音和成本 |
| 4 | `paper-specific semantic assets` | paper-specific semantic boundary assetization | 每篇都做自己的地雷圖與正反例詞典 | 依 paper 而定，先救 `2409`, `2511` | 若硬做全域化，會互相傷害 |
| 5 | `stage-aware calibration` | phase-specific operating-point calibration | 第一關偏保留，第二關偏驗證，senior 只看可追溯證據 | `2409`, `2511` | 全域 strictify 會先傷 `2601` |
| 6 | `只換模型 / 拉高 effort / 自由辯論式 multi-agent` | model-scale or free-debate-first optimization | 期待更大模型自己想清楚 | 偶爾對單篇有效 | 最容易造成四篇不穩定，尤其 `2307`, `2601` |

### 8.2 逼近 `final F1 = 1` 的排序

這裡的邏輯更嚴格，因為目標不是「分數變高一點」，而是「最後不再漏、不再誤殺」。

1. `verification routing`
2. `criterion ledger`
3. `targeted full-text retrieval`
4. `paper-specific semantic assets`
5. `stage-aware calibration`
6. `只換模型 / 拉高 effort / 自由辯論式 multi-agent`

### 8.3 為什麼這樣排

因為如果你接受：

- 高風險 case 可以進 verification queue
- 低風險 easy case 可以快速處理

那最能把 final F1 推向 1 的，不是讓第一個 reviewer 更強，而是讓：

- 危險 case 不再被太早定死
- decision 依據變成可追溯 ledger
- 缺的證據真的被補到

---

## 9. 評估規格與停止條件

### 9.1 主指標不只看 F1

固定要同時報：

- `precision`
- `recall`
- `F1`
- `F2`
- `F3`

原因很簡單：

- `F1` 看 precision / recall 等權
- `F2`、`F3` 更貼近 screening 的高召回風險結構

這點在 `2409` 和 `2511` 尤其重要。

### 9.2 必須分開報兩種結果

#### `final post-verification performance`
白話解釋：高風險 case 經過 verification 後，最後整體到底對不對。

#### `auto-resolution coverage`
術語版：系統在不進 verification queue 的情況下，自動完成 final decision 的比例。  
白話解釋：有多少 case 可以完全自動處理，不用送去更貴的下一關。

如果不把這兩個分開，你會得到一個假進步：

- F1 看起來很好
- 但其實只是把很多 case 丟給 `maybe`

### 9.3 固定的評估紀律

必須固定遵守：

- 不把 smoke / probe / offline run 當最佳基準
- 不把 `include_or_maybe` 當成唯一 automation 指標
- 不接受任何讓 `FN` 增加的改法作為「進步」

### 9.4 建議的 stop conditions

對四篇一起優化時，建議的停止條件如下：

1. `2409` 與 `2511` 的 full-run 表現至少超過各自當前最佳可比 full run
2. `2307` 與 `2601` 不因為全域改動而退步
3. 若某新方法提高 raw F1，但讓 `FN` 增加，視為不通過
4. 若某新方法只在 `include_or_maybe` 口徑上好看，但 auto-resolution coverage 極低，也不算真正進步

### 9.5 current 與 best observed 的 F2 / F3 參考

| Paper | Current F2 / F3 | Best observed full-run F2 / F3 | 解讀 |
| --- | --- | --- | --- |
| `2307.05527` | `0.9638 / 0.9643` | `0.9638 / 0.9643` | current 即 best observed |
| `2409.13738` | `0.8824 / 0.9375` | `0.9633 / 0.9813` | `2409` 是最值得追 best-run 的 paper |
| `2511.13936` | `0.9416 / 0.9539` | `0.8844 / 0.8754` | current authority 的 recall-sensitive 表現其實較好 |
| `2601.19926` | `0.9731 / 0.9731` | `0.9731 / 0.9731` | current 即 best observed |

---

## 10. 術語白話附錄

### `verification routing`
術語版：依據排除理由與風險類型，把 case 分流到不同深度的驗證路徑。  
白話解釋：不是每個 `exclude` 都一樣危險；有些可以快排，有些必須再查。

### `criterion ledger`
術語版：以 criteria 為主軸的結構化 obligation / evidence 記錄表。  
白話解釋：先填檢查表，再決定收不收。

### `structured evidence object`
術語版：將 evidence span、欄位、來源位置、判斷關係結構化的資料物件。  
白話解釋：不要只留一句理由，要留下「到底看到哪一句話」。

### `targeted full-text retrieval`
術語版：由 unresolved criterion 觸發的定向全文證據擷取。  
白話解釋：缺什麼證據，就去抓那個段落，不是把固定截斷全文塞進去。

### `paper-specific semantic assets`
術語版：專屬於某篇 review 的語義邊界資產，如正反例、反例類型、關鍵 relation。  
白話解釋：每篇 review 都有自己的地雷圖，不能只用一套全域關鍵字規則。

### `calibration`
術語版：調整 prompt / lane / adjudication 的 operating point，以改變 precision-recall tradeoff。  
白話解釋：第一關、第二關、最後仲裁，不該是同一種性格。

### `disagreement mining`
術語版：優先分析不同 workflow、不同 reviewer、不同模型之間的分歧樣本。  
白話解釋：真正該研究的是那些大家會吵架的 paper，不是 easy cases。

### `auto-resolution coverage`
術語版：在不進 verification queue 的情況下，自動完成 final decision 的比例。  
白話解釋：系統到底有多少比例真的能自己判完，不用送下一關。

---

## 主要依據檔案

本報告的數字與結論，主要來自下列本地檔案與已讀 PDF：

- `docs/brainstorming/SR_screening_ultradeep_report_2026_zh.pdf`
- `AGENTS.md`
- `docs/chatgpt_current_status_handoff.md`
- `screening/results/results_manifest.json`
- `screening/results/2307.05527_full/CURRENT.md`
- `screening/results/2409.13738_full/CURRENT.md`
- `screening/results/2511.13936_full/CURRENT.md`
- `screening/results/2601.19926_full/CURRENT.md`
- `screening/results/2307.05527_full/combined_after_fulltext_senior_no_marker_report.json`
- `screening/results/2409.13738_full/combined_f1.stage_split_criteria_migration.json`
- `screening/results/2511.13936_full/combined_f1.stage_split_criteria_migration.json`
- `screening/results/2601.19926_full/combined_after_fulltext_senior_no_marker_report.json`
- `docs/single_reviewer_baseline/REPORT_zh.md`
- `docs/single_reviewer_baseline/single_reviewer_runs_summary.csv`
- `screening/results/single_reviewer_official_batch_2409_low_rerun_after_criteria_change_2026-03-24/runs/20260324_2409_rerun2_gpt54_low/papers/2409.13738/single_reviewer_batch_f1.json`
- `screening/results/single_reviewer_official_batch_2stage_direct_review_2409_2511_2026-04-06/runs/20260408_full_gpt54mini_xhigh_2stagedirect_2409_2511/papers/2511.13936/single_reviewer_batch_f1.json`
- `screening/results/single_reviewer_official_batch_merged_2stage_qa_criteria_gpt5nano_2409_2511_2026-03-29/runs/20260329_full_gpt5mini_low_merged2stage_scoreauth_2409_2511/papers/2409.13738/single_reviewer_batch_f1.json`
- `screening/results/single_reviewer_official_batch_2stage_qa_gpt5nano_2409_2511_2026-03-28/runs/20260328_full_gpt5nano_low_2stageqa_2409_2511/papers/2409.13738/single_reviewer_batch_f1.json`
- `screening/results/fulltext_direct_v1_all4_2026-03-19/run_manifest.json`

---

## 最後結論

如果目標只是讓某一篇 paper 的 raw F1 再好看一點，那可以繼續追單次 best run。  
如果目標是四篇一起穩定，而且最後真的往 `F1 = 1` 靠近，正確方向不是「更像單一聰明裁判」，而是「更像一條可分流、可查證、可複核的審核流程」。

因此，後續最值得投資的不是新模型名字，而是：

1. `verification routing`
2. `criterion ledger`
3. `targeted full-text retrieval`

這三者一起，才是把四篇 SR 往 `final post-verification F1 = 1` 推進的主骨架。
