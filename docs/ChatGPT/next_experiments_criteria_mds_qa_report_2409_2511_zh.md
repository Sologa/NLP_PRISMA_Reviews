---
status_note: "Planning report only. Candidate experiment analysis. Not adopted current architecture."
title: "2409 / 2511 下一步實驗規劃與 criteria_mds QA 可用性評估報告"
date: "2026-03-16"
lang: zh-TW
---

# 摘要

這份報告要回答三個問題：

1. 讀完 `docs/ChatGPT/evidence_qa_feasibility_analysis_2409_2511.md` 之後，下一步最值得做哪些實驗？
2. 現行 `criteria_mds/` 裡的 QA，能不能直接拿來做接下來的實驗？
3. 如果不能，具體需要改哪些地方？

我的結論很明確：

1. **下一步最值得做的，不是再改 current criteria，而是做 current-state-aligned 的 stage-specific evidence QA / extraction，然後再加一層 evidence synthesis。**
2. **現行 `criteria_mds/` 不能直接當作 current-state 的 QA 規格來跑正式下一輪實驗。**
3. **`criteria_mds/` 很有價值，但它的正確定位是模板、起點、對照組，不是 current active QA spec。**
4. **如果要落地，至少要做四類修改：**
   - 依 `criteria_stage1/` 與 `criteria_stage2/` 分開重生 QA
   - 把 retrieval / metadata gate 與 screening evidence 徹底分離
   - 修正 `2409` 與 `2511` 內部仍存在的邊界漂移
   - 在 QA 後加入 schema-based evidence synthesis，而不是停在自由文本問答

換句話說，`criteria_mds/` 不應直接拿來跑；但它很適合用來**生成新一版、對齊 current stage-split criteria 的 QA 規格**。

# 1. Current State 前提

這一節只確認 current state，避免把候選實驗和 production state 混在一起。

## 1.1 現行 production criteria

目前 production runtime 使用的是：

1. Stage 1 criteria：`criteria_stage1/<paper_id>.json`
2. Stage 2 criteria：`criteria_stage2/<paper_id>.json`

對本次關心的兩篇 paper：

1. `2409.13738`
   - Stage 1: `criteria_stage1/2409.13738.json`
   - Stage 2: `criteria_stage2/2409.13738.json`
2. `2511.13936`
   - Stage 1: `criteria_stage1/2511.13936.json`
   - Stage 2: `criteria_stage2/2511.13936.json`

`criteria_jsons/*.json` 不是 current production criteria。

## 1.2 現行 metrics authority

這兩篇 paper 的 current authority 是：

1. `2409.13738`
   - Stage 1 F1 = `0.7500`
   - Combined F1 = `0.7843`
   - authority: `screening/results/2409.13738_full/stage1_f1.stage_split_criteria_migration.json`
   - authority: `screening/results/2409.13738_full/combined_f1.stage_split_criteria_migration.json`
2. `2511.13936`
   - Stage 1 F1 = `0.8657`
   - Combined F1 = `0.8814`
   - authority: `screening/results/2511.13936_full/stage1_f1.stage_split_criteria_migration.json`
   - authority: `screening/results/2511.13936_full/combined_f1.stage_split_criteria_migration.json`

## 1.3 候選 evidence-QA 分析文件的定位

`docs/ChatGPT/evidence_qa_feasibility_analysis_2409_2511.md` 是：

1. candidate next experiment analysis
2. separate-thread topic
3. not current workflow
4. not current criteria
5. not current score authority

所以本報告的正確任務不是「驗證 production 已經改成 evidence-QA」，而是：

**評估 evidence-QA 是否是下一步合理方向，以及目前 `criteria_mds/` 是否足以當這個方向的實驗規格。**

# 2. 直接回答：接下來該做哪些實驗？

## 2.1 最應優先做的不是 criteria surgery，而是 workflow-layer experiment

在 current architecture 下，以下事情已經是 repo-level invariant：

1. Stage 2 criteria 必須 source-faithful。
2. Stage 1 criteria 只能是 Stage 2 的 observable projection。
3. 不能把 derived operational hardening 寫回 formal criteria。
4. 不接受第三層 hidden guidance / operational policy 偽裝成 criteria。

這代表下一步最乾淨的改善槓桿，已經不在 criteria wording 本體，而在：

1. evidence extraction
2. structured reviewer output
3. evidence synthesis
4. decision support
5. stage handoff
6. senior adjudication input format

## 2.2 我建議的實驗序列

