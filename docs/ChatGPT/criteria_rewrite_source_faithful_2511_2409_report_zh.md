---
historical_note: "This document is historical. References to criteria_jsons/*.json describe the older single-file criteria phase, not the current active stage-split criteria."
title: "2511.13936 與 2409.13738 criteria 改寫報告"
subtitle: "以原篇為唯一上限的 source-faithful rewrite"
date: "2026-03-14"
lang: zh-TW
documentclass: article
classoption: a4paper
geometry: margin=2.2cm
mainfont: "Noto Serif CJK TC"
CJKmainfont: "Noto Serif CJK TC"
sansfont: "Noto Sans CJK TC"
monofont: "Noto Sans Mono CJK TC"
fontsize: 11pt
linestretch: 1.25
numbersections: true
colorlinks: true
linkcolor: blue
toc: true
header-includes:
  - |
    \usepackage{titlesec}
    \usepackage{xcolor}
    \definecolor{HeadingBlue}{HTML}{1F4E79}
    \titleformat{\section}{\Large\bfseries\color{HeadingBlue}}{\thesection}{0.75em}{}
    \titleformat{\subsection}{\large\bfseries\color{HeadingBlue}}{\thesubsection}{0.6em}{}
    \titleformat{\subsubsection}{\normalsize\bfseries\color{HeadingBlue}}{\thesubsubsection}{0.5em}{}
    \setlength{\parskip}{0.55em}
    \setlength{\parindent}{0pt}
---

# 摘要

這一輪的要求不是再做一版更 aggressive 的 operationalization，而是回到兩篇原文，重新確認作者到底把 eligibility 寫到了哪裡，然後只在那個上限之內改寫 criteria。基於這個前提，我的結論很明確。

第一，`2511.13936` 的原文 eligibility 非常簡潔。它只要求三件事：與 preference learning 有關、應用於 audio domain、且不是 survey/review。作者接著補充 preference learning 的定義：必須涉及兩個以上 audio clips 的 ranking 或 A/B comparison；數值評分只有在被轉成 ranking 時才算；偏好可以來自人類或合成訊號；即使沒有顯式比較，只要有一個用於 audio model 的 RL training loop，也可納入；若偏好只拿來做 evaluation 而沒有 learning component，則排除。原文還明說 multimodal work 只要包含 audio，就算在 audio domain 之內。依這個標準，repo 目前 `2511` criteria 裡的 `audio core`、`IEMOCAP/SEMAINE`、`training objective/loss/reward/model selection` 等硬化，都已經超出原篇。見 R1、R2、R3。

第二，`2409.13738` 的原文 IC/EC 也是明文列出的。納入條件是：peer-reviewed conference/journal 的 full research article、可取得全文、英文、primary research、明確研究 NLP for process extraction from natural language text、且要有 concrete method 與 experiments。排除條件則是：非 full research paper、非 conference/journal、非 peer-reviewed（包含 preprint）、無全文、非英文、secondary research、不是「NLP for process extraction from natural language text」，以及只有 superficial method discussion 或沒有 experiments。作者還在正文中把 process extraction 定義成從 natural-language text 抽取 process models，並在總結與附錄裡明示目標可包含 control-flow 與 decisional models；附錄的已納入清單也顯示，像 generation、discovery、creation、semi-automatic process elements identification 這類 title 並不會自動出局，只要它們仍然是在做從自然語言到 process model 的 extraction。依這個標準，repo 目前 `2409` criteria 裡某些額外 negative override，例如 generic LLM/dataset/foundation-model、IE/NER/RE 一概視為 output-object mismatch、recommendation/simulation/compliance 等項目，已經超過原篇明示範圍。見 R4、R5、R6、R7、R8、R9。

第三，若這一輪的優先目標是「不能超譯」，那麼最好的作法不是再往現有 JSON 疊更多 reviewer-friendly 句子，而是先做一版 source-faithful baseline rewrite，把 consumable fields 改回只包含原文可直接支持的內容。這裡要特別注意 implementation：`topic_pipeline.py` 目前實際會收集與處理的是 `sources`、`inclusion_criteria.required`、`inclusion_criteria.any_of` 與 `exclusion_criteria`，並不 consume `stage_projection`。所以如果你想避免超譯，真正要收斂的是這些會被 runtime 用到的欄位，而不是只在 `stage_projection` 寫得更漂亮。見 R10、R11。

# 1. 任務界定與判準

本報告的判準只有兩條。

