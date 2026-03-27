---
status_note: "Candidate next experiment only. Not adopted current architecture. Current production state is defined by AGENTS.md, docs/chatgpt_current_status_handoff.md, and screening/results/results_manifest.json."
title: "2409 / 2511：criteria-related QA、evidence extraction 與 evidence synthesis 的可行性分析"
subtitle: "基於 current stage-split criteria 與 repo 內現有 prompt / question-set 資產"
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
linestretch: 1.24
colorlinks: true
linkcolor: blue
urlcolor: blue
toc: true
numbersections: true
header-includes:
  - |
    \usepackage{titlesec}
    \usepackage{xcolor}
    \usepackage{longtable}
    \usepackage{booktabs}
    \usepackage{array}
    \usepackage{tabularx}
    \usepackage{enumitem}
    \usepackage{fvextra}
    \DefineVerbatimEnvironment{Highlighting}{Verbatim}{breaklines,breakanywhere,fontsize=\small}
    \setlist{itemsep=0.25em, topsep=0.35em}
    \definecolor{HeadingBlue}{HTML}{1F4E79}
    \definecolor{SoftGray}{HTML}{666666}
    \titleformat{\section}{\Large\bfseries\color{HeadingBlue}}{\thesection}{0.75em}{}
    \titleformat{\subsection}{\large\bfseries\color{HeadingBlue}}{\thesubsection}{0.6em}{}
    \titleformat{\subsubsection}{\normalsize\bfseries\color{HeadingBlue}}{\thesubsubsection}{0.5em}{}
    \setlength{\parskip}{0.55em}
    \setlength{\parindent}{0pt}
---

# 摘要

這份報告回答的核心問題只有一個：

在目前已經改成 `criteria_stage1/` + `criteria_stage2/` 的 current stage-split 架構下，對 `2409.13738` 與 `2511.13936` 來說，下一步是否應該改成「先做 criteria-related QA / evidence extraction，再做 criteria 判讀」？

我的結論是：**方向上是對的，而且很可能就是現在最值得做的下一步。**

但需要把話講精確：

1. 你說的「先針對 criteria 生成相關的 evidence QA，再依答案做 criteria 判讀」，本質上是 **criteria-conditioned evidence extraction**。
2. 這和完整的 **evidence extraction / synthesis** 還不是同一件事。QA 只是先把和 criteria 直接相關的證據抽出來；真正完整的 evidence synthesis 還要再做 **欄位正規化、矛盾處理、缺證據原因標記、跨 stage handoff**。
3. 所以最精確的推薦流程不是只有「QA -> 判讀」，而是：
   **stage-specific QA / extraction -> evidence synthesis -> criteria evaluation**。
4. repo 內其實已經同時存在兩種設計原型：
   - `sr_screening_prompts/` 比較接近「先抽取、後判定」
   - `sr_screening_prompts_3stage/` 比較接近「直接判定，邊判邊引用證據」
   而 `criteria_mds/` 與 `AGENT_PROMPT_generate_question_set_from_criteria.md` 又更明確地把「criteria -> 問題集 -> extraction agent -> deterministic decision」這條路寫出來。

也因此，若你的問題是「我現在對你前一份 next step 的理解，是否大致正確」，答案是：**大致正確，但還要再補上一層 synthesis / normalization，不能停在自由文本 QA。**

# 1. Current State Verification

本節只做 current state 驗證，避免再次把舊版本和新版本混在一起。

## 1.1 目前 active criteria 的位置

current active criteria 已經不是舊的 `criteria_jsons/*.json`，而是：

1. Stage 1：`criteria_stage1/<paper_id>.json`
2. Stage 2：`criteria_stage2/<paper_id>.json`

對這兩篇 paper 來說，current active path 是：

1. `2409.13738`
   - Stage 1：`criteria_stage1/2409.13738.json`
   - Stage 2：`criteria_stage2/2409.13738.json`
2. `2511.13936`
   - Stage 1：`criteria_stage1/2511.13936.json`
   - Stage 2：`criteria_stage2/2511.13936.json`

## 1.2 current runtime 的 criteria 設計哲學

`docs/stage_split_criteria_migration_report.md` 已經把本輪遷移的核心講得很清楚：

