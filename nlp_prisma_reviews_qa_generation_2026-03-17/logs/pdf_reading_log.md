# PDF Reading Log

本 log 逐篇記錄 16 篇 SR 的全文閱讀結果。重要說明：使用者指定的 GitHub 路徑 `refs/<paper_id>/<paper_id>.pdf` 在 repo raw 檢查中皆不存在，因此本次逐篇改以 **arXiv original PDF** 完成全文閱讀，並在下方逐篇明示。

|paper_id|SR title|repo path status|actual read source|pages|PDF 完成閱讀|
|---|---|---|---|---:|---|
|`2303.13365`|Requirement Formalisation using Natural Language Processing and Machine Learning: A Systematic Review|`refs/2303.13365/2303.13365.pdf` missing on raw GitHub|arXiv original PDF|12|Yes|
|`2306.12834`|Natural Language Processing in Electronic Health Records in Relation to Healthcare: A Systematic Review|`refs/2306.12834/2306.12834.pdf` missing on raw GitHub|arXiv original PDF|58|Yes|
|`2307.05527`|The Ethical Implications of Generative Audio Models: A Systematic Literature Review|`refs/2307.05527/2307.05527.pdf` missing on raw GitHub|arXiv original PDF|16|Yes|
|`2310.07264`|Classification of Dysarthria based on the Levels of Severity. A Systematic Review|`refs/2310.07264/2310.07264.pdf` missing on raw GitHub|arXiv original PDF|14|Yes|
|`2312.05172`|From Lengthy to Lucid: A Systematic Literature Review on NLP Techniques for Taming Long Sentences|`refs/2312.05172/2312.05172.pdf` missing on raw GitHub|arXiv original PDF|30|Yes|
|`2401.09244`|Cross-lingual Offensive Language Detection: A Systematic Review of Datasets, Transfer Approaches and Challenges|`refs/2401.09244/2401.09244.pdf` missing on raw GitHub|arXiv original PDF|35|Yes|
|`2405.15604`|Text Generation: A Systematic Literature Review of Tasks, Evaluation, and Challenges|`refs/2405.15604/2405.15604.pdf` missing on raw GitHub|arXiv original PDF|36|Yes|
|`2407.17844`|Innovative Speech-Based Deep Learning Approaches for Parkinson’s Disease Classification: A Systematic Review|`refs/2407.17844/2407.17844.pdf` missing on raw GitHub|arXiv original PDF|24|Yes|
|`2409.13738`|NLP4PBM: A Systematic Review on Process Extraction using Natural Language Processing with Rule-based, Machine and Deep Learning Methods|`refs/2409.13738/2409.13738.pdf` missing on raw GitHub|arXiv original PDF|50|Yes|
|`2503.04799`|Direct Speech to Speech Translation: A Review|`refs/2503.04799/2503.04799.pdf` missing on raw GitHub|arXiv original PDF|54|Yes|
|`2507.07741`|Code-Switching in End-to-End Automatic Speech Recognition: A Systematic Literature Review|`refs/2507.07741/2507.07741.pdf` missing on raw GitHub|arXiv original PDF|20|Yes|
|`2507.18910`|A Systematic Review of Key Retrieval-Augmented Generation (RAG) Systems: Progress, Gaps, and Future Directions|`refs/2507.18910/2507.18910.pdf` missing on raw GitHub|arXiv original PDF|33|Yes|
|`2509.11446`|Large Language Models (LLMs) for Requirements Engineering (RE): A Systematic Literature Review|`refs/2509.11446/2509.11446.pdf` missing on raw GitHub|arXiv original PDF|73|Yes|
|`2510.01145`|Automatic Speech Recognition (ASR) for African Low-Resource Languages: A Systematic Literature Review|`refs/2510.01145/2510.01145.pdf` missing on raw GitHub|arXiv original PDF|29|Yes|
|`2511.13936`|Preference-Based Learning in Audio Applications: A Systematic Analysis|`refs/2511.13936/2511.13936.pdf` missing on raw GitHub|arXiv original PDF|27|Yes|
|`2601.19926`|The Grammar of Transformers: A Systematic Review of Interpretability Research on Syntactic Knowledge in Language Models|`refs/2601.19926/2601.19926.pdf` missing on raw GitHub|arXiv original PDF|40|Yes|