第一條，凡是寫進建議 criteria 的句子，都必須能在原篇中找到直接支持，或是屬於對原篇明文條件的保守重述。

第二條，凡是只能算是 reviewer convenience、title/abstract operationalization、或根據你目前實驗結果額外硬化出來的 guardrail，如果原篇沒有明寫，就不應被包裝成作者原本的 eligibility criteria。

這意味著本報告不是在追求當下最好的 precision/F1；它追求的是「paper-grounded criteria fidelity」。若你之後還想追求更好的 runtime 表現，可以在這個 baseline 之上再做第二層 derived operational policy，但那一層必須和原篇 criteria 分開命名。

# 2. 我重新讀到的原篇 eligibility 定義

## 2.1 `2511.13936`

原文在 final selection 直接說，每一篇候選 paper 都會讀 abstract、introduction、conclusion 來判定 eligibility。納入條件只有三項：第一，paper pertains to preference learning；第二，paper is applied within the audio domain；第三，paper is not a survey or review article。見 R1。

接著作者把「related to preference learning」明確定義成四種可接受情形。第一，涉及兩個以上 audio clips 的 ranking。第二，涉及 A/B comparison。第三，數值評分只有在被轉成 rankings 時才算。第四，即使沒有顯式 comparisons，只要存在一個 RL training loop for an audio model，也可納入。作者同時明寫 two negative clauses：如果 preferences 只用於 evaluation，沒有 learning component，就排除；multimodal works including audio 也算 audio domain。見 R1。

因此，對 `2511` 來說，原篇真正的硬邊界是「preference learning 的最小成立條件」與「audio domain 是否成立」，而不是某個更細的 training-role taxonomy，也不是某些 speech/SER/corpus name 的出現與否。見 R1、R2。

## 2.2 `2409.13738`

原文在方法章節把 inclusion criteria 寫得非常完整。納入必須同時滿足四項：第一，full research article，發表於 peer-reviewed conference 或 journal，full text 可得，且為英文；第二，primary research，亦即 original contribution；第三，specifically covering the use of NLP for process extraction from natural language text；第四，explicate a concrete method and describe experiments for empirical validation。見 R4、R5。

原文的 exclusion criteria 也同樣清楚。若不是 full research paper、不是 conference/journal、不是 peer-reviewed（包含 preprint）、無全文、非英文，排除；若是 secondary research，排除；若不是 specifically covering NLP for process extraction，排除。作者還直接舉例，這一類排除包含：process redesign、matching、process prediction、sentiment analysis、target individual labels instead of natural text、generating natural text from processes。最後，若 paper 只有 superficial method discussion，或沒有 experiments，也排除。見 R4、R5。

更重要的是，作者在 introduction 先把 process extraction 定義成從 natural-language text 抽取 process models，並指出 process models 可以是 control-flow 或 decisional；傳統 process extraction pipeline 也被作者分成 NLP 與 process generation 兩步，其中第二步是把 NLP output 映射成 process model。見 R6。這告訴我們，`2409` 原篇的 target object 是 process model，但它本身並不把 generation/discovery/creation 等字面標籤視為排除條件。

附錄的已納入清單把這個邊界說得更清楚。原文確實納入了含有下列 title family 的 papers：`Automatic generation of business process models from user stories`、`A semi-automatic approach to identify business process elements in natural language texts`、`A-BPS: automatic business process discovery service using ordered neurons LSTM`、`Declarative Process Discovery: Linking Process and Textual Views`、`Assisted declarative process creation from natural language descriptions`。見 R7、R8。這代表如果我們在 criteria 裡直接把 generation、discovery、creation、semi-automatic、process elements 這些字面形式寫成 hard negative，就已經超過原篇。

# 3. 現行 repo criteria 哪裡超出原篇

## 3.1 `2511` 現行 JSON 的超出點

repo 目前的 `2511.13936.json` 把 eligibility 寫成三層 gate：audio-domain、preference-signal、learning-role，並額外加入 `speech`、`spoken dialogue/calls`、`SER`、`voice/paralinguistic cues`、`IEMOCAP/SEMAINE` 等 strong positives，同時規定 multimodal 只有在 audio 是 core input 時才算。見 R3。

這裡至少有三個地方超出原篇。

第一，原文從未要求 audio 必須是 core input modality；相反地，作者明說 multimodal works including audio 都算 within the audio domain。見 R1。