1. `criteria_stage2/` 是 canonical、source-faithful、對齊原 paper 的完整 eligibility。
2. `criteria_stage1/` 只保留 title/abstract 可觀測的投影，不新增原文沒有的 hard exclusion。
3. runtime 只讀 stage-specific criteria，且明確 **沒有 fallback**。

這個 current state 很重要，因為它直接限制了下一步的改進方向：

- **不能再把 operational hardening 塞回 criteria。**
- 任何額外的補強，都應該放在 prompt、workflow、evidence extraction、structured output、decision support 這些層，而不是 criteria 本體。

## 1.3 current runtime prompt 的型態

`scripts/screening/runtime_prompts/runtime_prompts.json` 目前提供的是 reviewer / senior 的角色與 adjudication context。

它有：

1. Stage 1 junior reviewer 的 backstory。
2. Stage 1 senior 的兩版 prompt（`stage1_senior_no_marker` 與 `stage1_senior_prompt_tuned`）。
3. Stage 2 fulltext junior / senior 的 backstory。

但它**沒有**像 `criteria_mds/` 那種顯式的 extraction schema，也沒有顯式的 Q1/Q2/Q3… 類 questions。換句話說，current runtime 比較接近「reviewer 直接看輸入並評 criterion」，而不是「先抽取 evidence，再做 criteria evaluation」。

## 1.4 current metrics（僅列這次分析需要的兩篇）

current metrics 以 `stage_split_criteria_migration` 這批檔案為準：

1. `2409.13738`
   - Stage 1 F1 = `0.7500`
   - Combined F1 = `0.8235`
2. `2511.13936`
   - Stage 1 F1 = `0.8788`
   - Combined F1 = `0.9062`

## 1.5 歷史最佳表現（只作對照，不當 current state）

這裡只抓和這次問題最相關的對照：

1. `2511` 的 `criteria_2511_opv2` 曾把 Combined F1 拉到 `0.9206`。
2. 但那一版的提升，很大部分來自 **operational hardening**，不是 source-faithful criteria 自然就能達到的表現。
3. `2409` 在舊的 `criteria_2409_stage_split` 報告裡，Combined F1 曾到 `0.7778`，而 current migration run 是 `0.8235`；所以 `2409` 現在不是單純退步，而是「current state 已改成 faithful stage-split 後，瓶頸轉到 evidence / interpretation 層」。

這一點很關鍵：

- `2511` 目前比歷史最佳差，主要提示 **operational support 被拿掉之後，criteria fidelity 本身不足以支撐原來的 runtime 表現**。
- `2409` 目前的問題則更像是：**criteria 已經切開了，但 reviewer 還缺一個更穩定的 evidence interface。**

# 2. 直接回答你的理解：大方向是對的，但還需要補一層

你的理解可以拆成兩句：

1. 「在判定 criteria 之前，最好先做 evidence extraction。」
2. 「或者先針對 criteria 生成相關 evidence QA，再依答案判讀 criteria。」

我對這兩句的判斷如下。

## 2.1 我同意的部分

我同意，而且同意程度很高。

原因是：在 current stage-split / source-faithful 架構下，`2409` 與 `2511` 的 remaining error，已經不太像「criteria wording 再多加幾句」就能乾淨解決的問題，而更像：

1. reviewer 沒有先把關鍵證據定位出來；
2. reviewer 在同一次 prompt 裡同時做「找證據」與「下結論」，容易把 topic relevance、常識補完、歷史 operational rule 混進正式 criteria 判讀；
3. senior adjudication 也只能接收到 junior 的結論與片段 reasoning，沒有一個穩定的 evidence object 可稽核。

所以，若你問「接下來是否應該先抽 evidence，再判 criteria」，答案是 **是**。

## 2.2 我想補充修正的部分

我會把你的說法再往前推一步：

不是只有「QA -> 判 criteria」，而是更像這樣：

1. **criteria-conditioned QA / extraction**
   - 先問和 current active criteria 直接對應的問題。
   - 每題都要求 quote + location。
2. **evidence synthesis**
   - 把 QA 的答案整理成穩定欄位。
   - 例如：`signal_audio=present/absent/unclear`、`signal_eval_only=yes/no/unclear`。
   - 同時保留 supporting quotes、位置、衝突、缺失原因。
3. **criteria evaluation**
   - 最後才用 source-faithful criteria 對 synthesized evidence 做判讀。

