# QA Generation General Prompt Report

## Executive Summary

本交付已完成以下內容：

- 先完整閱讀 16 篇 SR 的 PDF 本體，再做 comparative analysis
- 產出 1 份 **General Stage 1 QA Generation Prompt**
- 產出 1 份 **General Stage 2 QA Generation Prompt**
- 產出全部 **16 篇 Stage 1 QA**
- 產出全部 **16 篇 Stage 2 QA**
- 合計 **32 份 QA assets**
- 另附 **PDF Reading Log**、**Revision Log**、**16-paper Comparative Matrix**、**zip-ready manifest**

重要透明說明：使用者指定的 GitHub 路徑 `refs/<paper_id>/<paper_id>.pdf` 在 raw repo 檢查時不存在，因此我逐篇改以 **arXiv original PDF** 完成全文閱讀；該事實已寫入 reading log 與各 QA file 的 source note。


## Current-State Recap

本次工作先以 repo 的 current-state 檔案對齊背景，再開始讀 16 篇 SR PDF 與生成 QA。採納的 current-state 事實如下：

1. current runtime prompt source 是 `scripts/screening/runtime_prompts/runtime_prompts.json`
2. current production Stage 1 criteria 來源是 `criteria_stage1/<paper_id>.json`
3. current production Stage 2 criteria 來源是 `criteria_stage2/<paper_id>.json`
4. `criteria_jsons/*.json` 屬 historical/reference artifacts，不是 current production criteria
5. repo 明確禁止把 derived operational hardening 回寫成 formal criteria
6. repo 明確拒絕第三層 hidden guidance / hidden policy 作為正式 criteria layer
7. 因此這次的交付定位是：
   - QA generation prompts
   - generated QA assets
   - workflow support  
   而不是：
   - new criteria
   - hidden criteria
   - rewritten production criteria


## PDF Reading Log

完整逐篇閱讀紀錄見 [`../logs/pdf_reading_log.md`](../logs/pdf_reading_log.md)。

|paper_id|repo PDF 路徑狀態|實際閱讀來源|頁數|完成閱讀|
|---|---|---|---:|---|
|`2303.13365`|`refs/2303.13365/2303.13365.pdf` missing on raw GitHub|arXiv original PDF|12|Yes|
|`2306.12834`|`refs/2306.12834/2306.12834.pdf` missing on raw GitHub|arXiv original PDF|58|Yes|
|`2307.05527`|`refs/2307.05527/2307.05527.pdf` missing on raw GitHub|arXiv original PDF|16|Yes|
|`2310.07264`|`refs/2310.07264/2310.07264.pdf` missing on raw GitHub|arXiv original PDF|14|Yes|
|`2312.05172`|`refs/2312.05172/2312.05172.pdf` missing on raw GitHub|arXiv original PDF|30|Yes|
|`2401.09244`|`refs/2401.09244/2401.09244.pdf` missing on raw GitHub|arXiv original PDF|35|Yes|
|`2405.15604`|`refs/2405.15604/2405.15604.pdf` missing on raw GitHub|arXiv original PDF|36|Yes|
|`2407.17844`|`refs/2407.17844/2407.17844.pdf` missing on raw GitHub|arXiv original PDF|24|Yes|
|`2409.13738`|`refs/2409.13738/2409.13738.pdf` missing on raw GitHub|arXiv original PDF|50|Yes|
|`2503.04799`|`refs/2503.04799/2503.04799.pdf` missing on raw GitHub|arXiv original PDF|54|Yes|
|`2507.07741`|`refs/2507.07741/2507.07741.pdf` missing on raw GitHub|arXiv original PDF|20|Yes|
|`2507.18910`|`refs/2507.18910/2507.18910.pdf` missing on raw GitHub|arXiv original PDF|33|Yes|
|`2509.11446`|`refs/2509.11446/2509.11446.pdf` missing on raw GitHub|arXiv original PDF|73|Yes|
|`2510.01145`|`refs/2510.01145/2510.01145.pdf` missing on raw GitHub|arXiv original PDF|29|Yes|
|`2511.13936`|`refs/2511.13936/2511.13936.pdf` missing on raw GitHub|arXiv original PDF|27|Yes|
|`2601.19926`|`refs/2601.19926/2601.19926.pdf` missing on raw GitHub|arXiv original PDF|40|Yes|

