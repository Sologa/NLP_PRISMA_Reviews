---
title: "criteria_mds QA 下一步實驗的深入分析報告"
subtitle: "對 `docs/ChatGPT/next_experiments_criteria_mds_qa_report_2409_2511_zh.md` 的二次分析"
author: "OpenAI GPT-5.4 Pro"
date: "2026-03-15"
lang: zh-TW
documentclass: article
classoption: a4paper
geometry: margin=2.2cm
mainfont: "Noto Serif CJK TC"
CJKmainfont: "Noto Serif CJK TC"
sansfont: "Noto Sans CJK TC"
monofont: "Noto Sans Mono CJK TC"
fontsize: 11pt
linestretch: 1.22
colorlinks: true
linkcolor: blue
urlcolor: blue
toc: true
numbersections: true
header-includes:
  - |
    \usepackage{booktabs}
    \usepackage{longtable}
    \usepackage{array}
    \usepackage{tabularx}
    \usepackage{xcolor}
    \usepackage{titlesec}
    \usepackage{enumitem}
    \setlist{itemsep=0.28em, topsep=0.35em}
    \definecolor{HeadingBlue}{HTML}{1F4E79}
    \titleformat{\section}{\Large\bfseries\color{HeadingBlue}}{\thesection}{0.7em}{}
    \titleformat{\subsection}{\large\bfseries\color{HeadingBlue}}{\thesubsection}{0.6em}{}
    \titleformat{\subsubsection}{\normalsize\bfseries\color{HeadingBlue}}{\thesubsubsection}{0.5em}{}
    \setlength{\parskip}{0.55em}
    \setlength{\parindent}{0pt}
---

# 摘要

這份報告是針對 `docs/ChatGPT/next_experiments_criteria_mds_qa_report_2409_2511_zh.md` 的二次深入分析。我的整體判斷如下。

1. 那份檔案的方向大致正確。它抓到一個很關鍵的轉折：在 current stage-split 架構下，下一步最值得動的槓桿已經不是正式 criteria wording，而是 workflow 層，也就是 evidence QA、evidence extraction、evidence synthesis、stage handoff、以及 senior adjudication 的輸入格式。
2. 它最重要的判斷也基本成立：`criteria_mds/` 不能直接當 current-state 的正式 QA 規格；最多只能當模板、起點、對照組、或 prompt scaffolding。
3. 但它還可以再講得更精確。真正應該推進的不是單純的「QA -> criteria 判讀」，而是 `stage-specific QA / extraction -> evidence synthesis -> criteria evaluation`。如果只有 QA、沒有 synthesis，decision layer 仍然要重新解讀自然語言答案，穩定性提升會有限。
4. 若只選最值得做的 3 件事，我會選：
   1. 以 current active `criteria_stage1/` 與 `criteria_stage2/` 重生 stage-specific QA 資產。
   2. 同步定義最小可用的 evidence synthesis schema 與 stage handoff object。
   3. 針對 `2409`、`2511` 跑一個小而乾淨的三臂比較：baseline vs QA-only vs QA+synthesis。

# 本報告讀了哪些材料

本報告的主要依據如下。

1. 你指定的目標檔案：`docs/ChatGPT/next_experiments_criteria_mds_qa_report_2409_2511_zh.md`
2. current architecture 與 current metrics：
   1. `docs/stage_split_criteria_migration_report.md`
   2. `criteria_stage1/2409.13738.json`
   3. `criteria_stage2/2409.13738.json`
   4. `criteria_stage1/2511.13936.json`
   5. `criteria_stage2/2511.13936.json`
   6. `screening/results/2409.13738_full/stage1_f1.stage_split_criteria_migration.json`
   7. `screening/results/2409.13738_full/combined_f1.stage_split_criteria_migration.json`
   8. `screening/results/2511.13936_full/stage1_f1.stage_split_criteria_migration.json`
   9. `screening/results/2511.13936_full/combined_f1.stage_split_criteria_migration.json`
3. evidence-QA 相關材料：
   1. `criteria_mds/README.md`
   2. `criteria_mds/AGENT_PROMPT_generate_question_set_from_criteria.md`
   3. `criteria_mds/2409.13738.md`
   4. `criteria_mds/2511.13936.md`
   5. `sr_screening_prompts/README.md`
   6. `sr_screening_prompts_3stage/README.md`
4. 歷史脈絡：
   1. `docs/source_faithful_vs_operational_2409_2511_report.md`
   2. `docs/ChatGPT/evidence_qa_feasibility_analysis_2409_2511.md`