如果少了中間的 synthesis，你雖然做了 QA，但 decision layer 仍然得直接吃自由文本答案，漂移只會從「看 paper 漂」變成「看 QA answer 漂」。

# 3. 為什麼說 `sr_screening_prompts/` 與 `criteria_mds/` 的方向，和這個 next step 本質上是一致的

## 3.1 `criteria_mds/` 的設計哲學，本來就是 extraction-first

`criteria_mds/README.md` 和 `criteria_mds/AGENT_PROMPT_generate_question_set_from_criteria.md` 已經把設計意圖寫得很明確：

1. 先把 criteria 轉成 **Screening Question Set**。
2. 問題集只用來做 **資訊抽取 + quote + location**。
3. extraction agent **不要**直接做 include/exclude。
4. 取得答案後，再由你的 pipeline 依規則做 deterministic decision。

這其實就是你現在描述的那條路。

換句話說，repo 裡不是沒有這個想法；相反地，它其實已經被明確寫成一種方法論了。

## 3.2 `sr_screening_prompts/` 是「先抽取、後判定」的手動 prompt 原型

`sr_screening_prompts/README.md` 說得很清楚：它是兩階段 screening 的 5-prompt 套件，其中：

1. Stage 1.2 先做 title+abstract extraction（Prompt 2）。
2. 再做 Stage 1.2 criteria review（Prompt 3）。
3. Stage 2 先做 full-text extraction（Prompt 4）。
4. 再做 Stage 2 criteria review（Prompt 5）。

也就是：

**extract first, decide later**。

這與我前一份報告中建議的方向，本質上是一致的。

## 3.3 `sr_screening_prompts_3stage/` 則是把 extraction 折疊掉

相反地，`sr_screening_prompts_3stage/README.md` 明確寫出：

1. Prompt 2（title/abstract 抽取）被移除。
2. Prompt 4（fulltext 抽取）被移除。
3. Stage 1.2 與 Stage 2 改成直接做 criteria review，並在評 criterion 時同步附 evidence quotes。

這就是另一條路：

**judge while extracting**。

它的優點是 prompt 少、流程短；但缺點也很清楚：

1. 找證據與下結論混在同一步。
2. reviewer 很容易把未明示資訊補完。
3. senior 看到的也不是「整理好的 evidence object」，而是別人已經混過結論的輸出。

因此，如果你的問題是「我是不是在理解你建議我往 extraction-first 靠」，答案是：**是，你理解的是對的。**

# 4. 但我要補一個更精確的區分：QA 不等於完整 evidence extraction / synthesis

這一節是整份報告最重要的觀念釐清。

## 4.1 criteria-related QA 是什麼

criteria-related QA 的核心是：

1. 問題是從 criteria 長出來的。
2. 問題只問和 criterion 判定直接相關的事。
3. 輸出要求 quote + location。
4. 不在這一層做 include/exclude。

這是很好的第一步，因為它把「判準」和「支持判準的證據」分開了。

## 4.2 evidence extraction 是什麼

evidence extraction 比 criteria-related QA 稍微再寬一點。

它不只是一問一答，而是要把 paper 裡會影響判定的關鍵 evidence 全部找出來。這通常會包括：

1. 正向 evidence。
2. 反向 evidence。
3. 缺失 evidence。
4. 和同一 criterion 相關，但分散在多個 section 的 evidence。
5. 可能彼此衝突的 evidence。

也就是說，QA 比較像「把 criterion 需要的答案問出來」；evidence extraction 則更像「把 relevant evidence object 系統性抓出來」。

## 4.3 evidence synthesis 是什麼

evidence synthesis 再往前一步。

它不是只收集 evidence，而是把 evidence 轉成**可以穩定被 decision layer 消化的欄位**。

例如：

1. `signal_preference_learning = present / absent / unclear`
2. `signal_eval_only = yes / no / unclear`
3. `target_object = process_model / process_representation / unclear`
4. `experimental_validation = explicit / absent / unclear`

每個欄位都還要附：

1. supporting quotes
2. evidence location
3. conflict note
4. missingness reason

這一步非常重要，因為沒有 synthesis，decision agent 還是得讀一堆自然語言 QA 答案。那麼它只是把不穩定從 raw paper 搬到 QA answer，沒有真正穩下來。

## 4.4 所以最好的說法不是「只做 QA」

更準確的說法是：