如果要排優先順序，我建議是下面這個順序：

1. **Experiment A：用 current active stage-split criteria 重生 stage-specific QA spec**
2. **Experiment B：比較 current baseline vs QA-only**
3. **Experiment C：比較 QA-only vs QA+synthesis**
4. **Experiment D：讓 criteria evaluator / SeniorLead 看 synthesized evidence object**
5. **Experiment E：把現行 `criteria_mds/` 原封不動當對照組，只做一次負控制實驗**

這五個實驗中，真正必做的是 A、B、C。  
D 很重要，但可以在 B/C 跑完後再做。  
E 不是為了上線，而是為了量化「直接沿用 `criteria_mds/`」到底會造成多大污染。

# 3. 現行 `criteria_mds/` QA 能不能直接拿來做接下來的實驗？

## 3.1 簡短答案

**不能直接拿來做 current-state aligned 的正式實驗。**

但這個答案需要補一句：

**它可以拿來當模板、初稿、對照組、prompt scaffolding。**

也就是說：

1. 若問題是「能不能零修改直接上？」答案是 **不能**。
2. 若問題是「有沒有足夠價值作為下一版 QA 的骨架？」答案是 **有，而且很有價值**。

## 3.2 為什麼不能直接拿來跑

核心原因有五個。

### 原因 1：`criteria_mds/` 不是 current stage-split criteria 的保證映射

`criteria_mds/README.md` 明確把這批檔案定位成：

1. original extracted criteria
2. metadata-only programmable conditions
3. screening question set for extraction agent

它很接近你要的方向，但它不是根據 current active `criteria_stage1/` / `criteria_stage2/` 自動重生的產物。  
因此它不保證與 current-state criteria 一一對齊。

### 原因 2：它把 retrieval 與 screening 資訊放在同一份材料裡

這在 `2511` 特別明顯。`criteria_mds/2511.13936.md` 同時保留了：

1. 2020 onward
2. arXiv citation cutoff
3. venue / source / citation gate
4. final selection rule
5. screening question set

這些不是同一層東西。

如果直接把它當 current QA spec，容易把：

1. metadata filter
2. retrieval history
3. screening decision evidence

混成同一個 decision core。

### 原因 3：它不是 stage-specific QA

current architecture 的核心就是 stage split：

1. Stage 1 只應問 title/abstract 可觀測條件
2. Stage 2 才確認 full-text-only 條件

但 `criteria_mds/2409.13738.md` 與 `criteria_mds/2511.13936.md` 都還是單份 question set。  
如果直接拿來跑，很容易讓 Stage 1 問到不該在 Stage 1 決定的內容，或讓 Stage 2 重做 Stage 1 已經可觀測的部分。

### 原因 4：它在少數關鍵地方仍保留了歷史漂移或內部不一致

這一點是本報告最重要的判斷依據之一，下面分 paper 展開。

### 原因 5：它還沒有完整 synthesis schema

即使 question set 本身方向正確，目前輸出形態仍主要是：

1. QA answers
2. quote
3. location
4. 少量 signal fields

這還不足以構成穩定 decision interface。  
如果沒有 synthesis schema，decision layer 仍要重新解讀自然語言答案。

# 4. 具體差異分析：`2511` 為什麼不能直接沿用

## 4.1 `audio core modality` 與 current criteria 不一致

current active Stage 1 / Stage 2 criteria 對 `2511` 的 audio boundary 是：

1. `criteria_stage1/2511.13936.json`
   - multimodal works **including audio** are treated as within the audio domain
2. `criteria_stage2/2511.13936.json`
   - multimodal works **including audio** are treated as within the audio domain

但 `criteria_mds/2511.13936.md` 的 Stage 2 screening criteria 寫成：

1. `I2. Audio-domain application is present. For multi-modal works, this includes any paper where audio is a core modality.`

這個「audio is a core modality」比 current criteria 更嚴，屬於明顯的 boundary drift。

更重要的是，這份檔案在後面的操作化定義又寫成：

1. `Multi-modal work is included when it includes audio content`

也就是說，**同一份 `criteria_mds/2511.13936.md` 內部就存在兩種不同門檻：**

1. audio as core modality
2. any multimodal work including audio

這代表它不能直接被視為 current-state-ready QA spec。

## 4.2 `2511` 把 retrieval gate 與 screening gate 混在一起

`criteria_mds/2511.13936.md` 的 Q6 / Q7 直接要求：