## 16-Paper Comparative Matrix

|paper id|主題|eligibility 結構形狀|metadata-only 條件類型|title/abstract observable 條件類型|full-text-only 條件類型|Stage 1 QA design patterns|Stage 2 QA design patterns|anti-patterns|contamination risk|stage split feasibility|
|---|---|---|---|---|---|---|---|---|---|---|
|`2303.13365`|NLP / ML for requirement formalisation in requirements engineering|結構清楚、偏傳統：時間窗 + 發表型態/同儕審查 + 語言 + 主題任務（requirements → formalisation）+ 次級研究/灰色文獻排除。|2012-01 到 2022-03；英文；peer-reviewed journal / conference / workshop；排除書籍、網站、技術報告、白皮書、tutorial、重複紀錄。|title/abstract 可觀測核心是：是否處理 requirements text、是否用 NLP/ML、自動或半自動生成 formal model / formal representation，而非一般 RE 任務。|全文確認 formalisation 的輸入與輸出、是否為 primary study、是否落在可接受 publication form 與 date/language window，並排除 review / grey literature。|任務-輸出雙重可觀測：requirements text + formalisation artifact。|以 formal output、primary-study 身分與書目條件做 confirmatory closure。|把一般 RE/NLP 任務誤當 RF；把灰色文獻條件混入語義 QA。|中：formalisation 與鄰近 RE 任務邊界易混。|高：題名摘要通常能看出 requirements + formal model generation。|
|`2306.12834`|ML/DL-based NLP over EHR clinical narratives|屬於 domain + method + task-family 的複合結構：EHR / clinical narratives 為 domain，ML/DL 為方法門檻，再加至少一個納入任務族群；另有 publication-form 排除。|peer-reviewed journal 或 full conference paper；排除 preprint / preliminary / editorial / review；無明確年份硬門檻。|是否處理 EHR / EMR / clinical notes；是否以 ML/DL/NLP 分析臨床文本；是否屬於納入任務族群（classification, NER, ICD coding, summarization, embeddings, dialogue 等）。|全文確認研究是否「solely」或中心聚焦於 EHR 文本分析、方法是否真為 ML/DL、是否屬 full paper 且 peer-reviewed，並排除 editorial / review / tangential use。|domain + method + any-of task family。|用全文確認 EHR centrality、ML/DL 主體性與 publication form。|把 task examples 寫成全都必須；把 medical NLP 泛化為 EHR NLP。|中：醫療 NLP 範圍大，EHR 中心性容易被稀釋。|中高：摘要常能看出 EHR、臨床文本與 ML/DL 任務。|
|`2307.05527`|Generative audio models and their ethical implications|高度排他、負向家族豐富：generative audio 為主題核心，final output 必須是音訊；排除 ASR→text、video output、non-generative、extra primary outputs、只做 metric / incremental tweak、過度寬泛 multimodal papers。|2018-02-01 到 2023-02-01；full research paper；非 extended abstract / book chapter / non-full-paper；coding 證據只允許 main text + appendices。|題名摘要通常可見 generative audio centrality、audio final output、是否明顯為 ASR / classification / video / multimodal-broad paper。|全文確認 publication form、audio-only final output、paper 是否只是 metric / incremental method、以及 eligibility 是否依賴外部 supplement 才能成立。|以 output modality、generative status、centrality 先做 observable partition。|加入 publication form 與 evidence-scope confirmation。|將本 paper 的負向家族誤通用化；把 audio-only 邊界偷渡到其他 SR。|高：paper-specific negative exemplars 非常多。|高：題名摘要大多可看出 generative audio / ASR / video / classification 等關鍵邊界。|
|`2310.07264`|Severity-level dysarthria classification|任務極專一：不是一般 dysarthria detection，而是 severity-level classification，且強調 intelligibility 作為 severity 對應因素；有多個鄰近非目標任務排除。|明確 metadata gate 不多；主要是排除 review / survey / 章節型總述。|dysarthria 是否為主題；是否明示 severity levels / severity grading；是否落入非目標家族如 therapy、general recognition、feature-only analysis、binary classification。|全文確認任務是否真為 severity-level classification，是否評估 intelligibility / severity correspondence，並排除其他神經語音病症與一般性工具論文。|用病症 + task granularity + obvious negatives 做強分流。|全文確認 severity labels 與 intelligibility 角色。|把一般 dysarthria detection 誤收；把 feature analysis 當 severity classification。|中高：鄰近任務很多。|中：題名摘要常可見 severity / intelligibility，但細節偶爾要正文確認。|
|`2312.05172`|NLP methods for long-sentence summarization/compression/splitting/split-and-rephrase|結構混合 topic + metadata：長句處理任務族群為主，另有時間窗、語言、full-text、publication type，以及 pre-2017 citation threshold。|2000 至 2025；英文；full-text article；journal 或 conference；排除 dissertation / thesis / technical report；若 pre-2017，citation < 10 排除。|title/abstract 是否明示 long sentences 與 sentence-level summarization / compression / splitting / split-and-rephrase；是否只是一般 simplification / paraphrase / document summarization。|全文確認 paper 真正處理長句、屬 sentence-level operation、滿足 publication / language / full-text / citation metadata 要件，並排除灰色文獻。|sentence-level 長句任務族群投影。|全文驗證真正的 sentence-level target 與 metadata gates。|把 document-level summarization 誤收；把 citation filter 混成語義 QA。|中高：長句處理與一般 simplification 邊界易混。|中高：題名摘要通常能看出 long sentence 與 sentence-level task。|
|`2401.09244`|Cross-lingual / multilingual-with-transfer abusive or offensive language detection|重點不只是 offensive language detection，而是跨語言知識轉移；含 general abusive content 與 subtype detection，並明確排除跨平台/跨domain transfer、無 transfer 的低資源語言研究、competition reports 與 dissertations。|無明確年份硬門檻；排除 competition reports / papers、Master / PhD dissertations。|題名摘要是否同時出現 offensive / abusive / hate speech 類任務與 cross-lingual / multilingual transfer across languages。|全文確認 transfer 的軸線真的是 language，不是 platform/domain；確認 text classification 性質、general abusive 或 subtype detection，以及 publication-form exclusions。|task + transfer-axis 雙條件。|全文確認 language transfer、abuse subtype、publication-form 邊界。|把 multilingual 無 transfer 誤收；把 domain transfer 當 cross-lingual。|中高：transfer 概念很容易被寬化。|高：摘要通常會明示 cross-lingual / multilingual transfer 與 offensive language detection。|
|`2405.15604`|General NLP text generation, excluding multimodality and domain-specific studies outside review scope|相對寬鬆：核心是「對 text generation 有 relevance」，再排除 multimodality 與明顯屬於其他領域（如 medicine）的過度專題化研究；另有 2017–2023 年時間窗。|發表年份 2017–2023；無明確 peer-review / language 硬條件寫成 formal inclusion。|題名摘要是否中心聚焦 text generation；是否明顯為 multimodal generation；是否主要服務於其他領域如 medicine；是否只是鄰近 NLP 任務。|全文確認該研究對 general text generation 的 relevance、排除 multimodal focus 與 field-specific studies；本 SR 的 Stage 2 以 relevance confirmation 為主，而非更多 formal gates。|寬 scope 下的 centrality / relevance observable QA。|用全文做 relevance closure，而不是編造新 criteria。|把 retrieval gate 假裝成 screening QA；把主觀 relevance hardening 寫回 formal criteria。|高：原 review criteria 寬且帶主觀判斷。|低中：可分，但 Stage 2 主要是 confirm relevance，不是硬規則 closure。|
|`2407.17844`|Deep learning for Parkinson’s disease classification from speech|topic-specific but clear：PD classification + speech data + deep learning；排除傳統 ML / GMM / HMM、非 speech modality、其他疾病、review；另有 2020 之後時間窗。|2020 之後；排除 duplicates；review literature 排除。|是否處理 PD classification；是否使用 speech 作主要資料；是否使用 deep learning；是否明顯落在非 speech 或傳統 ML。|全文確認 speech 為 primary modality、方法確屬 deep learning、任務是 PD-specific classification，而非 broader neurodegenerative disease 或 non-speech analyses。|domain + modality + method-family 三分。|全文確認主模態與方法正確性。|忽略 DL gate；把非 speech 或其他疾病 paper 誤收。|中：method-family 與 modality 邊界都很明確。|高：題名摘要通常直接寫 PD + speech + deep learning / CNN / Transformer。|
|`2409.13738`|NLP for process extraction from natural-language text|source-faithful、最適合 stage split 的案例：Stage 2 canonical 為 IC.1–IC.4 / EC.1–EC.4；Stage 1 只保留 title/abstract observable 的 process-extraction core fit，並將 paper type / originality / concrete method / empirical validation defer 到 Stage 2。|peer-reviewed conference / journal；full text available；English；full research article；primary research；no year restriction。|是否 specifically cover NLP for process extraction from natural-language text；是否有 process-model / process-representation extraction objective；是否明顯落在非目標家族（process redesign / matching / prediction / sentiment / label-only / text-from-process generation）。|全文確認 publication form、language/full text、primary-study 身分、specific process extraction fit、concrete method、empirical validation，並排除所有非目標家族。|純 observable projection + defer strategy。|canonical full-eligibility closure。|把 operational hardening 寫回 criteria；把 negative examples generalize。|高：repo 明確禁止 criteria supertranslation。|高：Stage 1 / Stage 2 split 已有 current production precedent。|
|`2503.04799`|Direct speech-to-speech translation without intermediate text|task-specific：direct S2ST 為主，強調 machine-learning / neural models 與「避免 intermediate text representations」；排除 cascade S2ST、text-only 或 audio-only translation、scant experiments、solely outdated datasets。|2016–2024 發表年份。|是否是 speech-to-speech translation；是否 direct / end-to-end / no intermediate text；是否有 neural / ML model signal；是否明顯是 cascade 或非 S2ST。|全文確認 pipeline 沒有 intermediate text、模型屬於 direct S2ST、實驗與 datasets 具有實質內容，並排除 cascade 與非 S2ST papers。|task + pipeline-shape + model-family。|用方法節和實驗節確認 directness 與 substantive experimentation。|把示例模型寫成必要條件；把資料新舊過度硬化。|中：direct vs cascade 明確，但 experimental sufficiency 容易被過度主觀化。|高：摘要多半會直接說 direct / end-to-end S2ST。|
|`2507.07741`|End-to-end ASR for code-switched speech|核心是 published peer-reviewed research on E2E ASR for code-switched speech；analysis 重點在較新的 E2E systems。因 explicit exclusion families 稀少，需保守生成 QA。|peer-reviewed venues；analysis set 主要聚焦 2018–2024 的 E2E 系統（但不得過度硬化）。|題名摘要是否同時具備 code-switching / code-switched speech 與 end-to-end ASR 兩個中心訊號。|全文確認 E2E ASR 是核心方法、code-switching 是核心現象、publication form 為 peer-reviewed research，並以保守方式處理年份與 recency 描述。|只問最核心的雙條件：code-switching + E2E ASR。|用全文確認中心性與 peer-review，年份作輔助 metadata。|在 criteria 稀疏時自行發明硬門檻。|高：原 paper 給的 formal criteria 很少。|中：主題可觀測，但 publication-form 與 temporal nuance 要保守。|
|`2507.18910`|RAG systems and closely related retriever-generator integrations|核心是 RAG 或 closely related baseline：需要 retrieval + generation integration、knowledge-intensive task、substantive methodology；另允許 peer-reviewed 或 reputable source，含 preprints，英文。|2017–mid-2025 retrieval window；英文；peer-reviewed 或 otherwise reputable source；preprints 可納入；non-substantive publication 排除。|題名摘要是否顯示 RAG / retriever-generator integration、retrieved context conditioning generation、knowledge-intensive task；是否顯然只是 retrieval-only / generation-only / peripheral mention。|全文確認 integration 為核心、RAG 非 peripheral、task 真為 knowledge-intensive、publication 足夠 substantive，並將 source reputation 作為 metadata note 而非語義替代。|integration + centrality + task-scope。|全文確認 integration/centrality/substance，metadata 層另記 source quality。|把 source reputation 當語義 criteria；把 peripheral mention 誤收。|高：topic fit 與 source-quality 容易糾纏。|中高：摘要常能看出 retriever-generator integration 與 RAG centrality。|
|`2509.11446`|LLMs supporting requirements engineering tasks|核心是 primary studies using LLMs to support RE tasks；metadata gates 包含 peer-reviewed conf/workshop/journal、venue quality、English、>=5 pages；另排除 secondary/tertiary、book chapters、無 empirical evaluation 的 conceptual papers。|peer-reviewed conference/workshop/journal；CORE A*/A/B conferences；Q1/Q2 journals；對應 workshop；英文；>=5 pages。|是否以 LLMs 支援 RE tasks 為中心；是否可見 empirical / primary-study signal；是否明顯為 review / conceptual / short paper / book chapter。|全文與外部 metadata 確認 venue quality、page count、peer review、empirical evaluation、RE-task centrality，並排除非 primary studies。|task centrality + primary/empirical signal。|外部 metadata closure + full-text empirical confirmation。|用 venue rank 取代 topic fit；把 conceptual paper 誤當 empirical。|高：metadata 門檻很多，容易回流到語義層。|中高：摘要通常能看出 LLM + RE，但 empirical / venue quality 需 Stage 2。|
|`2510.01145`|ASR for African low-resource languages|domain-specific and clear：ASR for African low-resource languages，且研究內容需涉及 datasets、models 或 evaluation techniques；另有 2020-01 到 2025-07 日期窗與 quality score >= 3/5。|2020-01 到 2025-07；duplicates 排除；quality assessment score 必須 >= 3/5。|是否為 ASR；是否聚焦 African languages / African low-resource languages；是否處理 datasets / models / evaluation techniques；是否顯然非 ASR 或非 African language。|全文確認 low-resource African language scope、ASR centrality、貢獻類型在 scope 內，並做 quality-threshold closure。|task + language/geography + contribution type。|全文確認 low-resource African scope 與 quality threshold。|把非 ASR speech papers 誤收；把 quality score 提前混入 Stage 1。|中高：quality threshold 很容易被誤放到 early screening。|高：摘要通常能看出 ASR + African languages。|
|`2511.13936`|Preference learning in audio applications|核心邊界在 preference-learning definition：ranking / A-B comparisons、numeric ratings 只有在轉成 preferences 時才算、沒有 explicit comparisons 但有 RL training loop for audio model 也可算；audio-domain 包含 multimodal including audio；preferences-only-for-evaluation 排除；survey/review 排除。|canonical criteria 幾乎沒有正式 metadata gate；2020+、citation threshold、peer-review 等只屬 corpus construction / retrieval history，不可寫成 screening criteria。|title/abstract 是否有 preference-learning signal、audio-domain signal、learning-not-evaluation-only signal，以及 survey/review negative。|全文確認 preference signal 的具體形式（pairwise / ranking / converted ratings / RL loop）、audio applicability（multimodal including audio allowed）、preferences 是否真正進入 learning，而非只做 evaluation。|observable preference signal + audio-domain fit + evaluation-vs-learning boundary。|full-text resolution of preference mechanism and role of preferences in learning。|把 historical hardening 回流；把 multimodal-with-audio 誤排；把 ratings 未轉 preference 也誤收。|高：repo 已明示這篇最 fragile 之一。|高：題名摘要通常能看出 preference learning / RLHF-like signal / audio domain。|
|`2601.19926`|Empirical interpretability research on syntactic knowledge in Transformer language models|核心非常明確：Transformer-based language models + empirical assessment/analysis of syntax；排除 non-transformers、encoder-decoder MT-oriented architectures、非 syntax 分析、以及 non-empirical survey/review/position papers；publication type 可接受 journal / conference / archived preprint，且有 cut-off date。|publication type 為 journal / conference / archived preprint；publication cut-off <= 2025-07-31。|是否處理 Transformer-based language models；是否聚焦 syntactic knowledge / syntax；是否具有 empirical analysis 訊號；是否明顯屬於 survey / review / non-transformer / encoder-decoder MT paper。|全文確認 model family、syntax centrality、empirical analysis 性質、publication type/cut-off，並排除位置文與非 syntax interpretability paper。|architecture + linguistic target + empirical signal。|全文確認 syntax-specific empirical interpretability in TLMs。|把 family examples exhaustive 化；把 database workflow 當 eligibility。|中：criteria 清楚，但 architecture scope 易被過窄或過寬。|高：題名摘要通常足以看出 Transformer + syntax + empirical analysis。|