這裡有一個實作層面的誠實註記：本地 checkout 並沒有完整 repo 內容，所以我閱讀的是 GitHub 上對應路徑的最新 raw 版本，再在本地 repo 內生成這份報告。

# 先確認 current state，不和候選方案混版

## current criteria 的位置

current active criteria 已經不是舊的 `criteria_jsons/*.json`，而是兩份 stage-specific criteria。

| paper id | Stage 1 current path | Stage 2 current path |
|---|---|---|
| 2409.13738 | `criteria_stage1/2409.13738.json` | `criteria_stage2/2409.13738.json` |
| 2511.13936 | `criteria_stage1/2511.13936.json` | `criteria_stage2/2511.13936.json` |

這點和 `docs/stage_split_criteria_migration_report.md` 完全一致：Stage 2 是 canonical、source-faithful 的 final fulltext eligibility；Stage 1 是 title/abstract 可觀測投影，不新增原文沒有的 hard exclusion。

## current metrics

| paper id | Stage 1 precision | Stage 1 recall | Stage 1 F1 | Combined precision | Combined recall | Combined F1 |
|---|---:|---:|---:|---:|---:|---:|
| 2409.13738 | 0.6000 | 1.0000 | 0.7500 | 0.7000 | 1.0000 | 0.8235 |
| 2511.13936 | 0.8056 | 0.9667 | 0.8788 | 0.8529 | 0.9667 | 0.9062 |

這兩組數字的重要解讀是：

1. `2409` 的 Stage 1 是典型的高 recall、低 precision 型態。這通常表示很多 topic-adjacent paper 在 title/abstract 階段被保留了下來，真正需要的是把正反證據拆開抽，而不是再把 criteria 寫得更像 hardening。
2. `2511` 的 Combined precision 已經不差，主要壓力反而在 recall。這表示它更像是 boundary case 在後段被保守丟掉，而不是一堆明顯錯 paper 大量混進來。

## 你指定那份檔案的定位

`docs/ChatGPT/next_experiments_criteria_mds_qa_report_2409_2511_zh.md` 自己在 front matter 就寫得很清楚：它是 planning report，只是 candidate experiment analysis，並不是 current architecture 本身。

所以閱讀它的正確方式不是「它描述的流程已經是 production」，而是「它在提議下一輪值得做什麼」。這個定位是正確的，而且必須和 current state 分開看。

# 我對那份檔案的總評

## 我同意的部分

我同意下列五點，而且同意程度很高。

1. 它正確抓到：現在最乾淨的改善槓桿不在 formal criteria，而在 workflow 層。
2. 它正確抓到：`criteria_mds/` 不能直接當 current-state QA spec。
3. 它正確抓到：QA 必須 stage-specific，而不能一份問題集從 Stage 1 用到 Stage 2。
4. 它正確抓到：metadata / retrieval gate 應和 screening evidence 分離。
5. 它正確抓到：如果沒有 synthesis schema，光有 QA 還不夠穩。

## 我認為需要補強的部分

我認為它還需要補強四件事。

1. 它雖然提到 synthesis，但還是把 `QA-only` 放得過於中心。更精確的說，真正值得做的是「QA spec regeneration + synthesis schema definition」成對出現。這兩個不該被看成前後兩輪可有可無的小改，而應該是同一輪資產設計。
2. 它對 `2409` 與 `2511` 的 paper-specific error hypothesis 還可以再綁得更緊。這兩篇不是同一種問題：`2409` 主要是 object boundary；`2511` 主要是 learning-role / audio-domain / evaluation-only 邊界與後段保守排除。
3. 它已經主張 `criteria_mds/` 不能直接沿用，但還可以更明確地說：不是只有 wording drift 的問題，還有「單份 question set 與 stage-split runtime 不對齊」的結構性問題。
4. 它的實驗序列雖然合理，但最有資訊增益的其實不是單做 `baseline vs QA-only`，而是一次跑 `baseline vs QA-only vs QA+synthesis` 的三臂比較，這樣能直接回答 synthesis 到底值不值得。

# 這份檔案說對了什麼

## `criteria_mds/` 的原始定位，本來就更像 extraction scaffolding

`criteria_mds/README.md` 清楚說這個目錄裡包含三種東西：原始 extracted criteria、metadata-only 可程式判定條件、以及給 extraction agent 用的 Screening Question Set。它甚至明寫：實際跑 extraction agent 時，只要給 question set，不要把 criteria 本體也一起給；之後再由自己的 pipeline 決定 include/exclude。

