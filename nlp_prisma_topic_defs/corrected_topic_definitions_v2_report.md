# Corrected `topic_definition` values for `criteria_jsons/*.json`

## What changed

- `topic_definition` should define the **SR topic itself**, not describe the included studies.

- The current repo spec says `topic_definition` is a **one-sentence topic definition**.

- The current parser still copies the first markdown heading into both `topic` and `topic_definition`, so a manual or scripted correction is needed.


## Revised entries

### 2303.13365 — Requirement Formalisation using Natural Language Processing and Machine Learning: A Systematic Review

**Corrected `topic_definition`**

Requirement formalisation is the task of converting informal natural-language software or system requirements into precise, formal, machine-interpretable representations such as logic, models, or specifications.

**中文解說**

這個主題是在談：把人寫的自然語言需求轉成形式化、可被工具分析的表示，目的是降低歧義、提升一致性，並支援後續設計、驗證或自動化分析。

**專有名詞解釋**

- **Requirement formalisation**：把原本用自然語言寫出的需求，轉成較精確、可推理、可驗證的形式表示。
- **Natural Language Processing (NLP)**：讓電腦處理人類語言的技術，例如斷詞、句法分析、資訊抽取。
- **Machine Learning (ML)**：讓模型從資料中學規律，而不是完全靠人工寫規則。
- **Deep Learning (DL)**：ML 的一類，通常用多層神經網路學更複雜的表示。
- **Requirements Engineering (RE)**：軟體/系統開發中，蒐集、分析、整理、驗證需求的整體過程。

**Source**: https://arxiv.org/abs/2303.13365

### 2306.12834 — Natural Language Processing in Electronic Health Records in Relation to Healthcare Decision-making: A Systematic Review

**Corrected `topic_definition`**

Natural language processing in electronic health records for healthcare decision-making is the use of computational language methods to extract, classify, summarize, or translate information from free-text clinical records so that it can support clinical or administrative decisions.

**中文解說**

這個主題是在談：把電子健康紀錄中的自由文字病歷、醫療筆記、臨床敘述變成可分析的資訊，用來協助診斷、編碼、風險評估、照護決策或行政決策。

**專有名詞解釋**

- **Electronic Health Records (EHRs)**：電子化的病人醫療紀錄，常包含結構化欄位與自由文字。
- **Free-text clinical records**：沒有固定格式、由醫護人員以自然語言撰寫的病歷內容。
- **Clinical entity recognition**：從醫療文字中找出疾病、藥物、症狀、檢查等實體。
- **Text summarisation**：把長篇醫療文字濃縮成較短但保留重點的摘要。
- **Information extraction**：從文字中抽出結構化資訊，例如診斷、時間、檢查結果。

**Source**: https://arxiv.org/abs/2306.12834

### 2307.05527 — The Ethical Implications of Generative Audio Models: A Systematic Literature Review

**Corrected `topic_definition`**

The ethical implications of generative audio models are the moral, legal, and social issues created by systems that synthesize speech, music, or other audio, including deception, fraud, copyright infringement, consent, bias, and misuse.

**中文解說**

這個主題不是單純談怎麼生成音訊，而是在定義這類系統可能帶來的倫理、法律與社會風險，例如冒充他人、詐騙、偽造聲音、版權爭議、偏見與濫用。

**專有名詞解釋**

- **Generative audio model**：可以自動合成語音、音樂或其他聲音的模型。
- **Deepfake audio**：用 AI 合成、模仿特定人的聲音，可能用於偽造或欺騙。
- **Copyright infringement**：未經授權使用受著作權保護的內容，可能構成侵權。
- **Consent**：當事人是否同意自己的聲音、資料或作品被拿來訓練或生成。
- **Bias**：模型對不同族群、口音、語言或音樂風格產生系統性不公平。

**Source**: https://arxiv.org/abs/2307.05527

### 2310.07264 — Classification of Dysarthria based on the Levels of Severity. A Systematic Review

**Corrected `topic_definition`**

Dysarthria severity classification is the task of assigning dysarthric speech to severity levels, typically by analyzing acoustic, prosodic, or learned speech representations to support objective assessment.

**中文解說**

這個主題是在談：如何根據患者語音，自動或半自動判斷構音障礙有多嚴重，讓評估更客觀、可重現，不完全依賴人工主觀判讀。

**專有名詞解釋**