## General Prompt Design Principles

1. **先讀完整個 SR PDF，再抽象 prompt**  
   prompt 不是從 criteria 摘要逆向拼裝，而是先從全文理解正式 eligibility，再決定 Stage 1 / Stage 2 如何切分。

2. **source-faithful，而不是 criteria rewrite**  
   這次交付的是 QA generation prompts 與 generated QA assets，不是 new criteria、hidden criteria 或第三層 policy。

3. **metadata-only 與語義條件分層**  
   年份、語言、peer review、venue type、page count、citation threshold、source reputation、quality score 等保持在 metadata 層；topic / task / modality / output / primary-study signal 則進入語義 QA。

4. **Stage 1 只做 observable projection**  
   任何不能穩定由 title/abstract 判定的條件，一律 defer 給 Stage 2，而不是 invent proxy。

5. **Stage 2 接住 unresolved fields**  
   Stage 2 不是重複 Stage 1，而是用全文去確認 publication form、primary-study 身分、method centrality、empirical validation、subtle boundary cases，以及摘要與正文的衝突。

6. **paper-specific negative families 只能 local 使用**  
   例如 2409 的 process prediction / matching、2511 的 ratings conversion / RL loop、2307 的 audio-only output，都只能存在於各自的 QA，不可升級成 truly general prompt 的內建常識。