換句話說，`criteria_mds/` 的設計精神本來就不是「讓 reviewer 直接憑這份文件做最終判斷」，而是「把 criteria 轉成資訊抽取需求」。所以你現在把它理解成 evidence-QA 的前身或模板，這個理解是對的。

## `sr_screening_prompts/` 與 `sr_screening_prompts_3stage/` 確實代表兩條不同路線

repo 裡其實已經有兩種原型。

| 資產 | 核心流程 | 判讀方式 |
|---|---|---|
| `sr_screening_prompts/` | Stage 1.2 / Stage 2 先做資訊抽取，再依 criteria review 決策 | 比較接近 extraction-first |
| `sr_screening_prompts_3stage/` | Stage 1.2 與 Stage 2 直接 criteria review 打分 | 比較接近 direct review |
| `criteria_mds/` | 由 criteria 生成 question set，先抽 evidence，再用規則判定 | 比較像 QA scaffold |

所以你說「同 repo 裡其實已經有人做過類似先問問題再判 criteria 的思路」，這是成立的。真正差別在於：那些東西還沒有被整理成和 current stage-split criteria 完整對齊、可穩定落地的 current experiment asset。

## current stage-split 架構，天然就適合 evidence object

`docs/stage_split_criteria_migration_report.md` 把 current 架構講得非常清楚：Stage 2 是 canonical、source-faithful；Stage 1 是可觀測投影；而且本輪刻意不再加第三層 guidance。這個設計其實非常適合把「額外的 operational support」放在 criteria 外面，也就是 evidence object、reviewer output schema、handoff schema。

也就是說，現在不是 evidence-QA 和 current architecture 互相衝突；相反地，evidence-QA / synthesis 正好可以作為不污染 criteria 的輔助層。

# 為什麼我認為「QA -> 判讀」方向是可行的

## 對 `2409` 而言，問題像是 object boundary 沒先抽清楚

`2409` 的 current Stage 1 指標是 precision `0.6000`、recall `1.0000`、F1 `0.7500`。這是一個非常典型的訊號：系統幾乎把該保留的都保留下來了，但也保留了不少不該保留的 paper。

這類型問題通常不是靠把正式 criteria 再寫得更硬就能優雅解決。更乾淨的做法是：先把 reviewer 在 title/abstract 中到底看到了什麼拆成欄位，例如：

1. source object 到底是不是 natural-language text；
2. target object 到底是不是 process model / process representation；
3. NLP 在 paper 裡是核心 extraction 方法，還是只是 topic-adjacent；
4. 有沒有明確反證，例如 prediction、matching、label-only、text-from-process generation。

當這些欄位先被抽乾淨，criteria evaluation 才不會只靠整體印象或關鍵字相似度做判斷。

## 對 `2511` 而言，問題比較像 borderline positive 在後段被保守丟掉

`2511` 的 current Stage 1 是 precision `0.8056`、recall `0.9667`，Combined 則是 precision `0.8529`、recall `0.9667`。這組數字說明 cutoff 修正後的 current baseline 已不再是大面積 recall collapse；若還要做 evidence QA，應該聚焦在少量 residual edge cases，而不是把它當成整體救火線。

這類型問題也很適合 evidence-first。因為只要把下列幾個關鍵證據穩定抽出來，Stage 2 與 SeniorLead 的保守排除就可能減少：

1. ranking / A-B / pairwise preference 是否真的存在；
2. numeric rating 是否真的被轉成 ranking；
3. preference 是用在 learning 還是只用在 evaluation；
4. 沒有 explicit comparison 時，是否真的有 RL training loop for an audio model；
5. 多模態 paper 是否包含 audio，而不是 audio 只是很邊緣的陪襯。

這些都不是新 criteria；它們只是把 current criteria 需要的證據先拆乾淨。

# 但我不會把它叫做「完整 evidence extraction」

這一點我認為你先前的直覺是正確的，而且值得在報告裡講得更清楚。

## criteria-related QA 是什麼

criteria-related QA 的本質是：只針對和 criteria 判讀直接相關的資訊問問題，目標是讓後續 decision layer 不必重新從整篇 paper 找證據。

白話講，就是先把「做判斷一定要看的句子」抓出來。

## 完整 evidence extraction 是什麼