第二，原文沒有把 learning role 進一步細分成 training objective、loss、reward modeling、label construction、model selection 這種 operational taxonomy。原文只說：如果 preferences 只用於 evaluation 而沒有 learning component，就排除；若沒有顯式 comparisons，但有 RL training loop for an audio model，也可納入。見 R1。也就是說，原文有 learning component 這個門檻，但沒有你現在 JSON 裡那套更細的硬分類。

第三，原文的 keyword selection 與最終 eligibility 不是同一件事。作者在 methods 裡講過 keyword refinement，最後搜尋字串是 `("audio" OR "music" OR "acoustic") AND ("preference learning" OR "RLHF" OR "DPO" OR "KTO")`，而像 `speech`、`spoken`、`ordinal` 等字串是被測試過但未納入 final search string 的。這些詞不應被反過來寫成 eligibility 的 strong-positive evidence。見 R2。

## 3.2 `2409` 現行 JSON 的超出點

repo 目前的 `2409.13738.json` 不是原篇 IC/EC 的直譯，而是已經做過一次 stage-aware operationalization。它加入了 `method-role gate`、`uncertainty handling gate`、`generic NLP/LLM/dataset/foundation-model` negative、`output-object mismatch` negative、以及 `recommendation/simulation/compliance` 等原篇沒有明文列出的 exclusions。見 R9。

這裡至少有四個超出點。

第一，原文 IC/EC 沒有 `generic LLM/dataset/foundation-model paper with no explicit text-to-process task` 這條具體 negative。原文只說：若不是 specifically covering NLP for process extraction，就排除。見 R4、R5。這兩者邏輯接近，但不是同一句；若你要守 fidelity，就不應把後者換成更細、更強的 derived negative。

第二，原文沒有把 IE/NER/relation extraction/classification/retrieval 一概視為 output-object mismatch。相反地，作者在正文把 process extraction pipeline 的第一步就描述成 NLP analysis，而附錄中還納入了 process elements identification 與 process model generation from NER/RE family 的 papers。見 R6、R7、R8。若一篇 paper 透過 NER/RE 幫助完成 process extraction，原篇並不會因為它有 IE/RE 成分就直接排除。

第三，原文 EC.3 明列的是 process redesign、matching、process prediction、sentiment analysis、targeting individual labels instead of natural text、generating natural text from processes。repo 現行 JSON 又向外擴到 recommendation、simulation、compliance monitoring 等項目。這些擴寫對 operational precision 也許有幫助，但並不是原篇明示條件。見 R5、R9。

第四，repo 現行 JSON 把 Stage 2 的方法條件寫成必須提供一個 executable extraction pipeline。原文只說 need a concrete method and experiments，不需要 `executable pipeline` 這樣更硬的語句。見 R4、R5、R9。

# 4. 改寫原則

## 4.1 `2511` 的改寫原則

第一，只保留原文明說的三條 eligibility 與 preference-learning 補充定義。

第二，刪除所有把 keyword、語料名、任務別、或更細 learning-role taxonomy 寫成 hard gate 的內容。

第三，保留 `preferences solely for evaluation -> exclude` 這個負向條件，因為它是作者原文明寫的唯一 learning-related exclusion。

## 4.2 `2409` 的改寫原則

第一，把原文 IC.1 到 IC.4 與 EC.1 到 EC.4 直接還原成 consumable criteria。

第二，保留 process extraction 的原文定義：從 natural-language text 到 process model；目標可包含 control-flow 與 decisional models。這是 scope 說明，不是額外 gate。

第三，不把 generation、discovery、creation、semi-automatic、process elements identification 這些 title surface form 寫成 negative。原篇已納入同類 paper。見 R7、R8。

第四，不再把 current repo 中那些更細的 derived negatives 誤寫成原篇 criteria，例如 generic LLM/dataset、IE/NER/RE 一概排除、compliance/recommendation/simulation、executable extraction pipeline 等。

# 5. 建議改寫稿

本節給的是「可直接落地」的 source-faithful wording。為了讓你實際可用，我另外附了兩份 JSON 檔。這裡先把核心內容寫清楚。

## 5.1 `2511.13936` 建議改寫

### `topic_definition`

本篇的 eligibility 應寫成：paper 必須同時符合三件事。第一，與 preference learning 有關。第二，應用於 audio domain。第三，不是 survey 或 review。對 preference learning 的定義，應直接沿用原文：涉及兩個以上 audio clips 的 ranking 或 A/B comparison；數值評分只有在被轉成 ranking 時才算；偏好可來自 human judgments 或 synthetic generation；即使沒有 explicit comparisons，只要存在一個 RL training loop for an audio model，也可納入。若 preferences 只用於 evaluation，而沒有 learning component，則排除。Multimodal works including audio 應視為 within the audio domain。見 R1。