7. **生成結構化、可 synthesis 的 QA**  
   每題都必須包含 question、expected answer form、quote requirement、location requirement、state、missingness；Stage 2 額外包含 conflict_note 與 resolves_stage1，避免最後只剩自由文本。


## Revision Log

- **Round 0**：先把每篇 SR 拆成 metadata / observable / confirmatory 三層，但還有 paper-specific negative family 被誤通用化的風險。  
- **Round 1**：強化 Stage 1 只做 observable projection，卻仍發現部分 Stage 2 問題帶有 verdict 語氣。  
- **Round 2**：加入 synthesis-ready schema、`conflict_note`、`resolves_stage1`，並明文禁止 retrieval gate / historical hardening 回流。  
- **Final**：固定為 source-faithful QA generation；只生成問題集與 handoff，不重寫 criteria、不生成 verdict。  
完整紀錄見 [`../logs/revision_log.md`](../logs/revision_log.md)。

## Final General Stage 1 Prompt

獨立檔案見 [`../prompts/general_stage1_qa_generation_prompt.md`](../prompts/general_stage1_qa_generation_prompt.md)。

```markdown
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

```

## Final General Stage 2 Prompt

獨立檔案見 [`../prompts/general_stage2_qa_generation_prompt.md`](../prompts/general_stage2_qa_generation_prompt.md)。