完整 evidence extraction 的涵蓋面通常比 criteria QA 更廣。它除了會抓 criteria 直接需要的資訊，還會把 paper 的任務、資料、方法、評估、研究型態、邊界訊號、甚至衝突訊號一起做成較完整的結構。

白話講，就是先做一個「可重用的 paper 證據物件」，不是只回答幾個是非題。

## evidence synthesis 又是什麼

evidence synthesis 是把上一步抽到的自然語言答案和 quote，正規化成穩定欄位。它至少要處理五件事：

1. state：present / absent / unclear；
2. provenance：quote 與 location；
3. missingness_reason：是未明說、沒找到、互相衝突、還是 Stage 1 根本不可觀測；
4. conflict_note：不同段落是否互相打架；
5. handoff：哪些欄位已決、哪些欄位要留給下一階段補。

白話講，就是把「一堆回答」整理成「一個可以直接拿去做判讀的物件」。

## 所以最精確的流程應該怎麼說

我會把最精確的推薦流程寫成下面這樣：

`stage-specific criteria-conditioned QA / extraction -> evidence synthesis -> criteria evaluation -> senior adjudication on evidence object`

這比單純寫成 `QA -> criteria 判讀` 更完整，也比較不容易讓人誤解成「只要做問答就夠了」。

# 這份檔案最關鍵的判斷：`criteria_mds/` 不能直接用，是否成立？

答案是成立，而且理由不只一個。

## 它不是由 current stage-split criteria 自動重生的

`criteria_mds/README.md` 本身沒有保證它和 current `criteria_stage1/` / `criteria_stage2/` 一一對齊。它更像是依某一時間點抽出的 criteria 與 question set 資產。只要 current criteria 後來有做 stage-split migration，它就自然可能落後。

## `2511` 真的存在明顯 drift

`criteria_stage1/2511.13936.json` 與 `criteria_stage2/2511.13936.json` 都把「multimodal works including audio」視為 audio domain 內。但 `criteria_mds/2511.13936.md` 的 Stage 2 screening criteria 卻寫成 audio 是 core modality 才算；後面的 operational definition 又改寫成 includes audio content 就可。這代表同一份文件內部自己就有兩套門檻。

這種情況下，如果直接把那份 question set 當 current QA spec，你等於把不一致一起帶進去。

## `2409` 也真的存在 question-set level contamination 風險

`criteria_stage1/2409.13738.json` 和 `criteria_stage2/2409.13738.json` 對 `2409` 的核心是 text -> process representation / model 的 object boundary，並且把 label-only、prediction、matching、text-from-process generation 視為非目標家族。但 `criteria_mds/2409.13738.md` 的 Q5 output examples 又把 `labels` 放進和 process model、BPMN、Petri net 並列的位置。

這會造成一種很麻煩的污染：criteria 本體雖然沒有被改，但 question wording 會暗示 reviewer 把原本該排除的 label-only family 看成弱陽性。

## 它把 retrieval / metadata 與 screening evidence 混在一起

這在 `2511` 特別明顯。`criteria_mds/2511.13936.md` 同時帶著 2020 之後、arXiv citation cutoffs、venue / source / citation gate、以及 screening question set。這些資訊不是完全沒用，但它們不該全部落在同一個 QA layer 裡。

正確拆法應該至少是：

1. `metadata_filter_spec`
2. `screening_qa_spec`
3. `evidence_synthesis_schema`

如果不拆，後面的 agent 很容易把 retrieval 歷史條件誤當 screening 判斷核心。

# 我會如何重寫這份檔案的核心建議

如果要把你指定的那份檔案再精煉成「更可執行」的版本，我會把它的核心建議改寫成下面四條。

## 先做 asset regeneration，不是先做 prompt surgery

第一步不是去 patch 舊 `criteria_mds/*.md`，而是把 current active `criteria_stage1/` 與 `criteria_stage2/` 當成唯一 criteria source，為 `2409` 和 `2511` 各自生成兩份 stage-specific QA spec。

也就是說：

1. `2409.stage1.qa`
2. `2409.stage2.qa`
3. `2511.stage1.qa`
4. `2511.stage2.qa`

## QA spec 與 synthesis schema 應該成對出現

我不建議把 QA 和 synthesis 當成兩輪完全分開的事情。更合理的做法是：同一輪資產設計就把「問題」和「輸出欄位」一起定好。

例如每一題至少要能產出：

1. answer
2. state
3. quote
4. location
5. missingness_reason

否則你在下一輪還是得重做一次 schema 設計。

## `2409` 與 `2511` 必須各自有 paper-specific evidence object