**先做 stage-specific、criteria-conditioned evidence extraction / QA，再做 evidence synthesis，最後才做 criteria evaluation。**

# 5. 為什麼這在 current stage-split / source-faithful 架構下特別合理

## 5.1 因為現在不能再靠改 criteria 補 operational gap

current state 已經明確要求：

1. Stage 2 criteria 要忠於原 paper。
2. Stage 1 criteria 只能是 Stage 2 的 observable projection。
3. 不能把 derived hardening 偽裝成作者原文 eligibility。

這表示你現在若還想提升表現，最乾淨的槓桿就會轉到：

1. evidence extraction
2. structured reviewer output
3. decision support
4. stage handoff

而不是 criteria 本體。

## 5.2 `2511` 已經提供了一個很強的反向證據

`2511` 的 current combined F1 現在是 `0.9062`，而 `criteria_2511_opv2` 在 cutoff 修正後也同樣是 `0.9062`。

這表示：

1. `2511` 已不再存在「`opv2` 明顯高於 current authority」的分數差。
2. 下一步若考慮 evidence QA，重點不該再是把 baseline 從低點拉回來，而是判斷 residual edge cases 是否值得額外結構化支援。

既然現在又不能把那些 hardening 再塞回 criteria，最自然的替代方案，就是把那些「本來偷偷埋在 criteria 裡的 operational support」，搬到 extraction / synthesis / reviewer support 層。

## 5.3 `2409` 也顯示出一樣的結構性需求

`2409` 在 current state 下不是完全崩掉，而是進到一種典型狀態：

1. criteria 已經切得比以前乾淨。
2. 但 reviewer 仍會在 source-object / target-object / task objective / method concreteness 上搖擺。
3. 剩下的 hard FP 很多不是「paper 完全沒講」，而是「paper 有講一些相關話，但 reviewer 沒先把關鍵句子拆成可判讀欄位」。

這種型態非常適合 evidence-first workflow。

# 6. 為什麼我說你現在講的 QA，和真正完整的 evidence extraction / synthesis 還有差距

你自己提出了一個很重要的自我修正：

> 我這邊的 QA 只是先提取跟 criteria 相關的而已；evidence extraction / synthesis 需要更全面的信息。

我認為這個判斷是正確的。差距主要有五個。

## 6.1 QA 通常只抓「問題對應的答案」，不一定抓到負向或反證

例子：

1. 你問「是否有 experiments？」
2. 模型可能摘一段 evaluation sentence。
3. 但它不一定會主動再去找「有沒有只是 qualitative discussion、沒有 method validation」這種反向訊號。

完整 extraction / synthesis 會更主動地處理：

- 支持句
- 反證句
- 缺失訊號
- 衝突訊號

## 6.2 QA 的答案常常還是自由文本，decision layer 不一定吃得穩

如果 extraction 輸出只是：

- Q1 答案：一段自然語言
- Q2 答案：一段自然語言
- Q3 答案：一段自然語言

那 decision layer 仍然要重新解讀這些答案。

所以真正穩定的形式應該是：

1. 先保留自然語言 quotes；
2. 再額外整理成 canonical fields；
3. 最後 criteria evaluator 只看 canonical fields + quote provenance。

## 6.3 QA 不一定處理矛盾與缺失原因

例如：

1. abstract 說的是一件事；method section 顯示另一件事；
2. 或 abstract 沒寫，但 appendix / experiment table 有寫；
3. 或 paper 完全沒寫，和 reviewer 沒找到，是兩種不同的「unclear」。

完整 synthesis 會把這些區分開：

1. `not_stated`
2. `not_found`
3. `conflicting_evidence`
4. `stage1_unobservable`

如果沒有這一層，decision agent 很容易把不同型態的 unclear 都揉成同一種模糊感。

## 6.4 QA 未必會考慮 stage handoff

Stage 1 與 Stage 2 不是兩個互相獨立的世界。

理想上：

1. Stage 1 先抽出可觀測證據與 unresolved fields。
2. Stage 2 只補那些 Stage 1 unresolved、或本來就是 fulltext-only 的欄位。

如果沒有 handoff，Stage 2 很容易重做一遍，還可能在重做時和 Stage 1 的 evidence 對不齊。

## 6.5 QA 未必包含 section selection / evidence targeting

特別是 Stage 2，如果沒有「要先去哪幾個 section 找什麼」這種 evidence routing，模型會浪費很多注意力在低價值文字上。