```markdown
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

```

## Generated QA Assets

下列 32 份 QA 已全部生成：

### Stage 1

- [`qa_generated/2303.13365_stage1_qa.md`](../qa_generated/2303.13365_stage1_qa.md)
- [`qa_generated/2306.12834_stage1_qa.md`](../qa_generated/2306.12834_stage1_qa.md)
- [`qa_generated/2307.05527_stage1_qa.md`](../qa_generated/2307.05527_stage1_qa.md)
- [`qa_generated/2310.07264_stage1_qa.md`](../qa_generated/2310.07264_stage1_qa.md)
- [`qa_generated/2312.05172_stage1_qa.md`](../qa_generated/2312.05172_stage1_qa.md)
- [`qa_generated/2401.09244_stage1_qa.md`](../qa_generated/2401.09244_stage1_qa.md)
- [`qa_generated/2405.15604_stage1_qa.md`](../qa_generated/2405.15604_stage1_qa.md)
- [`qa_generated/2407.17844_stage1_qa.md`](../qa_generated/2407.17844_stage1_qa.md)
- [`qa_generated/2409.13738_stage1_qa.md`](../qa_generated/2409.13738_stage1_qa.md)
- [`qa_generated/2503.04799_stage1_qa.md`](../qa_generated/2503.04799_stage1_qa.md)
- [`qa_generated/2507.07741_stage1_qa.md`](../qa_generated/2507.07741_stage1_qa.md)
- [`qa_generated/2507.18910_stage1_qa.md`](../qa_generated/2507.18910_stage1_qa.md)
- [`qa_generated/2509.11446_stage1_qa.md`](../qa_generated/2509.11446_stage1_qa.md)
- [`qa_generated/2510.01145_stage1_qa.md`](../qa_generated/2510.01145_stage1_qa.md)
- [`qa_generated/2511.13936_stage1_qa.md`](../qa_generated/2511.13936_stage1_qa.md)
- [`qa_generated/2601.19926_stage1_qa.md`](../qa_generated/2601.19926_stage1_qa.md)