## 2303.13365 — Requirement Formalisation using Natural Language Processing and Machine Learning: A Systematic Review

1. **paper id**: `2303.13365`
2. **PDF 是否完成閱讀**: Yes。已完成 12 頁全文閱讀；repo 指定路徑 `refs/2303.13365/2303.13365.pdf` 缺失，改讀 arXiv original PDF。
3. **eligibility / inclusion / exclusion 結構**: 結構清楚、偏傳統：時間窗 + 發表型態/同儕審查 + 語言 + 主題任務（requirements → formalisation）+ 次級研究/灰色文獻排除。
4. **metadata-only 條件**: 2012-01 到 2022-03；英文；peer-reviewed journal / conference / workshop；排除書籍、網站、技術報告、白皮書、tutorial、重複紀錄。
5. **Stage 1 可觀測條件**: title/abstract 可觀測核心是：是否處理 requirements text、是否用 NLP/ML、自動或半自動生成 formal model / formal representation，而非一般 RE 任務。
6. **Stage 2 full-text / confirmatory 條件**: 全文確認 formalisation 的輸入與輸出、是否為 primary study、是否落在可接受 publication form 與 date/language window，並排除 review / grey literature。
7. **這篇 paper 對 general Stage 1 prompt 的啟發**: 提醒 general Stage 1 prompt 不能只問「有沒有 NLP」，而要問「是否把自然語言需求轉成 formal artifact」。
8. **這篇 paper 對 general Stage 2 prompt 的啟發**: 提醒 general Stage 2 prompt 要把 publication-form / language / year 這類 metadata gate 與全文語義確認分開處理。
9. **這篇 paper 的 anti-pattern / contamination risk**: 污染風險是把 requirements engineering 的其他任務（分類、追蹤、缺陷、user-story 分析）錯當 formalisation；以及把灰色文獻排除寫成語義問題。

## 2306.12834 — Natural Language Processing in Electronic Health Records in Relation to Healthcare: A Systematic Review

1. **paper id**: `2306.12834`
2. **PDF 是否完成閱讀**: Yes。已完成 58 頁全文閱讀；repo 指定路徑 `refs/2306.12834/2306.12834.pdf` 缺失，改讀 arXiv original PDF。
3. **eligibility / inclusion / exclusion 結構**: 屬於 domain + method + task-family 的複合結構：EHR / clinical narratives 為 domain，ML/DL 為方法門檻，再加至少一個納入任務族群；另有 publication-form 排除。
4. **metadata-only 條件**: peer-reviewed journal 或 full conference paper；排除 preprint / preliminary / editorial / review；無明確年份硬門檻。
5. **Stage 1 可觀測條件**: 是否處理 EHR / EMR / clinical notes；是否以 ML/DL/NLP 分析臨床文本；是否屬於納入任務族群（classification, NER, ICD coding, summarization, embeddings, dialogue 等）。
6. **Stage 2 full-text / confirmatory 條件**: 全文確認研究是否「solely」或中心聚焦於 EHR 文本分析、方法是否真為 ML/DL、是否屬 full paper 且 peer-reviewed，並排除 editorial / review / tangential use。
7. **這篇 paper 對 general Stage 1 prompt 的啟發**: 提醒 Stage 1 general prompt 需要允許「任務族群 any-of」而非把所有例子寫成必備條件。
8. **這篇 paper 對 general Stage 2 prompt 的啟發**: 提醒 Stage 2 general prompt 要能確認 domain centrality（EHR 只是資料來源還是研究中心）與 full-paper / peer-review metadata。
9. **這篇 paper 的 anti-pattern / contamination risk**: 污染風險是把列舉的任務例子誤寫成通用硬規則，或把任何 medical NLP 都誤收進來。

## 2307.05527 — The Ethical Implications of Generative Audio Models: A Systematic Literature Review