對 `2409` 與 `2511` 來說，這點尤其重要：

1. `2409` 的關鍵訊號常分布在 abstract、method、evaluation。
2. `2511` 的關鍵訊號常分布在 abstract、intro/conclusion、自述方法、training objective、evaluation setup。

所以，完整 evidence extraction/synthesis 通常還包含：

- 哪些 section 先看
- 哪些 section 只在 unresolved 時再看
- 哪些 evidence 應該優先級最高

# 7. 但有一個非常重要的風險：不要直接把現有 `criteria_mds/` 問題集原封不動當 current-state QA 規格

這一節很重要，因為它直接關係到你現在的想法到底可不可直接落地。

我的判斷是：

**方向可行，但不能直接把現有 `criteria_mds/` 問題集原封不動拿來當 current active QA spec。**

原因不是它不好，而是它有一部分是歷史生成物，未必和 current active stage-split criteria 完全對齊。

## 7.1 `2511` 的一個明顯例子：`audio core` 與 current active criteria 不一致

目前 current active `criteria_stage2/2511.13936.json` 寫的是：

- multimodal works **including audio** 都算在 audio domain 內。

但 `criteria_mds/2511.13936.md` 的 screening criteria 卻寫成：

- multimodal work 納入條件是 audio 為 **core modality**。

這兩者不是同一條件。

如果你直接把 `criteria_mds/2511.13936.md` 的 wording 當成 current QA 規格，就等於把較強的 operational hardening 偷偷帶回來。

這正是 current state 想避免的事。

## 7.2 `2511` 的第二個例子：retrieval gate 與 screening gate 被放在同一份問答材料中

`criteria_mds/2511.13936.md` 也保留了：

1. 2020 onward
2. arXiv citation cutoff
3. venue / source / citation gate

這些屬於 retrieval / metadata 層，不是 current active stage1/stage2 screening decision 的全部核心。

所以若你要用它做 QA，必須先切清楚：

1. 哪些問題是 metadata filter；
2. 哪些問題是 screening evidence；
3. 哪些問題只是歷史脈絡，不該進 current decision core。

## 7.3 `2409` 也有對齊風險：某些 output example 太寬，可能重新帶回舊邊界

`criteria_mds/2409.13738.md` 的 Q5 問 output 時，列了像：

- process model
- BPMN
- activity sequence
- Petri net
- event log
- labels

問題在於：current active 2409 criteria 的核心，是 **NLP for process extraction from natural language text**，而原 paper 的 EC.3 還明講過「targeting individual labels instead of natural text」屬於排除例。

也就是說，如果問題集本身把 `labels` 放成看起來平行的 target option，就有可能把 reviewer 的注意力往較寬的 target-object 解讀推。

這不是 criteria 本體污染，但它會造成 **question-set level contamination**。

## 7.4 所以更安全的做法是：用 current active criteria 重新生成 stage-specific QA

因此，我對 `criteria_mds/` 的最佳定位是：

1. 它是非常好的**起點與模板**。
2. 它清楚展示了 extraction-first 的思想。
3. 但它不應被直接視為 current active、可無審核直接上線的 QA spec。

更乾淨的作法應該是：

1. 以 `criteria_stage1/2409.13738.json`、`criteria_stage2/2409.13738.json` 重新生成 2409 的 stage-specific QA。
2. 以 `criteria_stage1/2511.13936.json`、`criteria_stage2/2511.13936.json` 重新生成 2511 的 stage-specific QA。
3. 只把 `criteria_mds/` 當成模板與對照，不直接當 current spec。

# 8. 如果真的往這條路走，對 2511 最有價值的 extraction / synthesis 應該抓什麼

## 8.1 `2511` 最需要被顯式抽出的不是 topic，而是四個 boundary signal

對 `2511` 來說，最關鍵的不是再問一次「是不是 audio paper」，而是把下面四種 boundary 分開。

### Stage 1 最值得抽的欄位

1. `signal_preference_learning`
   - 有沒有 ranking / A/B / pairwise preference？
   - quote + location。
2. `signal_rating_to_ranking`
   - 若只有 MOS / numeric rating，有沒有明示被轉成 ranking / preference signal？
3. `signal_rl_loop_for_audio_model`
   - 若沒有 explicit comparison，有沒有 RL training loop for an audio model？