1. publication year
2. venue / source
3. arXiv true/false
4. citation count
5. citation cutoff pass/fail

這些欄位本身不是沒有價值，而是：

1. 它們屬於 retrieval / metadata 層
2. 它們不是 current stage-split screening semantics 的核心 evidence object
3. 若直接混入 QA，decision agent 很容易把 retrieval gate 當 screening gate

這在 current architecture 下是不乾淨的。

## 4.3 `2511` 缺的不是更多 QA，而是更硬的 synthesis fields

`criteria_mds/2511.13936.md` 已經問到了：

1. ranking / A-B / pairwise preference
2. numeric ratings 是否轉 ranking
3. RL loop / reward model
4. learning vs evaluation
5. audio-domain evidence
6. survey/review

方向上是對的。

但如果要跑下一輪實驗，至少還要補成穩定欄位：

1. `comparison_type`
2. `rating_to_preference_conversion`
3. `preference_signal_source`
4. `learning_vs_evaluation_role`
5. `rl_loop_for_audio_model`
6. `audio_domain_signal`
7. `multimodal_with_audio`
8. `survey_signal`
9. `missingness_reason`
10. `conflict_note`

如果沒有這一層，`2511` 最脆弱的 boundary 仍然會漂：

1. rating vs ranking
2. learning vs evaluation
3. audio-adjacent vs audio-in-domain
4. multimodal including audio 的正確處理

## 4.4 `2511` 的結論

對 `2511` 來說：

1. `criteria_mds/2511.13936.md` 的 question ideas 可用
2. 但 spec 本身不能直接用
3. 至少要：
   - 修正 `audio core` 為 current criteria 對齊的 `including audio`
   - 將 Q6 / Q7 metadata 與 screening evidence 分檔或分層
   - 明確做成 Stage 1 / Stage 2 兩份 QA
   - 補上 synthesis schema

# 5. 具體差異分析：`2409` 為什麼也不能直接沿用

## 5.1 `2409` 最大問題不是 topic，而是 object boundary

current `2409` 的核心不是「跟 BPM/NLP 有沒有關」，而是：

1. source object 是否真的是 natural-language text
2. target object 是否真的是 process model / process representation
3. NLP 是否是 process extraction 的核心方法
4. 是否有 concrete method 與 empirical validation

這些 boundary 若沒有分開抽，reviewer 很容易因為 topic similarity 而保留 paper。

## 5.2 現有 question set 對正向任務有問，但對非目標家族問得不夠硬

current Stage 1 criteria 對 `2409` 已經明確列出 observable non-target examples：

1. process redesign
2. matching
3. process prediction
4. sentiment analysis
5. label-only work
6. generating natural text from processes

但 `criteria_mds/2409.13738.md` 的主要問題仍偏重於：

1. process extraction 任務句
2. input text
3. output representation
4. concrete method
5. experiments

這些很重要，但還少了更顯式的負向抽取：

1. `non_target_task_signal`
2. `label_only_signal`
3. `text_from_process_generation_signal`
4. `process_prediction_or_matching_signal`

這會讓 decision layer 比較容易只看到正向相關訊號，而看不到反證。

## 5.3 `labels` 被放進 output example，會造成 question-set level contamination

`criteria_mds/2409.13738.md` 的 Q5 第 3 題把 output 例子寫成：

1. process model
2. BPMN
3. activity sequence
4. Petri net
5. event log
6. labels

問題在於，current criteria 明確排除：

1. works targeting individual labels instead of natural text

因此把 `labels` 以平行的 output example 放進 question set，會造成兩種風險：

1. reviewer 把 label extraction 視為某種 process representation
2. decision model 受到 prompt wording 影響，把原本該排除的 family 看成弱陽性

這就是典型的 **question-set level contamination**。  
它不是 criteria 本體污染，但實際效果可能很接近。

## 5.4 `2409` 也需要 stage split，而不是單份 QA

對 `2409` 來說，Stage 1 最該抽的是：

1. `task_sentence`
2. `source_object`
3. `target_object`
4. `nlp_role`
5. `non_target_task_signal`
6. `secondary_research_signal`

而 Stage 2 才該再加：

1. `paper_type`
2. `peer_reviewed_or_venue_type`
3. `fulltext_availability`
4. `language`
5. `primary_research_signal`
6. `concrete_method_signal`
7. `experimental_validation_signal`

現有 `criteria_mds/2409.13738.md` 沒有把這兩層拆開，所以不能直接當 current-stage experiment spec。