1. **paper id**: `2307.05527`
2. **PDF 是否完成閱讀**: Yes。已完成 16 頁全文閱讀；repo 指定路徑 `refs/2307.05527/2307.05527.pdf` 缺失，改讀 arXiv original PDF。
3. **eligibility / inclusion / exclusion 結構**: 高度排他、負向家族豐富：generative audio 為主題核心，final output 必須是音訊；排除 ASR→text、video output、non-generative、extra primary outputs、只做 metric / incremental tweak、過度寬泛 multimodal papers。
4. **metadata-only 條件**: 2018-02-01 到 2023-02-01；full research paper；非 extended abstract / book chapter / non-full-paper；coding 證據只允許 main text + appendices。
5. **Stage 1 可觀測條件**: 題名摘要通常可見 generative audio centrality、audio final output、是否明顯為 ASR / classification / video / multimodal-broad paper。
6. **Stage 2 full-text / confirmatory 條件**: 全文確認 publication form、audio-only final output、paper 是否只是 metric / incremental method、以及 eligibility 是否依賴外部 supplement 才能成立。
7. **這篇 paper 對 general Stage 1 prompt 的啟發**: 提醒 Stage 1 prompt 可保留 paper-specific negative families，但只能在該 SR 的 QA 裡出現，不能升級成 general rule。
8. **這篇 paper 對 general Stage 2 prompt 的啟發**: 提醒 Stage 2 prompt 需要處理「證據範圍限制」：若 eligibility 只能靠外部 supplemental material 才能成立，應單獨提問。
9. **這篇 paper 的 anti-pattern / contamination risk**: 污染風險是把本 paper 的強負向家族（ASR、video、extra outputs）誤當所有 review 都適用；或把 audio-only 過度一般化。

## 2310.07264 — Classification of Dysarthria based on the Levels of Severity. A Systematic Review

1. **paper id**: `2310.07264`
2. **PDF 是否完成閱讀**: Yes。已完成 14 頁全文閱讀；repo 指定路徑 `refs/2310.07264/2310.07264.pdf` 缺失，改讀 arXiv original PDF。
3. **eligibility / inclusion / exclusion 結構**: 任務極專一：不是一般 dysarthria detection，而是 severity-level classification，且強調 intelligibility 作為 severity 對應因素；有多個鄰近非目標任務排除。
4. **metadata-only 條件**: 明確 metadata gate 不多；主要是排除 review / survey / 章節型總述。
5. **Stage 1 可觀測條件**: dysarthria 是否為主題；是否明示 severity levels / severity grading；是否落入非目標家族如 therapy、general recognition、feature-only analysis、binary classification。
6. **Stage 2 full-text / confirmatory 條件**: 全文確認任務是否真為 severity-level classification，是否評估 intelligibility / severity correspondence，並排除其他神經語音病症與一般性工具論文。
7. **這篇 paper 對 general Stage 1 prompt 的啟發**: 提醒 Stage 1 prompt 對 highly specific task review 要把鄰近任務明確拆開提問，不可只問「是不是 dysarthria」。
8. **這篇 paper 對 general Stage 2 prompt 的啟發**: 提醒 Stage 2 prompt 要能確認 task granularity（severity levels vs binary detection）與 clinically meaningful target signal。
9. **這篇 paper 的 anti-pattern / contamination risk**: 污染風險是把所有 dysarthria-ASR / dysarthria detection 都納入，或把 feature analysis 誤當 severity classification。

## 2312.05172 — From Lengthy to Lucid: A Systematic Literature Review on NLP Techniques for Taming Long Sentences

1. **paper id**: `2312.05172`
2. **PDF 是否完成閱讀**: Yes。已完成 30 頁全文閱讀；repo 指定路徑 `refs/2312.05172/2312.05172.pdf` 缺失，改讀 arXiv original PDF。
3. **eligibility / inclusion / exclusion 結構**: 結構混合 topic + metadata：長句處理任務族群為主，另有時間窗、語言、full-text、publication type，以及 pre-2017 citation threshold。
4. **metadata-only 條件**: 2000 至 2025；英文；full-text article；journal 或 conference；排除 dissertation / thesis / technical report；若 pre-2017，citation < 10 排除。
5. **Stage 1 可觀測條件**: title/abstract 是否明示 long sentences 與 sentence-level summarization / compression / splitting / split-and-rephrase；是否只是一般 simplification / paraphrase / document summarization。
6. **Stage 2 full-text / confirmatory 條件**: 全文確認 paper 真正處理長句、屬 sentence-level operation、滿足 publication / language / full-text / citation metadata 要件，並排除灰色文獻。
7. **這篇 paper 對 general Stage 1 prompt 的啟發**: 提醒 Stage 1 prompt 應允許一個 SR 有多個 task-family option，但仍要保持 sentence-level granularity。
8. **這篇 paper 對 general Stage 2 prompt 的啟發**: 提醒 Stage 2 prompt 要能容納外部 metadata confirmation，例如 pre-2017 citation threshold，且不要把它寫成語義問題。
9. **這篇 paper 的 anti-pattern / contamination risk**: 污染風險是把 document summarization、一般 text simplification 或 paraphrase 誤認為 long-sentence taming。