4. `signal_audio_domain`
   - 音訊、語音、音樂是否明確出現？
   - 多模態時 audio 是不是有明示出現？
5. `signal_eval_only`
   - 偏好訊號是拿來 training / optimization，還是只拿來 evaluation？
6. `signal_survey_or_review`
   - 是否是 survey / review / overview。

### 為什麼這會有幫助

因為 `2511` current state 的主要損失，本質上不是 criteria 沒寫，而是 reviewer 對以下邊界不夠穩：

1. ranking / preference 與純 rating / evaluation 的切分；
2. audio-domain 與 topic-adjacent 的切分；
3. survey / non-survey 的切分；
4. explicit comparison 缺席時，RL loop 例外條件是否成立。

這四件事如果沒有先抽成結構化 evidence，reviewer 直接打 criterion 很容易在同一個 prompt 裡混掉。

## 8.2 `2511` 真正需要的不是更大的問題集，而是更穩的 synthesis schema

我對 `2511` 的判斷是：

它其實不需要太大的 question set。相反地，它更需要一個**小而硬、欄位穩定**的 synthesis schema。

最小 schema 可以是：

1. `preference_learning_signal`
2. `comparison_type`
3. `rating_to_preference_conversion`
4. `learning_vs_evaluation_role`
5. `audio_domain_signal`
6. `multimodal_with_audio`
7. `survey_signal`
8. `confidence`
9. `missingness_reason`
10. `evidence_quotes`

這樣做的好處是：

- 2511 的 criteria 本來就短。
- 你不需要做很大的 knowledge extraction；你只需要把最會漂的邊界穩住。

# 9. 如果往這條路走，對 2409 最有價值的 extraction / synthesis 應該抓什麼

## 9.1 `2409` 的核心不是 topic relevance，而是 object boundary

對 `2409` 來說，最容易出錯的不是 paper 是否和 BPM / NLP 有關，而是：

1. source object 是不是 natural-language text；
2. target object 是不是 process model / process representation；
3. NLP 在 paper 裡是不是 process extraction 的核心方法；
4. paper 是否真的提供 concrete method 與 experiments。

因此，`2409` 的 extraction 應該圍繞這幾個 canonical fields 來設計。

### Stage 1 最值得抽的欄位

1. `task_sentence`
   - abstract 中最能代表任務的一句。
2. `source_object`
   - input 是否明確是 natural-language text。
3. `target_object`
   - output 是否明確是 process model / process representation。
4. `nlp_role`
   - NLP / text processing 是核心 extraction method，還是背景工具。
5. `non_target_task_signal`
   - 是否偏向 redesign / matching / prediction / text generation from processes / label-only task。
6. `secondary_research_signal`
   - 是否為 review / qualitative analysis / challenge discussion。

### Stage 2 再加的 confirmatory 欄位

1. `paper_type`
2. `peer_reviewed_or_venue_type`
3. `fulltext_availability`
4. `language`
5. `primary_research_signal`
6. `concrete_method_signal`
7. `experimental_validation_signal`

## 9.2 為什麼這對 2409 特別重要

因為 `2409` 的 remaining hard FP，很多不是完全沒有 evidence，而是 evidence 沒有被拆對。

典型問題是：

1. paper 很像 process/BPM/LLM 相關；
2. 也許提了 modelling / extraction / representation；
3. 但沒有先把 `source_object`、`target_object`、`task_direction`、`method_role` 分別抽出來；
4. reviewer 便容易靠 topic similarity 把它保留下來。

換句話說，`2409` 比 `2511` 更需要一個 **object-oriented evidence schema**。

# 10. 所以我對你這個想法的總判斷：可行，而且是現在最乾淨的方向

我的總判斷可以濃縮成三句。

## 10.1 方向判斷

**可行，而且非常合理。**

如果你現在不想再污染 criteria，那最自然的下一步，就是把原本藏在 operational criteria 裡的「判讀支撐」，改成：

1. stage-specific evidence QA / extraction
2. evidence synthesis
3. criteria evaluation

## 10.2 但不要只做自由文本 QA

如果只有 QA，沒有 synthesis，你會遇到三個問題：

1. decision agent 仍要重新解讀自然語言答案；
2. 不同 reviewer 會用不同語言回答同一欄；
3. senior 無法穩定做 adjudication。