## 5.5 `2409` 的結論

對 `2409` 來說：

1. 現有 question ideas 有效
2. 但它缺少 object-boundary oriented synthesis schema
3. 也缺少對 non-target families 的顯式 counter-evidence extraction
4. 並且存在 output example 過寬的污染風險

# 6. 所以到底要改什麼？我建議的最小必要修改

如果你要把 `criteria_mds/` 這條線拿來做下一輪實驗，我認為至少要做下面六項修改。

## 6.1 修改 1：不要直接改 current criteria，改 QA assets

這些新資產應該被定位成：

1. workflow support
2. evidence extraction spec
3. evidence synthesis spec

而不是：

1. new criteria
2. hidden guidance
3. third-layer policy

也就是說，**新 QA 檔案應與 `criteria_stage1/`、`criteria_stage2/` 分開存放。**

## 6.2 修改 2：用 current criteria 重生，而不是修補舊 `criteria_mds/` 就上線

最乾淨的做法不是在原檔上 patch 幾行，而是：

1. 以 `criteria_stage1/2409.13738.json` 生成 `2409.stage1.qa`
2. 以 `criteria_stage2/2409.13738.json` 生成 `2409.stage2.qa`
3. 以 `criteria_stage1/2511.13936.json` 生成 `2511.stage1.qa`
4. 以 `criteria_stage2/2511.13936.json` 生成 `2511.stage2.qa`

`criteria_mds/` 只保留為：

1. 模板
2. 靈感來源
3. 對照參考

## 6.3 修改 3：把 metadata / retrieval 與 screening evidence 分成兩層

我建議拆成：

1. `metadata_filter_spec`
2. `screening_qa_spec`
3. `evidence_synthesis_schema`

其中：

1. `metadata_filter_spec` 處理 year / venue / citations / open access / paper type 等能程式化或外部 metadata 處理的條件
2. `screening_qa_spec` 只問需要從內容抽 evidence 的條件
3. `evidence_synthesis_schema` 負責把 QA 回答正規化成 decision layer 可直接消化的欄位

## 6.4 修改 4：每個 synthesis field 都要有 state + provenance

每個欄位不該只有一個值，而要至少有：

1. `state`
2. `supporting_quotes`
3. `location`
4. `conflict_note`
5. `missingness_reason`

其中 `missingness_reason` 建議至少區分：

1. `not_stated`
2. `not_found`
3. `conflicting_evidence`
4. `stage1_unobservable`

## 6.5 修改 5：Stage 1 與 Stage 2 要共享 handoff object

Stage 1 的輸出不該在 Stage 2 消失。  
我建議：

1. Stage 1 抽出 evidence object
2. Stage 2 讀取 Stage 1 object
3. Stage 2 只補 unresolved fields 與 full-text-only fields

這能避免：

1. 重複抽取
2. 前後階段 evidence 不一致
3. senior 看到的是混過 interpretation 的摘要，而不是穩定 evidence

## 6.6 修改 6：SeniorLead 應優先看 evidence object，而不是直接看混合輸出

如果最終要把這條線接進 runtime，SeniorLead 的輸入應優先是：

1. synthesized evidence object
2. unresolved / conflicting fields
3. 必要時才回看原文 quote

這比直接看 junior 的自由文本 reasoning 更可稽核。

# 7. 建議的實驗矩陣

這一節回答「接下來需要做哪些實驗」。

## 7.1 Experiment A：Current-state-aligned QA spec regeneration

### 目的

建立真正對齊 current architecture 的 QA 資產。

### 做法

1. 不用 `criteria_mds/*.md` 直接當 spec
2. 以 `criteria_stage1/` + `criteria_stage2/` 為唯一 criteria source
3. 為 `2409` / `2511` 各生成兩份 QA spec
4. 每題只要求：
   - answer
   - `present / absent / unclear`
   - quote
   - location

### 產出

1. `2409.stage1.qa.md`
2. `2409.stage2.qa.md`
3. `2511.stage1.qa.md`
4. `2511.stage2.qa.md`

### 是否需要 code

最小版不一定需要。  
可以先手動或半自動生成，先做離線實驗。

### 成功條件

1. 每一條 current criteria 都有對應 evidence question 或 metadata rule
2. 沒有把 retrieval history 混成 screening decision
3. 沒有把新 hardening 偽裝成 criteria

## 7.2 Experiment B：QA-only ablation

### 目的

驗證「先問 QA，再判讀」是否比 current direct-reviewer workflow 更穩。