## 2401.09244 — Cross-lingual Offensive Language Detection: A Systematic Review of Datasets, Transfer Approaches and Challenges

1. **paper id**: `2401.09244`
2. **PDF 是否完成閱讀**: Yes。已完成 35 頁全文閱讀；repo 指定路徑 `refs/2401.09244/2401.09244.pdf` 缺失，改讀 arXiv original PDF。
3. **eligibility / inclusion / exclusion 結構**: 重點不只是 offensive language detection，而是跨語言知識轉移；含 general abusive content 與 subtype detection，並明確排除跨平台/跨domain transfer、無 transfer 的低資源語言研究、competition reports 與 dissertations。
4. **metadata-only 條件**: 無明確年份硬門檻；排除 competition reports / papers、Master / PhD dissertations。
5. **Stage 1 可觀測條件**: 題名摘要是否同時出現 offensive / abusive / hate speech 類任務與 cross-lingual / multilingual transfer across languages。
6. **Stage 2 full-text / confirmatory 條件**: 全文確認 transfer 的軸線真的是 language，不是 platform/domain；確認 text classification 性質、general abusive 或 subtype detection，以及 publication-form exclusions。
7. **這篇 paper 對 general Stage 1 prompt 的啟發**: 提醒 Stage 1 prompt 要把「主題」與「轉移軸線」分開問，避免只抓到 offensive language detection 卻漏掉 cross-lingual 核心。
8. **這篇 paper 對 general Stage 2 prompt 的啟發**: 提醒 Stage 2 prompt 要能辨別 multilingual 但無 transfer 與真正 cross-lingual knowledge transfer 的差異。
9. **這篇 paper 的 anti-pattern / contamination risk**: 污染風險是把 multilingual 研究一律視為 cross-lingual，或把 domain adaptation / platform transfer 誤當語言轉移。

## 2405.15604 — Text Generation: A Systematic Literature Review of Tasks, Evaluation, and Challenges

1. **paper id**: `2405.15604`
2. **PDF 是否完成閱讀**: Yes。已完成 36 頁全文閱讀；repo 指定路徑 `refs/2405.15604/2405.15604.pdf` 缺失，改讀 arXiv original PDF。
3. **eligibility / inclusion / exclusion 結構**: 相對寬鬆：核心是「對 text generation 有 relevance」，再排除 multimodality 與明顯屬於其他領域（如 medicine）的過度專題化研究；另有 2017–2023 年時間窗。
4. **metadata-only 條件**: 發表年份 2017–2023；無明確 peer-review / language 硬條件寫成 formal inclusion。
5. **Stage 1 可觀測條件**: 題名摘要是否中心聚焦 text generation；是否明顯為 multimodal generation；是否主要服務於其他領域如 medicine；是否只是鄰近 NLP 任務。
6. **Stage 2 full-text / confirmatory 條件**: 全文確認該研究對 general text generation 的 relevance、排除 multimodal focus 與 field-specific studies；本 SR 的 Stage 2 以 relevance confirmation 為主，而非更多 formal gates。
7. **這篇 paper 對 general Stage 1 prompt 的啟發**: 提醒 general Stage 1 prompt 必須能處理「relevance-based review」而不強行製造不存在的 hard criteria。
8. **這篇 paper 對 general Stage 2 prompt 的啟發**: 提醒 general Stage 2 prompt 在 criteria 本身寬鬆時，應把全文確認寫成 scope/centrality 問題，而不是捏造硬門檻。
9. **這篇 paper 的 anti-pattern / contamination risk**: 污染風險最高的是把檢索策略、引用網路或主觀 relevance hardening 偽裝成正式 criteria；以及把 multimodality / medicine 這些 paper-specific exclusions 一般化。