所以只做 QA 還不夠；**QA 之後一定要進一層 schema-based synthesis。**

## 10.3 也不要直接把現有問題集當 current-state spec

現有 `criteria_mds/` 很有價值，但它是模板與前置資產，不是 current active spec。

如果直接照抄，就有機會把：

1. 舊 operational assumption
2. retrieval-stage gate
3. 不再 current 的邊界

偷偷帶回來。

# 11. 我最建議優先做的 3 個 next steps

你之前希望 next steps 不要變成 wishlist。這裡我只列 3 個，而且我認為這 3 個就是最值得先做的。

## 11.1 Next step 1：以 current active stage-split criteria 重新生成 stage-specific QA，不要直接沿用舊問題集

### 這一步要做什麼

1. 以 `criteria_stage1/2409.13738.json`、`criteria_stage2/2409.13738.json` 重新生成 2409 的 QA。
2. 以 `criteria_stage1/2511.13936.json`、`criteria_stage2/2511.13936.json` 重新生成 2511 的 QA。
3. 每題只要求：
   - answer
   - evidence quote
   - location
   - `present / absent / unclear`
4. 不在這一層做 include/exclude。

### 為什麼這一步最值得先做

因為它能同時滿足三件事：

1. 忠於 current active criteria。
2. 不污染 criteria。
3. 把 extraction-first workflow 重新帶回來。

### 風險

如果生成問題集時沒有和 current active criteria 對齊，問題集本身就可能再次成為污染來源。

### 預期收益

中到高。

這一步最可能直接改善的是：

1. reviewer 漂移
2. 依 topic similarity 補完
3. senior 看不到穩定 evidence object 的問題

### 是否需要改 code

最小版不一定。

你可以先用手動或半自動方式產一版 current-state-aligned QA，跑小規模對照。

## 11.2 Next step 2：在 QA 後面補一層 evidence synthesis schema

### 這一步要做什麼

把 QA 回答再整理成 canonical fields，例如：

1. `2409`
   - `source_object`
   - `target_object`
   - `nlp_role`
   - `concrete_method`
   - `experimental_validation`
2. `2511`
   - `signal_preference_learning`
   - `signal_eval_only`
   - `signal_audio`
   - `signal_survey`
   - `signal_rl_loop`

每個欄位要有：

1. state
2. supporting quote
3. location
4. conflict note
5. missingness reason

### 為什麼這一步很重要

因為沒有 synthesis，decision layer 只是從讀 paper 改成讀 QA，自由度還是太高。

### 風險

schema 設計得太大，會讓 extraction 負擔過重。

### 預期收益

高。

這一步是把 extraction 真正變成可供 decision / senior / error analysis 重用的中間層。

### 是否需要改 code

中等。

如果你只先做離線實驗，甚至可先用 JSON schema 手動驗證；若要接到 production pipeline，則需要 code。

## 11.3 Next step 3：讓 criteria evaluator 與 SeniorLead 優先看 synthesized evidence，而不是直接看原文混合輸出

### 這一步要做什麼

1. junior reviewer 先做 extraction。
2. synthesis layer 產生 canonical evidence object。
3. criteria evaluator 根據 evidence object 做判讀。
4. SeniorLead 若介入，也先看 evidence object，再視需要回查原文。

### 為什麼這一步重要

因為目前 senior adjudication 最大的問題之一，就是它接收到的是已經混合過 interpretation 的輸出，而不是乾淨 evidence。

### 風險

若 evidence object 太貧乏，senior 可能失去必要上下文。

### 預期收益

中到高。

這一步對兩篇 paper 都有好處，但對 `2409` 特別重要，因為 `2409` 的 hard FP 多半來自 object boundary 沒先拆開。

### 是否需要改 code

中到高。

不過你可以先離線做 ablation：

1. raw text 直接判讀
2. QA 後直接判讀
3. QA + synthesis 後判讀

先看哪一層最有增益。

# 12. 我明確不建議的方向

## 12.1 不建議直接把 `criteria_mds/` 現成問題集當 current production spec

原因很簡單：它不是 current active criteria 的保證映射。

## 12.2 不建議把 QA 中歸納出的 operational rule 再命名成 criteria

這會再次污染 criteria，等於繞一圈又回到現在刻意避免的事。

## 12.3 不建議只做「自由文本 QA -> 自由文本判讀」而沒有 synthesis