- **Dysarthria**：由神經系統問題導致的運動性言語障礙，可能影響發音清晰度、節奏與可懂度。
- **Severity level**：疾病或障礙的嚴重程度分級，例如輕度、中度、重度。
- **Acoustic features**：從聲音訊號抽出的量化特徵，例如頻率、能量、共振峰、時長。
- **Prosody**：語音中的節奏、重音、語調與停頓等特性。
- **Speech-language pathologist (SLP)**：語言治療師／言語病理專家，負責評估與治療語言或言語障礙。

**Source**: https://arxiv.org/abs/2310.07264

### 2312.05172 — From Lengthy to Lucid: A Systematic Literature Review on NLP Techniques for Taming Long Sentences

**Corrected `topic_definition`**

NLP techniques for taming long sentences are methods that improve the readability and comprehensibility of overly long sentences, chiefly through sentence compression and sentence splitting while preserving meaning.

**中文解說**

這個主題是在談：如何把過長、難讀的句子處理得更清楚、更容易理解，通常靠刪掉冗餘內容或把一句拆成多句，同時盡量保留原意。

**專有名詞解釋**

- **Sentence compression**：在不改變核心意思的前提下，把句子縮短。
- **Sentence splitting**：把一個很長的句子拆成兩句或多句，降低理解負擔。
- **Supervised learning**：利用標註好的輸入—輸出範例來訓練模型。
- **Weakly supervised learning**：只依賴較弱、較粗糙或不完整的標註訊號進行學習。
- **Self-supervised learning**：從未標註資料本身設計學習目標，讓模型自動學表示。

**Source**: https://arxiv.org/abs/2312.05172

### 2401.09244 — Cross-lingual Offensive Language Detection: A Systematic Review of Datasets, Transfer Approaches and Challenges

**Corrected `topic_definition`**

Cross-lingual offensive language detection is the task of identifying offensive or harmful text in one language by leveraging data, representations, or models transferred from one or more other languages.

**中文解說**

這個主題是在談：當目標語言缺少足夠資料時，能不能借助其他語言的資料、特徵或模型，來偵測辱罵、仇恨、侮辱或其他冒犯性內容。

**專有名詞解釋**

- **Offensive language detection**：自動辨識侮辱、辱罵、仇恨、歧視或其他有害文字內容。
- **Cross-lingual**：跨語言，指模型或知識從一種語言轉移到另一種語言。
- **Transfer learning**：先在某些資料或任務上學到能力，再轉用到新任務或新語言。
- **Multilingual dataset**：同時包含多種語言資料的資料集。
- **Instance / feature / parameter transfer**：三種常見遷移方式：轉移資料樣本、轉移表示特徵、或轉移模型參數。

**Source**: https://arxiv.org/abs/2401.09244

### 2405.15604 — Text Generation: A Systematic Literature Review of Tasks, Evaluation, and Challenges

**Corrected `topic_definition`**

Text generation is the automatic production of coherent natural-language output by computational models across tasks such as open-ended generation, summarization, translation, paraphrasing, and question answering.

**中文解說**

這個主題是在談 NLP 系統如何自動生成文字，包含不同任務類型、常見評估方法，以及文字生成普遍會遇到的共通問題。

**專有名詞解釋**

- **Open-ended generation**：沒有非常嚴格格式限制的自由生成，例如故事、文章、回覆。
- **Summarization**：把較長內容濃縮成較短摘要。
- **Paraphrasing**：保留原意但改寫表達方式。
- **Question answering**：根據問題生成答案的任務。
- **Hallucination**：模型生成了看似合理但其實不正確或無根據的內容。

**Source**: https://arxiv.org/abs/2405.15604

### 2407.17844 — Innovative Speech-Based Deep Learning Approaches for Parkinson's Disease Classification: A Systematic Review

**Corrected `topic_definition`**

Speech-based deep learning for Parkinson's disease classification is the use of neural models to analyze speech signals and distinguish speech associated with Parkinson's disease from non-Parkinsonian speech for screening or diagnostic support.

**中文解說**

這個主題是在談：能不能利用一個人的語音作為非侵入式生物訊號，透過深度學習協助偵測或分類巴金森氏症。

**專有名詞解釋**