## 2407.17844 — Innovative Speech-Based Deep Learning Approaches for Parkinson’s Disease Classification: A Systematic Review

1. **paper id**: `2407.17844`
2. **PDF 是否完成閱讀**: Yes。已完成 24 頁全文閱讀；repo 指定路徑 `refs/2407.17844/2407.17844.pdf` 缺失，改讀 arXiv original PDF。
3. **eligibility / inclusion / exclusion 結構**: topic-specific but clear：PD classification + speech data + deep learning；排除傳統 ML / GMM / HMM、非 speech modality、其他疾病、review；另有 2020 之後時間窗。
4. **metadata-only 條件**: 2020 之後；排除 duplicates；review literature 排除。
5. **Stage 1 可觀測條件**: 是否處理 PD classification；是否使用 speech 作主要資料；是否使用 deep learning；是否明顯落在非 speech 或傳統 ML。
6. **Stage 2 full-text / confirmatory 條件**: 全文確認 speech 為 primary modality、方法確屬 deep learning、任務是 PD-specific classification，而非 broader neurodegenerative disease 或 non-speech analyses。
7. **這篇 paper 對 general Stage 1 prompt 的啟發**: 提醒 Stage 1 prompt 可把 domain、modality、model-family 分成三題，不要壓成一個大問句。
8. **這篇 paper 對 general Stage 2 prompt 的啟發**: 提醒 Stage 2 prompt 對方法家族（DL vs non-DL）與 modality（speech vs gait / handwriting / imaging）要有 confirmatory QA。
9. **這篇 paper 的 anti-pattern / contamination risk**: 污染風險是把任何 PD speech paper 都納入，忽略 deep learning gate；或把 multimodal clinical studies 誤視為 speech-primary。

## 2409.13738 — NLP4PBM: A Systematic Review on Process Extraction using Natural Language Processing with Rule-based, Machine and Deep Learning Methods

1. **paper id**: `2409.13738`
2. **PDF 是否完成閱讀**: Yes。已完成 50 頁全文閱讀；repo 指定路徑 `refs/2409.13738/2409.13738.pdf` 缺失，改讀 arXiv original PDF。
3. **eligibility / inclusion / exclusion 結構**: source-faithful、最適合 stage split 的案例：Stage 2 canonical 為 IC.1–IC.4 / EC.1–EC.4；Stage 1 只保留 title/abstract observable 的 process-extraction core fit，並將 paper type / originality / concrete method / empirical validation defer 到 Stage 2。
4. **metadata-only 條件**: peer-reviewed conference / journal；full text available；English；full research article；primary research；no year restriction。
5. **Stage 1 可觀測條件**: 是否 specifically cover NLP for process extraction from natural-language text；是否有 process-model / process-representation extraction objective；是否明顯落在非目標家族（process redesign / matching / prediction / sentiment / label-only / text-from-process generation）。
6. **Stage 2 full-text / confirmatory 條件**: 全文確認 publication form、language/full text、primary-study 身分、specific process extraction fit、concrete method、empirical validation，並排除所有非目標家族。
7. **這篇 paper 對 general Stage 1 prompt 的啟發**: 提醒 Stage 1 prompt 對 fragile review 應只做 observable projection，不可偷塞 paper-type 或 validation hardening。
8. **這篇 paper 對 general Stage 2 prompt 的啟發**: 提醒 Stage 2 prompt 要能承接 unresolved fields，並以 canonical source-faithful criteria 做 closure。
9. **這篇 paper 的 anti-pattern / contamination risk**: 最高污染風險是把 source/target object、text-to-process relation 之類 operational hardening 寫回 formal criteria，或把非目標例子轉成 general prompt 內建知識。

## 2503.04799 — Direct Speech to Speech Translation: A Review