### 對照組

1. Baseline：current runtime prompt + current stage-split criteria
2. Variant：current-aligned QA-only -> criteria evaluation

### 評估指標

1. Stage 1 F1
2. Combined F1
3. precision / recall
4. unstable keys across repeated runs
5. per-paper error family breakdown

### 預期

1. `2409`：應先看到 FP family 壓低與 object-boundary 更穩
2. `2511`：應先看到 evaluation-only / ranking-vs-rating / multimodal-audio boundary 更穩

### 風險

如果只有 QA、沒有 synthesis，改善幅度可能有限。

## 7.3 Experiment C：QA + synthesis ablation

### 目的

驗證 synthesis 是否是必要中間層，而不是可選附件。

### 對照組

1. QA-only
2. QA + synthesis

### 評估重點

1. 是否降低 run-to-run 波動
2. 是否降低 senior 在 interpretation 上的自由度
3. 是否使錯誤類型更集中、更可診斷

### 我的預期

這個實驗很可能是整條 evidence-QA 路線裡最關鍵的一個。  
因為沒有 synthesis，decision layer 只是從讀 raw paper 改成讀 raw QA。

## 7.4 Experiment D：SeniorLead 讀 evidence object 的 ablation

### 目的

檢查 senior 是否因為 evidence object 而更穩，而不是重新做一遍自由判讀。

### 對照組

1. Senior 讀 juniors' free-form outputs
2. Senior 讀 synthesized evidence object

### 預期

1. `2409` 對這個實驗尤其敏感
2. `2511` 則主要看 boundary case 是否更一致

### 是否需要 code

若只是離線對照，不一定。  
若要接到 runtime，則需要 code。

## 7.5 Experiment E：`criteria_mds/` 原封不動負控制

### 目的

量化「直接沿用現有 `criteria_mds/`」的實際污染成本。

### 為什麼值得做一次

因為目前我們是理論上判定它不能直接用。  
做一次負控制可以具體回答：

1. contamination 到底有多大
2. 哪些 drift 真的會轉成 metrics 或 error family
3. 哪些 drift 其實影響不大

### 注意

這不是為了上線，而是為了驗證判斷。

# 8. Paper-specific synthesis schema 建議

## 8.1 `2511` 建議最小 schema

我建議 `2511` 的 schema 盡量小，但要硬。

### Stage 1 必要欄位

1. `preference_learning_signal`
2. `comparison_type`
3. `rating_to_preference_conversion`
4. `rl_loop_for_audio_model`
5. `learning_vs_evaluation_role`
6. `audio_domain_signal`
7. `multimodal_with_audio`
8. `survey_signal`
9. `missingness_reason`
10. `evidence_quotes`

### Stage 2 可延伸欄位

1. `preference_signal_source`
2. `optimization_target`
3. `reward_model_or_preference_model`
4. `conflict_note`

### 為什麼這樣設計

`2511` 的 criteria 本身不長，問題不是 coverage 不夠，而是 boundary 沒有被結構化。

## 8.2 `2409` 建議最小 schema

`2409` 比 `2511` 更需要 object-oriented evidence schema。

### Stage 1 必要欄位

1. `task_sentence`
2. `source_object`
3. `target_object`
4. `nlp_role`
5. `non_target_task_signal`
6. `secondary_research_signal`
7. `missingness_reason`
8. `evidence_quotes`

### Stage 2 必要欄位

1. `paper_type`
2. `peer_reviewed_or_venue_type`
3. `fulltext_availability`
4. `language`
5. `primary_research_signal`
6. `concrete_method_signal`
7. `experimental_validation_signal`
8. `conflict_note`

### 為什麼這樣設計

`2409` 的 hard FP 很多不是 paper 完全沒關，而是：

1. source object 抽錯
2. target object 抽太寬
3. NLP role 看太鬆
4. non-target family 沒先抽出來

# 9. 我建議的實驗成功標準

## 9.1 共通標準

不只看 F1，也要看：

1. precision / recall tradeoff
2. unstable keys
3. error family concentration
4. senior adjudication consistency

## 9.2 `2409` 的成功標準

### 主要目標

1. 降低 hard FP
2. 維持 current recall
3. 提升 run-to-run stability

### 實際判準

1. Combined F1 高於 `0.7843`
2. Combined recall 不低於 current 明顯幅度
3. object-boundary 相關 FP family 減少
4. unstable keys 不增加

## 9.3 `2511` 的成功標準