- **Parkinson's disease (PD)**：一種神經退化疾病，可能影響動作、聲音與說話方式。
- **Speech-based diagnosis**：用語音特徵作為疾病篩檢或輔助診斷依據。
- **End-to-end learning**：模型直接從原始輸入學到最終任務，不必手工設計太多中間步驟。
- **Transfer learning**：先從其他資料學到能力，再轉移到巴金森語音任務。
- **Explainability**：讓人知道模型為什麼做出某個判斷，而不只是給結果。

**Source**: https://arxiv.org/abs/2407.17844

### 2409.13738 — NLP4PBM: A Systematic Review on Process Extraction using Natural Language Processing with Rule-based, Machine and Deep Learning Methods

**Corrected `topic_definition`**

Automated process extraction is the task of transforming natural-language descriptions of activities, actors, and control flow into structured process representations or process models using natural language processing.

**中文解說**

這個主題是在談：如何把文件、規範、手冊或需求中的文字流程描述，自動轉成流程模型或其他結構化流程表示。

**專有名詞解釋**

- **Process extraction**：從文字中抽取流程步驟、角色、事件與順序關係。
- **Business Process Management (BPM)**：對組織流程進行設計、分析、執行與優化的領域。
- **Process model**：用結構化方式表達流程，例如步驟、分支、順序與角色關係。
- **Rule-based method**：主要依靠人工撰寫規則而不是從資料自動學習。
- **Control flow**：流程中步驟之間的先後、分支、合併與循環關係。

**Source**: https://arxiv.org/abs/2409.13738

### 2503.04799 — Direct Speech to Speech Translation: A Review

**Corrected `topic_definition`**

Direct speech-to-speech translation is the translation of spoken input into spoken output with little or no explicit intermediate text representation, ideally preserving both meaning and salient speech characteristics such as prosody or speaker identity.

**中文解說**

這個主題是在談：輸入是語音、輸出也是語音，而且盡量不先完整轉成文字再翻譯，目標是讓翻譯更即時、自然，也更能保留說話風格。

**專有名詞解釋**

- **Speech-to-speech translation (S2ST)**：把一種語言的語音直接翻成另一種語言的語音。
- **Automatic speech recognition (ASR)**：把語音轉成文字。
- **Machine translation (MT)**：把一種語言的文字翻成另一種語言的文字。
- **Text-to-speech (TTS)**：把文字轉成語音。
- **Cascade model**：先 ASR，再 MT，再 TTS 的串接式系統。
- **Prosody**：語音中的節奏、語調、重音與韻律。

**Source**: https://arxiv.org/abs/2503.04799

### 2507.07741 — Code-Switching in End-to-End Automatic Speech Recognition: A Systematic Literature Review

**Corrected `topic_definition`**

Code-switching in end-to-end automatic speech recognition is the recognition of multilingual speech that alternates between languages within an utterance using a single model that maps audio directly to transcriptions.

**中文解說**

這個主題是在談：當說話者在同一句或同一段中混用兩種以上語言時，端到端語音辨識模型要怎麼正確辨識。

**專有名詞解釋**

- **Code-switching**：說話時在不同語言或語言變體之間切換。
- **End-to-end ASR**：單一模型直接把聲音映射成文字，而不是切成多個模組處理。
- **Transcription**：把語音內容寫成文字的結果。
- **Dataset**：用來訓練或評估模型的語音與標註資料集合。
- **Metric**：衡量模型表現的指標，例如錯誤率。

**Source**: https://arxiv.org/abs/2507.07741

### 2507.18910 — A Systematic Review of Key Retrieval-Augmented Generation (RAG) Systems: Progress, Gaps, and Future Directions

**Corrected `topic_definition`**

Retrieval-augmented generation is an architecture that combines external information retrieval with generative language models so that outputs are conditioned on retrieved evidence rather than only on parametric model memory.

**中文解說**

這個主題是在談：先從外部知識庫、文件或搜尋系統取回相關資料，再讓生成模型根據這些證據產生答案，以提升事實性與上下文相關性。

**專有名詞解釋**

- **Retrieval-Augmented Generation (RAG)**：檢索增強生成；先找資料，再根據資料生成答案。
- **Information retrieval**：從文件集合中找出與問題最相關的內容。
- **Generative language model**：能根據輸入自動生成自然語言輸出的模型。
- **Hallucination**：模型在沒有證據支持下生成錯誤或虛構內容。
- **Agentic RAG**：把多步驟規劃、工具調用或代理式決策加進 RAG 流程的做法。