1. **paper id**: `2503.04799`
2. **PDF 是否完成閱讀**: Yes。已完成 54 頁全文閱讀；repo 指定路徑 `refs/2503.04799/2503.04799.pdf` 缺失，改讀 arXiv original PDF。
3. **eligibility / inclusion / exclusion 結構**: task-specific：direct S2ST 為主，強調 machine-learning / neural models 與「避免 intermediate text representations」；排除 cascade S2ST、text-only 或 audio-only translation、scant experiments、solely outdated datasets。
4. **metadata-only 條件**: 2016–2024 發表年份。
5. **Stage 1 可觀測條件**: 是否是 speech-to-speech translation；是否 direct / end-to-end / no intermediate text；是否有 neural / ML model signal；是否明顯是 cascade 或非 S2ST。
6. **Stage 2 full-text / confirmatory 條件**: 全文確認 pipeline 沒有 intermediate text、模型屬於 direct S2ST、實驗與 datasets 具有實質內容，並排除 cascade 與非 S2ST papers。
7. **這篇 paper 對 general Stage 1 prompt 的啟發**: 提醒 Stage 1 prompt 對 pipeline-shape 很重要的 review，要把「是否 direct」明確獨立成題。
8. **這篇 paper 對 general Stage 2 prompt 的啟發**: 提醒 Stage 2 prompt 可用 full text 釐清 architecture details 與 experimental sufficiency，但不要捏造額外門檻。
9. **這篇 paper 的 anti-pattern / contamination risk**: 污染風險是把 example models（如 Translatotron 2, UnitY）寫成硬必要條件，或把 dataset 新舊程度過度 operationalize。

## 2507.07741 — Code-Switching in End-to-End Automatic Speech Recognition: A Systematic Literature Review

1. **paper id**: `2507.07741`
2. **PDF 是否完成閱讀**: Yes。已完成 20 頁全文閱讀；repo 指定路徑 `refs/2507.07741/2507.07741.pdf` 缺失，改讀 arXiv original PDF。
3. **eligibility / inclusion / exclusion 結構**: 核心是 published peer-reviewed research on E2E ASR for code-switched speech；analysis 重點在較新的 E2E systems。因 explicit exclusion families 稀少，需保守生成 QA。
4. **metadata-only 條件**: peer-reviewed venues；analysis set 主要聚焦 2018–2024 的 E2E 系統（但不得過度硬化）。
5. **Stage 1 可觀測條件**: 題名摘要是否同時具備 code-switching / code-switched speech 與 end-to-end ASR 兩個中心訊號。
6. **Stage 2 full-text / confirmatory 條件**: 全文確認 E2E ASR 是核心方法、code-switching 是核心現象、publication form 為 peer-reviewed research，並以保守方式處理年份與 recency 描述。
7. **這篇 paper 對 general Stage 1 prompt 的啟發**: 提醒 Stage 1 prompt 對 criteria 稀疏的 paper 要採 conservative extraction，不可自己補滿不存在的排除家族。
8. **這篇 paper 對 general Stage 2 prompt 的啟發**: 提醒 Stage 2 prompt 要用 full text 補足中心性與 publication-form confirmation，而不是 invented hardening。
9. **這篇 paper 的 anti-pattern / contamination risk**: 污染風險最高的是因為 explicit exclusions 太少，就自己發明 dataset / language / architecture filters。

## 2507.18910 — A Systematic Review of Key Retrieval-Augmented Generation (RAG) Systems: Progress, Gaps, and Future Directions

1. **paper id**: `2507.18910`
2. **PDF 是否完成閱讀**: Yes。已完成 33 頁全文閱讀；repo 指定路徑 `refs/2507.18910/2507.18910.pdf` 缺失，改讀 arXiv original PDF。
3. **eligibility / inclusion / exclusion 結構**: 核心是 RAG 或 closely related baseline：需要 retrieval + generation integration、knowledge-intensive task、substantive methodology；另允許 peer-reviewed 或 reputable source，含 preprints，英文。
4. **metadata-only 條件**: 2017–mid-2025 retrieval window；英文；peer-reviewed 或 otherwise reputable source；preprints 可納入；non-substantive publication 排除。
5. **Stage 1 可觀測條件**: 題名摘要是否顯示 RAG / retriever-generator integration、retrieved context conditioning generation、knowledge-intensive task；是否顯然只是 retrieval-only / generation-only / peripheral mention。
6. **Stage 2 full-text / confirmatory 條件**: 全文確認 integration 為核心、RAG 非 peripheral、task 真為 knowledge-intensive、publication 足夠 substantive，並將 source reputation 作為 metadata note 而非語義替代。
7. **這篇 paper 對 general Stage 1 prompt 的啟發**: 提醒 Stage 1 prompt 要把 RAG integration 與 retrieval-only / generation-only 明確拆開，且不要把 source reputation 混進語義題。
8. **這篇 paper 對 general Stage 2 prompt 的啟發**: 提醒 Stage 2 prompt 在 source-quality 條件存在時，要把它留在 metadata 層，正文只處理是否真的有 retriever-generator integration。
9. **這篇 paper 的 anti-pattern / contamination risk**: 高風險污染是把「major venue / recognized industrial labs」這種 corpus-building heuristic 寫成一般 screening criteria，或把 minimal RAG mention 誤收。