### `inclusion_criteria.required`

第一條應寫成：paper pertains to preference learning, defined by the ranking or A/B comparison of two or more audio clips; numeric ratings count only when converted to rankings; preferences may be human or synthetic; papers without explicit comparisons are still eligible when they contain an RL training loop for an audio model.

第二條應寫成：paper is applied within the audio domain; multimodal works including audio are treated as within the audio domain.

第三條應寫成：paper is not a survey or review article.

### `exclusion_criteria`

第一條應寫成：studies that use preferences solely for evaluation, with no learning component, are excluded.

第二條應寫成：survey or review articles are excluded.

### 我刻意不寫進去的內容

我刻意不把 `audio core`、`IEMOCAP/SEMAINE`、`speech/SER`、`training objective/loss/reward/model selection`、`ordinal intensity labels` 等內容寫進 criteria。不是因為它們永遠沒用，而是因為原文沒有把它們列成 eligibility 的硬邊界。若把這些寫進 criteria，就會把「目前 pipeline 的 operational preference」誤包裝成「原篇作者的原始 protocol」。

## 5.2 `2409.13738` 建議改寫

### `topic_definition`

本篇 scope 應寫成：此 review 研究的是 NLP-enabled process extraction，也就是從 natural-language text 抽取 process models。目標 process models 可包含 control-flow models（imperative 或 declarative）與 decisional models。對 pipeline 而言，title+abstract 階段只能先判定是否顯示出「NLP for process extraction from natural language text」這個核心條件；完整 eligibility 仍要回到全文確認 paper type、language/fulltext、originality、concrete method 與 experiments。見 R4、R5、R6。

### `inclusion_criteria.required`

第一條應寫成：paper is a full research article published in a peer-reviewed conference or journal, a full text is available, and the paper is written in English.

第二條應寫成：paper is a primary research article presenting an original research contribution.

第三條應寫成：paper specifically covers the use of NLP for process extraction from natural language text.

第四條應寫成：paper explicates a concrete method and describes experiments to empirically validate the method.

### `exclusion_criteria`

第一條應寫成：papers that are not full research papers, not published in a conference or journal, not peer-reviewed including preprints, have no full text available, or are not written in English are excluded.

第二條應寫成：secondary research articles are excluded.

第三條應寫成：papers not specifically covering the use of NLP for process extraction are excluded. This includes studies on NLP for process redesign, matching, or process prediction, sentiment analysis, works that target individual labels instead of natural text, or studies on generating natural text from processes.

第四條應寫成：papers that only superficially discuss an applied method, or do not describe experiments to validate the method, are excluded.

### 我刻意不寫進去的內容

我刻意不把 `generic LLM/dataset/foundation-model paper`、`output-object mismatch for IE/NER/RE/classification/retrieval`、`recommendation/simulation/compliance monitoring`、`executable extraction pipeline` 等語句寫回 criteria。這些都是比原篇更細、更硬的 operational paraphrase，不是原篇 IC/EC 的直譯。見 R5、R9。

我也刻意不把 `generation`、`discovery`、`creation`、`semi-automatic`、`process elements` 這些 title family 寫成 negative。原因很簡單：原篇自己的已納入清單就包含這些 family。見 R7、R8。

# 6. 實作層面的解法

## 6.1 如果你現在最在意的是「不能超譯」

最直接的作法是：把 `2511.13936.json` 與 `2409.13738.json` 的 consumable fields 直接換成本報告附的 source-faithful rewrite。這裡的 consumable fields 指的是 `topic_definition`、`inclusion_criteria.required`、`exclusion_criteria`，以及必要的 `sources`。見 R10、R11。

這麼做的好處是語義邊界最乾淨：你之後若看到 runtime 行為不理想，可以明確說那是 pipeline operationalization 問題，而不是原篇 criteria 本身被你改寫歪了。

## 6.2 如果你還想保留某些 operational hardening

那也不要把它們繼續寫進「原篇 criteria」本體。比較乾淨的方案是把整個設計切成兩層。

第一層叫做 `paper-grounded core criteria`。這一層只保留原篇可以直接支持的內容，也就是本報告現在給出的 rewrite。