### Stage 2

- [`qa_generated/2303.13365_stage2_qa.md`](../qa_generated/2303.13365_stage2_qa.md)
- [`qa_generated/2306.12834_stage2_qa.md`](../qa_generated/2306.12834_stage2_qa.md)
- [`qa_generated/2307.05527_stage2_qa.md`](../qa_generated/2307.05527_stage2_qa.md)
- [`qa_generated/2310.07264_stage2_qa.md`](../qa_generated/2310.07264_stage2_qa.md)
- [`qa_generated/2312.05172_stage2_qa.md`](../qa_generated/2312.05172_stage2_qa.md)
- [`qa_generated/2401.09244_stage2_qa.md`](../qa_generated/2401.09244_stage2_qa.md)
- [`qa_generated/2405.15604_stage2_qa.md`](../qa_generated/2405.15604_stage2_qa.md)
- [`qa_generated/2407.17844_stage2_qa.md`](../qa_generated/2407.17844_stage2_qa.md)
- [`qa_generated/2409.13738_stage2_qa.md`](../qa_generated/2409.13738_stage2_qa.md)
- [`qa_generated/2503.04799_stage2_qa.md`](../qa_generated/2503.04799_stage2_qa.md)
- [`qa_generated/2507.07741_stage2_qa.md`](../qa_generated/2507.07741_stage2_qa.md)
- [`qa_generated/2507.18910_stage2_qa.md`](../qa_generated/2507.18910_stage2_qa.md)
- [`qa_generated/2509.11446_stage2_qa.md`](../qa_generated/2509.11446_stage2_qa.md)
- [`qa_generated/2510.01145_stage2_qa.md`](../qa_generated/2510.01145_stage2_qa.md)
- [`qa_generated/2511.13936_stage2_qa.md`](../qa_generated/2511.13936_stage2_qa.md)
- [`qa_generated/2601.19926_stage2_qa.md`](../qa_generated/2601.19926_stage2_qa.md)

## Zip-Ready Manifest

完整 manifest 見 [`../manifest.md`](../manifest.md)。

```text
report/
  qa_generation_general_prompt_report.md
prompts/
  general_stage1_qa_generation_prompt.md
  general_stage2_qa_generation_prompt.md
logs/
  pdf_reading_log.md
  revision_log.md
qa_generated/
  32 markdown QA files
manifest.md
```

## Final Recommendations

1. **把這 32 份 QA 當 workflow support，而不是 criteria rewrite**  
   若要接入 repo runtime，建議將這些 QA 問題集映射到 reviewer evidence schema 或 handoff object，而不要直接覆蓋 `criteria_stage1/` / `criteria_stage2/`。

2. **優先先接四篇 current fragile / current active papers**  
   若要做實驗接線，先處理已有 current stage criteria 的 `2307.05527`、`2409.13738`、`2511.13936`、`2601.19926`，再擴展到其餘 12 篇。

3. **把 Stage 1 / Stage 2 QA 的輸出結構固定化**  
   後續若要接 synthesis，建議維持：
   - Stage 1：`qid / question / quote / location / state / missingness / handoff`
   - Stage 2：再加 `conflict_note / resolves_stage1`
   這樣才不會回到只剩自由文本的 reviewer outputs。