## 2509.11446 — Large Language Models (LLMs) for Requirements Engineering (RE): A Systematic Literature Review

1. **paper id**: `2509.11446`
2. **PDF 是否完成閱讀**: Yes。已完成 73 頁全文閱讀；repo 指定路徑 `refs/2509.11446/2509.11446.pdf` 缺失，改讀 arXiv original PDF。
3. **eligibility / inclusion / exclusion 結構**: 核心是 primary studies using LLMs to support RE tasks；metadata gates 包含 peer-reviewed conf/workshop/journal、venue quality、English、>=5 pages；另排除 secondary/tertiary、book chapters、無 empirical evaluation 的 conceptual papers。
4. **metadata-only 條件**: peer-reviewed conference/workshop/journal；CORE A*/A/B conferences；Q1/Q2 journals；對應 workshop；英文；>=5 pages。
5. **Stage 1 可觀測條件**: 是否以 LLMs 支援 RE tasks 為中心；是否可見 empirical / primary-study signal；是否明顯為 review / conceptual / short paper / book chapter。
6. **Stage 2 full-text / confirmatory 條件**: 全文與外部 metadata 確認 venue quality、page count、peer review、empirical evaluation、RE-task centrality，並排除非 primary studies。
7. **這篇 paper 對 general Stage 1 prompt 的啟發**: 提醒 Stage 1 prompt 要把「LLM for RE」與「LLM mentioned in SE context」區分開來，並將 venue-quality 完全留在 metadata 層。
8. **這篇 paper 對 general Stage 2 prompt 的啟發**: 提醒 Stage 2 prompt 可承接 external metadata gates（CORE/Q ranking, page count），但不應讓這些 metadata 取代正文對 RE support 的確認。
9. **這篇 paper 的 anti-pattern / contamination risk**: 污染風險是讓 venue ranking 和頁數門檻主導語義判定，或把 conceptual papers 只憑 abstract 就直接當 empirical。

## 2510.01145 — Automatic Speech Recognition (ASR) for African Low-Resource Languages: A Systematic Literature Review

1. **paper id**: `2510.01145`
2. **PDF 是否完成閱讀**: Yes。已完成 29 頁全文閱讀；repo 指定路徑 `refs/2510.01145/2510.01145.pdf` 缺失，改讀 arXiv original PDF。
3. **eligibility / inclusion / exclusion 結構**: domain-specific and clear：ASR for African low-resource languages，且研究內容需涉及 datasets、models 或 evaluation techniques；另有 2020-01 到 2025-07 日期窗與 quality score >= 3/5。
4. **metadata-only 條件**: 2020-01 到 2025-07；duplicates 排除；quality assessment score 必須 >= 3/5。
5. **Stage 1 可觀測條件**: 是否為 ASR；是否聚焦 African languages / African low-resource languages；是否處理 datasets / models / evaluation techniques；是否顯然非 ASR 或非 African language。
6. **Stage 2 full-text / confirmatory 條件**: 全文確認 low-resource African language scope、ASR centrality、貢獻類型在 scope 內，並做 quality-threshold closure。
7. **這篇 paper 對 general Stage 1 prompt 的啟發**: 提醒 Stage 1 prompt 可把 task、geographic/linguistic scope、contribution type 分開問，避免只抓到 ASR。
8. **這篇 paper 對 general Stage 2 prompt 的啟發**: 提醒 Stage 2 prompt 要能處理 quality-assessment threshold，但它屬 full-text confirmatory / workflow support，不是 title/abstract semantic cue。
9. **這篇 paper 的 anti-pattern / contamination risk**: 污染風險是把任何 African speech paper 都納入，或把 quality score 門檻過早回流到 Stage 1。