這樣只能部分解決問題，穩定度通常不夠。

## 12.4 不建議讓 senior 直接補完 extraction 沒抽出的條件

如果 extraction 沒有先把 evidence object 釘住，senior 很容易重新回到「憑相關性補完」的舊問題。

# 13. 結論

最後把整份報告濃縮成四句。

1. 你的理解大方向是對的：**先做 evidence QA / evidence extraction，再做 criteria 判讀**，確實是 current stage-split / source-faithful 架構下最合理的下一步。
2. 但更精確的做法不是只有 QA，而是：
   **QA / extraction -> synthesis -> criteria evaluation**。
3. `sr_screening_prompts/`、`criteria_mds/`、`AGENT_PROMPT_generate_question_set_from_criteria.md` 都已經提供了這個方向的 repo 內前例；相對地，`sr_screening_prompts_3stage/` 則是把 extraction 折疊掉的對照設計。
4. 若真的要落地，最重要的不是把舊問題集拿來直接用，而是：
   **用 current active `criteria_stage1/` 與 `criteria_stage2/` 重新生成 stage-specific QA，並在 QA 後加一層 evidence synthesis。**

# 14. 最終直接回答你的問題

## 14.1 你現在對我前一份 next step 的理解，對不對？

**對，大方向是對的。**

如果用一句話重寫，就是：

> 在 current stage-split 架構下，最值得嘗試的不是再改 criteria，而是把 reviewer 的工作拆成「先抽 evidence，再用 evidence 判 criteria」。

## 14.2 你說的 QA，和真正 evidence extraction / synthesis 的差別在哪？

差別在於：

1. QA 通常只抓 criterion 直接相關的答案。
2. extraction 會更完整地抓正反證據與缺失訊號。
3. synthesis 會把 extraction 的自然語言結果整理成穩定 schema，供 decision layer 使用。

所以：

- QA 是一個很好的起點。
- 但若要真的提升穩定度，最好不要停在 QA，而要再加 synthesis。

## 14.3 如果只選一個最值得先做的方向，你會選哪個？

我會選：

**用 current active stage-split criteria 重新生成 stage-specific QA，並要求輸出結構化 evidence fields，而不是只輸出自由文本答案。**

因為這一步：

1. 最符合 current state；
2. 不污染 criteria；
3. 和 repo 現有資產（`criteria_mds/` 與 `sr_screening_prompts/`）最有延續性；
4. 也是最容易做乾淨 ablation 的起點。

# 15. 參考來源（本報告使用）

1. `docs/stage_split_criteria_migration_report.md`
2. `criteria_stage1/2409.13738.json`
3. `criteria_stage2/2409.13738.json`
4. `criteria_stage1/2511.13936.json`
5. `criteria_stage2/2511.13936.json`
6. `scripts/screening/runtime_prompts/runtime_prompts.json`
7. `screening/results/2409.13738_full/stage1_f1.stage_split_criteria_migration.json`
8. `screening/results/2409.13738_full/combined_f1.stage_split_criteria_migration.json`
9. `screening/results/2511.13936_full/stage1_f1.stage_split_criteria_migration.json`
10. `screening/results/2511.13936_full/combined_f1.stage_split_criteria_migration.json`
11. `docs/source_faithful_vs_operational_2409_2511_report.md`
12. `docs/criteria_2511_operationalization_v2_report.md`
13. `docs/criteria_2409_stage_split_report.md`
14. `criteria_mds/README.md`
15. `criteria_mds/AGENT_PROMPT_generate_question_set_from_criteria.md`
16. `criteria_mds/2409.13738.md`
17. `criteria_mds/2511.13936.md`
18. `sr_screening_prompts/README.md`
19. `sr_screening_prompts/sr_specific/02_stage1_2_title_abstract_questions.md`
20. `sr_screening_prompts/sr_specific/03_stage1_2_criteria_review.md`
21. `sr_screening_prompts/sr_specific/04_stage2_fulltext_questions.md`
22. `sr_screening_prompts/sr_specific/05_stage2_criteria_review.md`
23. `sr_screening_prompts_3stage/README.md`
24. `sr_screening_prompts_3stage/sr_specific/05_stage2_criteria_review.md`
25. Original paper: `https://arxiv.org/html/2409.13738v1`
26. Original paper: `https://arxiv.org/html/2511.13936v1`