對 `2409` 來說，我會優先抽以下欄位。

### `2409` Stage 1 最小欄位

| 欄位 | 用途 |
|---|---|
| `task_sentence` | 抓 paper 自己怎麼描述任務 |
| `source_object` | 判斷是否真的是 natural-language text |
| `target_object` | 判斷是否真的是 process representation / model |
| `nlp_role` | 判斷 NLP 是核心 extraction 還是只是相鄰任務 |
| `non_target_task_signal` | 顯式抓 prediction / matching / redesign / label-only 等反證 |
| `secondary_research_signal` | 排除 review / survey 類 |
| `missingness_reason` | 解釋為何仍 uncertain |
| `evidence_quotes` | 保留原文依據 |

### `2409` Stage 2 補充欄位

| 欄位 | 用途 |
|---|---|
| `paper_type` | full research or not |
| `peer_reviewed_or_venue_type` | conference / journal / preprint |
| `fulltext_availability` | 可否取得全文 |
| `language` | English 與否 |
| `primary_research_signal` | original contribution 與否 |
| `concrete_method_signal` | 是否真的有具體方法 |
| `experimental_validation_signal` | 是否真的有實證驗證 |
| `conflict_note` | 處理方法與實驗證據衝突 |

對 `2511` 來說，我會優先抽以下欄位。

### `2511` Stage 1 最小欄位

| 欄位 | 用途 |
|---|---|
| `preference_learning_signal` | 是否有 preference learning 核心訊號 |
| `comparison_type` | ranking / A-B / pairwise / none |
| `rating_to_preference_conversion` | rating 是否明確被轉成 preference |
| `rl_loop_for_audio_model` | 無 explicit comparison 時的替代陽性訊號 |
| `learning_vs_evaluation_role` | preference 是用於 learning 還是只做 evaluation |
| `audio_domain_signal` | 是否真的落在 audio domain |
| `multimodal_with_audio` | 多模態是否包含 audio |
| `survey_signal` | 是否 review / survey |
| `missingness_reason` | 為何 uncertain |
| `evidence_quotes` | 保留原文依據 |

### `2511` Stage 2 補充欄位

| 欄位 | 用途 |
|---|---|
| `preference_signal_source` | human / synthetic / mixed |
| `optimization_target` | preference 對哪個 model / policy 起作用 |
| `reward_model_or_preference_model` | 是否存在相關模組 |
| `conflict_note` | evaluation-only 與 learning-role 的衝突說明 |

## SeniorLead 應該讀 evidence object，不該直接重做自由判讀

這是那份檔案已經提到、但我認為還可以再講得更重的一點。若 evidence-QA 這條線最後要進 runtime，SeniorLead 最該看到的不是兩個 junior 的長篇自然語言，而是：

1. synthesized evidence object；
2. unresolved fields；
3. conflicting fields；
4. 必要時才展開原文 quote。

這樣 SeniorLead 的工作才會變成 adjudication，而不是第三次從零讀一次 paper。

# 我會怎麼安排實驗，不做過大的 wishlist

如果只挑最值得做的 4 個 next steps，我會選下面這四個。

## Step 1：重生 current-state-aligned 的 stage-specific QA spec

這一步的產物不是 code，而是資產。

1. 以 `criteria_stage1/2409.13738.json` 生成 `2409` Stage 1 QA。
2. 以 `criteria_stage2/2409.13738.json` 生成 `2409` Stage 2 QA。
3. 以 `criteria_stage1/2511.13936.json` 生成 `2511` Stage 1 QA。
4. 以 `criteria_stage2/2511.13936.json` 生成 `2511` Stage 2 QA。
5. metadata-only 規則和 screening QA 分檔。

這一步最重要的成功條件只有三個：

1. 不把任何 derived hardening 偽裝成 criteria；
2. 每條 current criteria 都能對應到 evidence question 或 metadata rule；
3. `criteria_mds/` 只當模板，不直接上線。

## Step 2：同一輪定義最小 evidence synthesis schema + handoff object

這一步是我最想補進原報告的地方。沒有它，QA-only 的價值會被大幅稀釋。

最小 schema 至少要有：

1. `state`
2. `supporting_quotes`
3. `location`
4. `missingness_reason`
5. `conflict_note`

而 handoff object 的原則很簡單：Stage 1 抽出的 evidence 不應在 Stage 2 消失；Stage 2 應該只補 unresolved 與 full-text-only 欄位。

## Step 3：跑小型三臂比較，而不是只跑單一替代流程