## 2511.13936 — Preference-Based Learning in Audio Applications: A Systematic Analysis

1. **paper id**: `2511.13936`
2. **PDF 是否完成閱讀**: Yes。已完成 27 頁全文閱讀；repo 指定路徑 `refs/2511.13936/2511.13936.pdf` 缺失，改讀 arXiv original PDF。
3. **eligibility / inclusion / exclusion 結構**: 核心邊界在 preference-learning definition：ranking / A-B comparisons、numeric ratings 只有在轉成 preferences 時才算、沒有 explicit comparisons 但有 RL training loop for audio model 也可算；audio-domain 包含 multimodal including audio；preferences-only-for-evaluation 排除；survey/review 排除。
4. **metadata-only 條件**: canonical criteria 幾乎沒有正式 metadata gate；2020+、citation threshold、peer-review 等只屬 corpus construction / retrieval history，不可寫成 screening criteria。
5. **Stage 1 可觀測條件**: title/abstract 是否有 preference-learning signal、audio-domain signal、learning-not-evaluation-only signal，以及 survey/review negative。
6. **Stage 2 full-text / confirmatory 條件**: 全文確認 preference signal 的具體形式（pairwise / ranking / converted ratings / RL loop）、audio applicability（multimodal including audio allowed）、preferences 是否真正進入 learning，而非只做 evaluation。
7. **這篇 paper 對 general Stage 1 prompt 的啟發**: 提醒 Stage 1 prompt 對 fragile review 要保留 source-faithful operational definition，但不可加入 peer-review、audio must be core、arXiv citation thresholds 等 historical hardening。
8. **這篇 paper 對 general Stage 2 prompt 的啟發**: 提醒 Stage 2 prompt 要顯式承接 learning-vs-evaluation、converted ratings、RL loop、multimodal-with-audio 等 borderline cases。
9. **這篇 paper 的 anti-pattern / contamination risk**: 最高污染風險是把 historical opv2 hardening、peer-review、citation thresholds、或「audio must be sole/core modality」偷偷回流成正式 screening QA。

## 2601.19926 — The Grammar of Transformers: A Systematic Review of Interpretability Research on Syntactic Knowledge in Language Models

1. **paper id**: `2601.19926`
2. **PDF 是否完成閱讀**: Yes。已完成 40 頁全文閱讀；repo 指定路徑 `refs/2601.19926/2601.19926.pdf` 缺失，改讀 arXiv original PDF。
3. **eligibility / inclusion / exclusion 結構**: 核心非常明確：Transformer-based language models + empirical assessment/analysis of syntax；排除 non-transformers、encoder-decoder MT-oriented architectures、非 syntax 分析、以及 non-empirical survey/review/position papers；publication type 可接受 journal / conference / archived preprint，且有 cut-off date。
4. **metadata-only 條件**: publication type 為 journal / conference / archived preprint；publication cut-off <= 2025-07-31。
5. **Stage 1 可觀測條件**: 是否處理 Transformer-based language models；是否聚焦 syntactic knowledge / syntax；是否具有 empirical analysis 訊號；是否明顯屬於 survey / review / non-transformer / encoder-decoder MT paper。
6. **Stage 2 full-text / confirmatory 條件**: 全文確認 model family、syntax centrality、empirical analysis 性質、publication type/cut-off，並排除位置文與非 syntax interpretability paper。
7. **這篇 paper 對 general Stage 1 prompt 的啟發**: 提醒 Stage 1 prompt 在 architecture-specific review 中，要把 model family、linguistic phenomenon、empiricality 分開問。
8. **這篇 paper 對 general Stage 2 prompt 的啟發**: 提醒 Stage 2 prompt 應能解決「Transformer 但不是 LM」與「interpretability 但不是 syntax」的細邊界。
9. **這篇 paper 的 anti-pattern / contamination risk**: 污染風險是把 examples（BERT/GPT）寫成唯一合法 family，或把 review-seed database workflow 混成正式 criteria。