### 主要目標

1. 回收 current source-faithful stage-split 下流失的 recall
2. 但不靠重新塞 operational criteria
3. 讓 learning-vs-evaluation / multimodal-audio 邊界更穩

### 實際判準

1. Combined F1 高於 `0.8814`
2. Combined recall 高於 current `0.8667`
3. 沒有以 question wording 重新引入 `audio core` 類硬化條件
4. unstable keys 減少

# 10. 是否需要直接修改 `criteria_mds/` 這個目錄？

## 10.1 我不建議把 `criteria_mds/` 直接改造成 current production QA

理由有三個：

1. 它目前帶有明顯歷史模板性質
2. 它不是 stage-specific QA 的正式產物
3. 直接改寫會模糊 historical template 與 current experiment spec 的界線

## 10.2 我更建議的做法

建立新的 experiment asset 目錄，例如：

1. `evidence_qa_stage1/`
2. `evidence_qa_stage2/`
3. `evidence_schemas/`

或一個更集中的結構，例如：

1. `screening/evidence_specs/2409.13738.stage1.md`
2. `screening/evidence_specs/2409.13738.stage2.md`
3. `screening/evidence_specs/2511.13936.stage1.md`
4. `screening/evidence_specs/2511.13936.stage2.md`

這樣可以維持：

1. current criteria 的清潔性
2. QA spec 的獨立性
3. 歷史 `criteria_mds/` 的可追溯性

# 11. 最終判斷

## 11.1 對「接下來要做哪些實驗」的最終回答

我建議的實驗順序是：

1. 用 current `criteria_stage1/` + `criteria_stage2/` 重生 stage-specific QA
2. 跑 `baseline vs QA-only`
3. 跑 `QA-only vs QA+synthesis`
4. 跑 `senior free-form vs senior evidence-object`
5. 只做一次 `criteria_mds as-is` 負控制

若你只做一件事，我會選第 1 件加第 2 件：

**重生 current-state-aligned stage-specific QA，然後先驗證 QA-only 是否已經比 baseline 更穩。**

## 11.2 對「現行 `criteria_mds/` QA 足夠直接拿來做嗎」的最終回答

**不夠。**

更精確地說：

1. **足夠當模板**
2. **不足以直接當 current-state aligned 的實驗規格**
3. **若直接沿用，會把 retrieval gate、歷史 wording、以及少量 boundary drift 帶回實驗**

## 11.3 對「需不需要更改」的最終回答

**需要，而且不是小修，是結構性修改。**

至少要改：

1. stage split
2. metadata vs screening 分層
3. paper-specific boundary wording
4. synthesis schema
5. stage handoff

# 12. 最短版結論

如果你要給 ChatGPT 一個最短、最不容易誤解的版本，可以直接用下面這段：

> 目前最值得做的下一步，不是再改 current criteria，而是用 current active `criteria_stage1/` 與 `criteria_stage2/` 重新生成 stage-specific evidence QA，並在 QA 後加入 evidence synthesis。現行 `criteria_mds/` 不能直接當作 current-state QA spec 使用，因為它混有 retrieval/materialized metadata gate、不是 stage-specific、且在 `2409` / `2511` 上仍存在邊界漂移風險。`criteria_mds/` 最適合當模板與對照，而不是直接上線。建議先做三個 ablation：baseline vs QA-only、QA-only vs QA+synthesis、以及 senior free-form vs senior evidence-object。  

# 13. 本報告使用的主要依據

1. `AGENTS.md`
2. `docs/chatgpt_current_status_handoff.md`
3. `screening/results/results_manifest.json`
4. `screening/results/2409.13738_full/CURRENT.md`
5. `screening/results/2511.13936_full/CURRENT.md`
6. `docs/ChatGPT/evidence_qa_feasibility_analysis_2409_2511.md`
7. `criteria_mds/README.md`
8. `criteria_mds/AGENT_PROMPT_generate_question_set_from_criteria.md`
9. `criteria_mds/2409.13738.md`
10. `criteria_mds/2511.13936.md`
11. `criteria_stage1/2409.13738.json`
12. `criteria_stage2/2409.13738.json`
13. `criteria_stage1/2511.13936.json`
14. `criteria_stage2/2511.13936.json`
15. `docs/stage_split_criteria_migration_report.md`
16. `sr_screening_prompts/README.md`
17. `sr_screening_prompts_3stage/README.md`
18. `docs/source_faithful_vs_operational_2409_2511_report.md`