**Source**: https://arxiv.org/abs/2507.18910

### 2509.11446 — Large Language Models (LLMs) for Requirements Engineering (RE): A Systematic Literature Review

**Corrected `topic_definition`**

Requirements engineering with large language models is the application of large language models to language-intensive requirements tasks such as elicitation, analysis, specification, validation, and related work over requirements artefacts.

**中文解說**

這個主題是在談：把 ChatGPT、GPT-4、LLaMA 這類大型語言模型用到需求工程的不同階段，協助處理需求文件與其他需求相關工件。

**專有名詞解釋**

- **Large Language Model (LLM)**：以大量文字資料訓練、能理解與生成自然語言的大型模型。
- **Requirements engineering (RE)**：蒐集、分析、撰寫、驗證與管理需求的工程活動。
- **Elicitation**：從利害關係人或文件中蒐集需求。
- **Validation**：檢查需求是否正確、完整、一致且符合真實需要。
- **Requirements artefact**：需求工程中產生或使用的文件、issue、規格、法規文本等材料。

**Source**: https://arxiv.org/abs/2509.11446

### 2510.01145 — Automatic Speech Recognition (ASR) for African Low-Resource Languages: A Systematic Literature Review

**Corrected `topic_definition`**

Automatic speech recognition for African low-resource languages is the development and evaluation of speech-to-text systems for African languages that have limited labeled data, tooling, benchmark coverage, or other linguistic and computational resources.

**中文解說**

這個主題是在談：面對資料、工具與基準都不足的非洲語言，如何建立與評估可用的語音辨識系統。

**專有名詞解釋**

- **Automatic speech recognition (ASR)**：把語音自動轉成文字的技術。
- **Low-resource language**：缺乏大量標註資料、工具、詞典、語料或基準測試的語言。
- **Word Error Rate (WER)**：以字詞為單位計算辨識錯誤率的常見 ASR 指標。
- **Character Error Rate (CER)**：以字元為單位計算錯誤率，對某些語言更細緻。
- **Diacritic Error Rate (DER)**：評估重音符號、聲調符號等附加符號錯誤的指標。
- **Self-supervised learning**：利用未標註語音先學表徵，再用少量標註資料微調。

**Source**: https://arxiv.org/abs/2510.01145

### 2511.13936 — Preference-Based Learning in Audio Applications: A Systematic Analysis

**Corrected `topic_definition`**

Preference-based learning in audio is the training or evaluation of audio systems using relative judgments or rankings—often from humans or reward models—to optimize subjective qualities such as naturalness, quality, or musicality.

**中文解說**

這個主題是在談：音訊系統的品質不只靠客觀分數評估，也可以根據人類偏好、成對比較或排序回饋來學習更符合主觀感受的輸出。

**專有名詞解釋**

- **Preference-based learning**：利用「A 比 B 好」這種相對偏好訊號來訓練或評估模型。
- **RLHF**：Reinforcement Learning from Human Feedback，利用人類回饋來調整模型行為。
- **Reward model**：學習預測人類偏好的模型，用來給其他模型訓練訊號。
- **PESQ**：常見的語音品質客觀評估指標。
- **Naturalness**：聲音聽起來像不像自然人聲或自然音訊的主觀感受。

**Source**: https://arxiv.org/abs/2511.13936

### 2601.19926 — The Grammar of Transformers: A Systematic Review of Interpretability Research on Syntactic Knowledge in Language Models

**Corrected `topic_definition`**

Syntactic knowledge in language models is the extent to which language models encode, represent, and use grammatical structure and dependencies, while interpretability research investigates how and where that knowledge is manifested inside the model.

**中文解說**

這個主題是在談：語言模型到底有沒有學到句法規則，以及研究者如何用可解釋性方法去觀察這些語法知識在模型裡的分布與作用。

**專有名詞解釋**

- **Transformer**：現代大型語言模型常用的神經網路架構。
- **Syntactic knowledge**：模型對語法結構、依存關係、詞類與句法規則的掌握程度。
- **Interpretability**：研究模型內部機制與可理解性的方向。
- **Part of speech**：詞類，例如名詞、動詞、形容詞。
- **Agreement**：語法上一致關係，例如主詞與動詞在人稱或數上的一致。
- **Binding / filler-gap dependency**：較複雜的句法現象，涉及指稱關係與長距離依存。

**Source**: https://arxiv.org/abs/2601.19926