我建議的比較矩陣如下。

| arm | 流程 | 目的 |
|---|---|---|
| A | current baseline | 保留 current runtime 作對照 |
| B | QA-only -> criteria evaluation | 驗證單純先問再判是否有幫助 |
| C | QA+synthesis -> criteria evaluation | 驗證 synthesis 是否真的是必要中介層 |

這一步最重要，因為它會直接回答：

1. 只做 QA 夠不夠；
2. synthesis 到底值不值得；
3. 哪一篇 paper 對這條路線反應最大。

## Step 4：只在前三步有明顯收益後，再做 SeniorLead evidence-object ablation

這一步要回答的是：SeniorLead 在 current free-form mode 與 evidence-object mode 下，是否真的更穩。

這個步驟很值得做，但它不該排在最前面。因為若前面的 QA 與 synthesis 自己都還不穩，SeniorLead 就算改輸入格式，也只是接手不穩的中間物件。

# 我明確不建議的做法

## 不建議直接把現行 `criteria_mds/` 當 current QA spec 上線

原因不是只有 wording 有點舊，而是它在 `2511` 上有 boundary drift，在 `2409` 上有 question-set contamination 風險，並且和 current stage-split 架構在資產形態上就不完全對齊。

## 不建議把新的 evidence schema 命名成 criteria

這一點一定要守住。因為一旦把 workflow support 偽裝成 criteria，就會重新把「作者原文 eligibility」和「為了 runtime 穩定而加的 operational support」混在一起。

## 不建議只做 QA、不做 synthesis 就直接下結論

因為這樣 decision layer 只是從讀 raw paper 變成讀 raw QA，自然語言歧義仍然存在，run-to-run 波動不一定會真正降下來。

## 不建議一開始就大改 SeniorLead 或全域 prompt

目前最值得驗證的不是 global prompt surgery，而是 evidence object 這條線本身有沒有信息增益。若這條線還沒證明有效，就先動 SeniorLead，很容易把變因重新纏在一起。

# 如果把你原本的想法翻成最精確的一句話

如果我要把你前面的想法翻成一個最精確、最不容易誤解的版本，我會寫成下面這句：

> 在 current stage-split criteria 架構下，下一步最值得做的不是再改 formal criteria，而是從 current active `criteria_stage1/` 與 `criteria_stage2/` 生成 stage-specific、criteria-conditioned evidence QA，並把輸出整理成可 handoff 的 evidence synthesis object，再依此做 criteria evaluation；現有 `criteria_mds/` 可當模板與負控制，但不能直接當 current production QA spec。

# 最終結論

我對你指定那份檔案的最後判斷是：

1. 方向是對的，而且已經很接近真正值得做的 next step。
2. 它最大的價值在於：把 attention 從「formal criteria 還要不要再動」拉回到「workflow 支援層怎麼補」。
3. 它最大的不足在於：還可以更明確地把 `QA`、`evidence extraction`、`evidence synthesis`、`criteria evaluation` 這四層分開。
4. 若只做一件事，我不會選「直接沿用 `criteria_mds/` 跑 QA-only」，而會選「用 current stage-split criteria 重生 QA spec，並同步定義 synthesis schema」。
5. 若只做一組實驗，我不會只跑 `baseline vs QA-only`，而會跑 `baseline vs QA-only vs QA+synthesis`。這是最能回答現在核心問題的一組實驗。

# 附錄 A. 建議的資產分層

| 層級 | 應放什麼 | 不應放什麼 |
|---|---|---|
| formal criteria | source-faithful Stage 2、observable Stage 1 | derived hardening、hidden guidance |
| metadata filter | year、venue、peer review、fulltext、citation gate 等 | 需要內容理解的語義條件 |
| screening QA spec | 問題、quote、location、present/absent/unclear | include/exclude 結論 |
| evidence synthesis schema | state、provenance、missingness、conflict、handoff | 作者原文 eligibility 本體 |
| decision layer | criteria evaluation、senior adjudication | 新的未聲明規則來源 |

# 附錄 B. 本報告最短版

最短版結論只有三句。

1. 你指定那份檔案的方向是對的：下一步應該往 evidence-QA / extraction 走，而不是再改 formal criteria。
2. 但真正值得做的不是單純 `QA -> 判讀`，而是 `stage-specific QA / extraction -> synthesis -> criteria evaluation`。
3. `criteria_mds/` 很有價值，但正確定位是模板與對照，不是 current active QA spec。