第二層叫做 `derived reviewer guidance` 或 `operational policy`。這一層才放 title/abstract stage 的 heuristics，例如 reviewer 在 abstract 缺資訊時要不要保留 `maybe`、哪些詞族常造成 false positive、哪些 signal 在你的資料集上容易誤導。但這一層不能再被說成是作者原本的 inclusion/exclusion criteria。

要注意的是，repo 目前 `topic_pipeline.py` 不 consume `stage_projection`；它真正收集與處理的是 `sources`、`inclusion_criteria.required`、`inclusion_criteria.any_of` 與 `exclusion_criteria`。見 R10、R11。也就是說，如果你把 derived reviewer guidance 只放在 `stage_projection`，那它目前不會實際影響 runtime。這件事要嘛接受，要嘛未來改 code。

# 7. 我建議的下一步

第一步，先落地一版 source-faithful rewrite，只改這兩個 criteria JSON，不改 pipeline、不改 senior prompt、不改 aggregation、不改其他 paper。

第二步，對照 historical data 做一輪 diff。這一輪的主要成功標準不是 precision/F1，而是兩件事：第一，criteria 內沒有任何一句話超出原篇；第二，runtime 實際讀到的 consumable fields 已完全替換成 source-faithful 版本。

第三步，如果你之後仍然要追更好的 operational performance，請把下一輪明確命名成 derived operational criteria，而不是再把它混進原篇 criteria rewrite。這樣未來做 error analysis 時，你才能分辨是 paper boundary 本身、還是 runtime projection policy 在出問題。

# 8. 結論

若只問一句話：接下來這兩篇該怎麼改？

我的答案是：`2511` 與 `2409` 都先退回 source-faithful rewrite。`2511` 退回到原文三條 eligibility 加上 preference-learning 的原文定義；`2409` 退回到 IC.1-IC.4 與 EC.1-EC.4 的直譯，並保留 process extraction 的原文 scope。不要再把 current repo 裡那些為了 runtime performance 而加的硬化句子，直接算成作者原本 criteria 的一部分。

如果你要的是「忠於原篇」而不是「這一輪先把 F1 壓到最好」，這就是我認為最乾淨、最可 defend 的做法。

# 9. 附件說明

本報告另外附兩份可直接下載的 JSON 建議稿：

第一份是 `2511.13936.source_faithful_rewrite.json`。

第二份是 `2409.13738.source_faithful_rewrite.json`。

它們都只保留原篇能直接支持的 criteria wording，不再混入超出原篇的 operational hardening。

# 10. 參考來源

1. R1. [Preference-Based Learning in Audio Applications: A Systematic Analysis, Section 3.5 Final Selection and Inclusion](https://arxiv.org/html/2511.13936v1)
2. R2. [Preference-Based Learning in Audio Applications: A Systematic Analysis, Section 3 Methods and keyword refinement](https://arxiv.org/html/2511.13936v1)
3. R3. [Repo current criteria JSON for `2511.13936`](https://raw.githubusercontent.com/Sologa/NLP_PRISMA_Reviews/refs/heads/master/criteria_jsons/2511.13936.json)
4. R4. [NLP4PBM: A Systematic Review on Process Extraction using Natural Language Processing with Rule-based, Machine and Deep Learning Methods, Inclusion and Exclusion Criteria](https://arxiv.org/html/2409.13738v1)
5. R5. [NLP4PBM: Exclusion examples in EC.3 and EC.4](https://arxiv.org/html/2409.13738v1)
6. R6. [NLP4PBM: Introduction and process extraction definition](https://arxiv.org/html/2409.13738v1)
7. R7. [NLP4PBM Appendix A1, included paper titles showing generation / discovery / creation / semi-automatic families](https://arxiv.org/html/2409.13738v1)
8. R8. [NLP4PBM conclusion on target process models and covered scope](https://arxiv.org/html/2409.13738v1)
9. R9. [Repo current criteria JSON for `2409.13738`](https://raw.githubusercontent.com/Sologa/NLP_PRISMA_Reviews/refs/heads/master/criteria_jsons/2409.13738.json)
10. R10. [Repo handoff: current system state and criteria-focused direction](https://raw.githubusercontent.com/Sologa/NLP_PRISMA_Reviews/master/docs/chatgpt_current_status_handoff.md)
11. R11. [Repo `topic_pipeline.py`: consumable criteria fields and lack of `stage_projection` consumption](https://github.com/Sologa/NLP_PRISMA_Reviews/blob/master/scripts/screening/vendor/src/pipelines/topic_pipeline.py)
