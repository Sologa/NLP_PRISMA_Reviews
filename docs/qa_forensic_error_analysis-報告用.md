# 2409 / 2511 QA Forensic Error Analysis

Date: 2026-03-19

## 1. Current-State Recap

- 本報告依序核對了 `AGENTS.md`、`docs/chatgpt_current_status_handoff.md`、`screening/results/results_manifest.json`、`screening/results/2409.13738_full/CURRENT.md`、`screening/results/2511.13936_full/CURRENT.md`。
- current runtime prompt authority 是 `scripts/screening/runtime_prompts/runtime_prompts.json`。
- current production criteria authority 是 stage-split criteria：
  `criteria_stage1/2409.13738.json`、`criteria_stage2/2409.13738.json`、`criteria_stage1/2511.13936.json`、`criteria_stage2/2511.13936.json`。
- `2409` 與 `2511` current score authority 仍是 `stage_split_criteria_migration`；本次 forensic analysis 的 primary targets 則是你指定的兩個 QA runs：
  `screening/results/qa_first_v1_2409_stage2_followup_2026-03-19/` 與
  `screening/results/qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19/`。
- gold label 以 `refs/<paper>/metadata/title_abstracts_metadata-annotated.jsonl` 中的 `is_evidence_base` 為準。
- `Combined` verdict 不是直接拿 `latte_fulltext_review_results.json` 算；本報告使用
  `Stage 1 whole-set verdict + Stage 2 overwrite Stage 1 positive cases`
  重建 combined confusion inventory。
- 全文證據只對 misclassified cases 做 targeted search，沒有先通讀整個 `refs/<paper>/mds/`。

## 2. Misclassification Inventory

### 2.1 `2409`

- Stage 1 FP:
  `bellan2021process`, `bellan2022extracting`, `bellan2022process`, `bellan_gpt3_2022`, `bellan_pet_23`, `berti2023abstractions`, `bordignon2018natural`, `busch2023just`, `grohs2023large`, `kourani_process_modelling_with_llm`, `lopez2021challenges`, `maqbool2019comprehensive`, `neuberger_data_augment`, `riefer2016mining`, `robeer2016`, `sintoris2017extracting`, `van2018challenges`
- Stage 1 FN:
  `azevedo2018bpmn`
- Combined FP:
  `bellan2022extracting`, `bellan_gpt3_2022`, `robeer2016`
- Combined FN:
  `azevedo2018bpmn`, `goossens2023extracting`, `halioui2018bioinformatic`, `neuberger2023beyond`, `qian2020approach`, `vda_extracting_declarative_process`
- Gold-only unmatched keys, not counted as FP/FN:
  `de2008stanford`, `dumas2018fundamentals`, `omg_bpmn`, `omg_dmn`, `omg_uml`, `weske2007business`

### 2.2 `2511`

- Stage 1 FP:
  `manocha2020differentiable`, `xu2025qwen2`
- Stage 1 FN:
  `chumbalov2020scalable`, `dong2020pyramid`, `huang2025step`, `jayawardena2020ordinal`, `parthasarathy2018preference`
- Combined FP:
  `manocha2020differentiable`
- Combined FN:
  `chumbalov2020scalable`, `dong2020pyramid`, `huang2025step`, `jayawardena2020ordinal`, `parthasarathy2018preference`, `wu2023interval`
- Gold-only unmatched keys, not counted as FP/FN:
  `bradley1952rank`, `itu20031534`, `luce1959individual`, `mantisnlp2023rlhf`

## 3. 2409 Case Dossiers

### 3.1 `azevedo2018bpmn`

- `paper_key`: `azevedo2018bpmn`
- `title`: BPMN Model and Text Instructions Automatic Synchronization
- `abstract`: The proper representation of business processes is important for its execution and understanding. BPMN is the de facto standard notation for business process modeling. However, domain specialists, which are experts in the business, do not have necessarily the modeling skills to easily read a BPMN model. Natural language is easier to read for them. So, both model and text are necessary artifacts for a broad communication. However, unilateral manual editions of them may result in inconsistencies. This research proposes a framework for synchronizing BPMN model artifacts and its natural language text representation. It generates textual work instructions from the model, and it updates the original model if the textual instructions are edited. The framework was implemented using Java standard technology and evaluated through experiments. In the first experiment, we showed the knowledge represented by the textual work instructions and the correspondent process models are equivalent. Furthermore, in a second experiment, we showed our approach for maintaining the texts and models consistent performed satisfactory, where we verified the equivalence of the two artifacts.
- `gold label`: `True`
- `predicted final verdict`: `exclude (senior:2)` at Stage 1; combined stayed exclude because it never reached Stage 2
- `是哪一層出錯`: `Stage 1 early exclude` + `source-target inversion`
- `模型當時的主要判讀理由`: senior 把它讀成「從 model 生成 text」而不是「從 text 萃取 process model」，因此把 `T1/T2` 視為 direct negative。
- `全文 evidence`: `refs/2409.13738/mds/azevedo2018bpmn.md:13-15` 明寫它會 `"generate textual work instructions from the model"`，但同一句也寫 `"updates the original model if the textual instructions are edited"`；`refs/2409.13738/mds/azevedo2018bpmn.md:255-262` 又把 `Text to Model: BPMN Process Model Generation from Natural Language Texts` 獨立成 NLP component，且說它會 `"identify BPMN process model elements"` 並 `"create/update the model"`。
- `為什麼這是一個 FP / FN`: 這是 FN。模型抓到了 paper 的 `model -> text` 半邊，但漏掉了 paper 也明確包含 `text -> model` 半邊，所以把 bidirectional synchronization 誤判成非-target。
- `這是 clean model error，還是 borderline ambiguity`: `borderline ambiguity`。abstract 的第一閱讀確實容易先看到 text generation，但全文已經足夠清楚說明也有 text-to-model branch。
- `如果要寫詳解，最核心的一句話是什麼`: 這篇不是只有 process-to-text；全文明確包含從自然語言文字回推 BPMN model 的 NLP branch。

### 3.2 `bellan2022extracting`

- `paper_key`: `bellan2022extracting`
- `title`: Extracting business process entities and relations from text using pre-trained language models and in-context learning
- `abstract`: The extraction of business processes elements from textual documents is a research area which still lacks the ability to scale to the variety of real-world texts. In this paper we investigate the usage of pre-trained language models and in-context learning to address the problem of information extraction from process description documents as a way to exploit the power of deep learning approaches while relying on few annotated data. In particular, we investigate the usage of the native GPT-3 model and few in-context learning customizations that rely on the usage of conceptual definitions and a very limited number of examples for the extraction of typical business process entities and relationships. The experiments we have conducted provide two types of insights. First, the results demonstrate the feasibility of the proposed approach, especially for what concerns the extraction of activity, participant, and the performs relation between a participant and an activity it performs. They also highlight the challenge posed by control flow relations. Second, it provides a first set of lessons learned on how to interact with these kinds of models that can facilitate future investigations on this subject.
- `gold label`: `False`
- `predicted final verdict`: `maybe (senior:3)` at Stage 2, so combined stayed positive
- `是哪一層出錯`: `Stage 2 closure` + `target-boundary confusion`
- `模型當時的主要判讀理由`: 模型認為它有 concrete method 與 empirical validation，但 target fit 仍 unresolved，於是保留 `maybe`；同時還把 publication form 當成 unresolved。
- `全文 evidence`: `refs/2409.13738/mds/bellan2022extracting.md:44-46` 已經明寫 `EDOC 2022, LNCS 13585` 與 DOI，所以 publication-form 並不 unresolved；`refs/2409.13738/mds/bellan2022extracting.md:127-132` 把它自己的位置定義成 two-step pipeline 的第一步：先抽 process elements，再由第二步建 process model；`refs/2409.13738/mds/bellan2022extracting.md:314-318` 更直接寫本 paper 只抽 `activities`, `participants`, `performing relation`, `sequence relation`，這些只是 `"basic building blocks"`。
- `為什麼這是一個 FP / FN`: 這是 FP。全文支持的是 entity/relation extraction layer，不是 canonical process model / decision model extraction layer；模型把「建模前置 building blocks」留成 positive，邊界放太寬。
- `這是 clean model error，還是 borderline ambiguity`: `clean model error`。全文已經把工作範圍說得比模型保留判讀更窄。
- `如果要寫詳解，最核心的一句話是什麼`: 這篇是在抽 process elements，不是在抽最終 formal process model。

### 3.3 `robeer2016`

- `paper_key`: `robeer2016`
- `title`: Automated Extraction of Conceptual Models from User Stories via NLP
- `abstract`: Natural language (NL) is still the predominant notation that practitioners use to represent software requirements. Albeit easy to read, NL does not readily highlight key concepts and relationships such as dependencies and conflicts. This contrasts with the inherent capability of graphical conceptual models to visualize a given domain in a holistic fashion. In this paper, we propose to automatically derive conceptual models from a concise and widely adopted NL notation for requirements: user stories. Due to their simplicity, we hypothesize that our approach can improve on the low accuracy of previous works. We present an algorithm that combines state-of-the-art heuristics and that is implemented in our Visual Narrator tool. We evaluate our work on two case studies wherein we obtained promising precision and recall results (between 80% and 92%). The creators of the user stories perceived the generated models as a useful artifact to communicate and discuss the requirements, especially for team members who are not yet familiar with the project.
- `gold label`: `False`
- `predicted final verdict`: `maybe (senior:3)` at Stage 2, so combined stayed positive
- `是哪一層出錯`: `Stage 2 closure` + `target-boundary confusion`
- `模型當時的主要判讀理由`: 模型承認它是 original research、method、evaluation 都夠，但把「conceptual model from user stories」當成 process-extraction plausibly-related case，最後保留 `maybe`。
- `全文 evidence`: `refs/2409.13738/mds/robeer2016.md:11-15` 開宗明義寫的是 `"graphical conceptual models"` 與 `"user stories"`；`refs/2409.13738/mds/robeer2016.md:59-64` 說 tool 會 `"creates conceptual models from user stories"` 並生成 `"OWL ontologies"`；`refs/2409.13738/mds/robeer2016.md:1209-1213` 結論再次寫它 `"automatically generates a conceptual model from a collection of agile requirements expressed as user stories"`。
- `為什麼這是一個 FP / FN`: 這是 FP。全文 target 是 requirements/user-story conceptual modeling，不是 business-process / decision-model extraction；模型被「model from text」的表面相似度帶偏。
- `這是 clean model error，還是 borderline ambiguity`: `clean model error`。全文多次把 target object 限定為 conceptual model。
- `如果要寫詳解，最核心的一句話是什麼`: 這篇是 user-story conceptual modeling，不是 process-model extraction。

### 3.4 `goossens2023extracting`

- `paper_key`: `goossens2023extracting`
- `title`: Extracting Decision Model and Notation models from text using deep learning techniques
- `abstract`: Companies and organizations often use manuals and guidelines to communicate and execute operational decisions. Decision Model and Notation (DMN) models can be used to model and automate these decisions. Modeling a decision from a textual source, however, is a time intensive and complex activity hence a need for shorter modeling times. This paper studies how NLP deep learning techniques can extract decision models from text faster. In this paper, we study and evaluate an automatic sentence classifier and a decision dependency extractor using NLP deep learning models (BERT and Bi-LSTM-CRF). A large labeled and tagged dataset was collected from real use cases to train these models. We conclude that BERT can be used for the (semi)-automatic extraction of decision models from text.
- `gold label`: `True`
- `predicted final verdict`: `exclude (senior:2)` after Stage 2; Stage 1 本來是 `maybe`
- `是哪一層出錯`: `Stage 2 closure` + `senior adjudication` + `publication-form overreach`
- `模型當時的主要判讀理由`: Stage 2 evaluator 其實已經是 `clear_include`，但 senior 看到 `Journal Pre-proof` 後，把 publication form 視為未完成、不可納入。
- `全文 evidence`: `refs/2409.13738/mds/goossens2023extracting.md:11-16` 明確寫 `To appear in: Expert Systems With Applications` 與 `Accepted date: 21 August 2022`；`refs/2409.13738/mds/goossens2023extracting.md:20-22` 說這是 `"a PDF file of an article ... after acceptance"`，不是一般 arXiv-only preprint；內容面上，`refs/2409.13738/mds/goossens2023extracting.md:41-47` 直接說用 BERT / Bi-LSTM-CRF 抽 decision models from text；`refs/2409.13738/mds/goossens2023extracting.md:129-144` 與 `:1949-1957` 又清楚列出 pipeline、dataset、experiments、tool。
- `為什麼這是一個 FP / FN`: 這是 FN。方法、target、evaluation 都是正證據，publication-form 也不是「未 peer-reviewed」；模型把 accepted journal pre-proof 當成不合格，closure 收得過頭。
- `這是 clean model error，還是 borderline ambiguity`: `clean model error`。
- `如果要寫詳解，最核心的一句話是什麼`: accepted journal pre-proof 不是未審稿 preprint，不能直接當 publication-form negative。

### 3.5 `qian2020approach`

- `paper_key`: `qian2020approach`
- `title`: An Approach for Process Model Extraction by Multi-grained Text Classification
- `abstract`: Process model extraction (PME) is a recently emerged interdiscipline between natural language processing (NLP) and business process management (BPM), which aims to extract process models from textual descriptions. Previous process extractors heavily depend on manual features and ignore the potential relations between clues of different text granularities. In this paper, we formalize the PME task into the multi-grained text classification problem, and propose a hierarchical neural network to effectively model and extract multi-grained information without manually-defined procedural features. Under this structure, we accordingly propose the coarse-to-fine (grained) learning mechanism, training multi-grained tasks in coarse-to-fine grained order to share the high-level knowledge for the low-level tasks. To evaluate our approach, we construct two multi-grained datasets from two different domains and conduct extensive experiments from different dimensions. The experimental results demonstrate that our approach outperforms the state-of-the-art methods with statistical significance and further investigations demonstrate its effectiveness.
- `gold label`: `True`
- `predicted final verdict`: `exclude (senior:2)` after Stage 2; Stage 1 本來是 `maybe`
- `是哪一層出錯`: `Stage 2 closure`
- `模型當時的主要判讀理由`: senior 接受它在 target / method / evaluation 都是正證據，但因 local fulltext 有 `arXiv` header，就把 publication form 視為 direct negative。
- `全文 evidence`: `refs/2409.13738/mds/qian2020approach.md:8-23` 與 `:46-78` 清楚表明這篇就是 process model extraction from text，且有 hierarchical neural network 與 `"conduct extensive experiments"`；但 `refs/2409.13738/mds/qian2020approach.md:34-35` 左右的 header 同時出現 `arXiv:1906.02127v3 [cs.CL] 20 Mar 2020`，在 candidate fulltext 內看不到像 `To appear in`、conference proceedings header 這種直接 venue confirmation。
- `為什麼這是一個 FP / FN`: 這是 FN，但它不是像 `goossens2023extracting` 那樣乾淨。內容 fit 幾乎完全沒問題，真正衝突的是 publication form：gold 把它算進 evidence base，但 local candidate markdown 只直接給到 arXiv-level metadata。
- `這是 clean model error，還是 borderline ambiguity`: `borderline ambiguity`。以這份 local fulltext 自身來看，模型的 publication-form 顧慮不是憑空捏造；真正不一致的是 gold include 與 local markdown metadata 之間。
- `如果要寫詳解，最核心的一句話是什麼`: 這篇的主衝突不在 task fit，而在 local fulltext 只露出 arXiv metadata，讓 gold include 和 runtime closure 規則產生張力。

### 3.6 `vda_extracting_declarative_process`

- `paper_key`: `vda_extracting_declarative_process`
- `title`: Extracting Declarative Process Models from Natural Language
- `abstract`: Process models are an important means to capture information on organizational operations and often represent the starting point for process analysis and improvement. Since the manual elicitation and creation of process models is a time-intensive endeavor, a variety of techniques have been developed that automatically derive process models from textual process descriptions. However, these techniques, so far, only focus on the extraction of traditional, imperative process models. The extraction of declarative process models, which allow to effectively capture complex process behavior in a compact fashion, has not been addressed. In this paper we close this gap by presenting the first automated approach for the extraction of declarative process models from natural language. To achieve this, we developed tailored Natural Language Processing techniques that identify activities and their inter-relations from textual constraint descriptions. A quantitative evaluation shows that our approach is able to generate constraints that closely resemble those established by humans. Therefore, our approach provides automated support for an otherwise tedious and complex manual endeavor.
- `gold label`: `True`
- `predicted final verdict`: `exclude (senior:2)` after Stage 2; Stage 1 本來是 `maybe`
- `是哪一層出錯`: `Stage 2 closure` + `senior adjudication` + `publication-form overreach`
- `模型當時的主要判讀理由`: 模型承認它是 original NLP method with evaluation，但把它讀成「book chapter，不算 conference/journal」。
- `全文 evidence`: `refs/2409.13738/mds/vda_extracting_declarative_process.md:23-29` 明寫它提出 `"the first automated approach for the extraction of declarative process models from natural language"` 且有 `"quantitative evaluation"`；`refs/2409.13738/mds/vda_extracting_declarative_process.md:41-43` 明確是 `CAiSE 2019, LNCS 11483`；`refs/2409.13738/mds/vda_extracting_declarative_process.md:668-676` 再次說它拿自動抽取結果去對 manually created gold standard 做 quantitative evaluation。
- `為什麼這是一個 FP / FN`: 這是 FN。內容 fit 非常強，而 `CAiSE 2019, LNCS` 比較像 conference proceedings，不支持模型那種「book chapter-only artifact」式排除。
- `這是 clean model error，還是 borderline ambiguity`: `clean model error`。
- `如果要寫詳解，最核心的一句話是什麼`: `CAiSE 2019, LNCS` 被誤讀成 disqualifying book chapter，是這個 case 的核心錯點。

## 4. 2511 Case Dossiers

### 4.1 `manocha2020differentiable`

- `paper_key`: `manocha2020differentiable`
- `title`: A differentiable perceptual audio metric learned from just noticeable differences
- `abstract`: Many audio processing tasks require perceptual assessment. The "gold standard" of obtaining human judgments is time-consuming, expensive, and cannot be used as an optimization criterion. On the other hand, automated metrics are efficient to compute but often correlate poorly with human judgment, particularly for audio differences at the threshold of human detection. In this work, we construct a metric by fitting a deep neural network to a new large dataset of crowdsourced human judgments. Subjects are prompted to answer a straightforward, objective question: are two recordings identical or not? These pairs are algorithmically generated under a variety of perturbations, including noise, reverb, and compression artifacts; the perturbation space is probed with the goal of efficiently identifying the just-noticeable difference (JND) level of the subject. We show that the resulting learned metric is well-calibrated with human judgments, outperforming baseline methods. Since it is a deep network, the metric is differentiable, making it suitable as a loss function for other tasks. Thus, simply replacing an existing loss (e.g., deep feature loss) with our metric yields significant improvement in a denoising network, as measured by subjective pairwise comparison.
- `gold label`: `False`
- `predicted final verdict`: `include (junior:5,4)` after Stage 2
- `是哪一層出錯`: `Stage 2 closure` + `preference-signal overread`
- `模型當時的主要判讀理由`: 模型把 binary `"same or different"` judgments 視為 pairwise preference signal，並因為 network 用這些 labels 訓練，所以給 include。
- `全文 evidence`: `refs/2511.13936/mds/manocha2020differentiable.md:82-84` 與 `:120-123` 明寫受試者回答的是兩段音訊是否 `"same or different"`；`refs/2511.13936/mds/manocha2020differentiable.md:234-238` 訓練目標是預測 human judgment 的 binary classification；真正的 `"A/B preference tests"` 出現在 `refs/2511.13936/mds/manocha2020differentiable.md:596-599`，但那是 downstream denoising evaluation，不是 core training signal。
- `為什麼這是一個 FP / FN`: 這是 FP。全文支持的是 perceptual discriminability / JND learning，不是「兩段音訊誰更好」的 preference learning；模型把 similarity judgment 誤升格成 preference judgment。
- `這是 clean model error，還是 borderline ambiguity`: `clean model error`。
- `如果要寫詳解，最核心的一句話是什麼`: `"same or different"` 的 JND 標註不是 ranking/preference。

### 4.2 `wu2023interval`

- `paper_key`: `wu2023interval`
- `title`: From Interval to Ordinal: A HMM based Approach for Emotion Label Conversion
- `abstract`: Ordinal labels along affect dimensions are garnering increasing interest in computation paralinguistics. However, they are rarely obtained directly from raters, and instead typically obtained by conversion from interval labels. Current approaches to such conversion map interval labels to either absolute ordinal labels (AOL) (e.g., low and high), or to relative ordinal labels (ROL) (e.g., one has higher arousal than the other), but never take both into account. This paper presents a novel approach to map time-continuous interval labels to time-continuous ordinal labels. It simultaneously considers both inter-rater ambiguity about where AOLs sit on the interval label scale and the consistency amongst different raters in terms of ROLs. We validate the proposed approach by comparing the converted ordinal labels to original interval labels and the categorical labels for the same speech using the publicly available MSP-Podcast and MSP-Conversation corpora.
- `gold label`: `True`
- `predicted final verdict`: `exclude (senior:2)` after Stage 2; Stage 1 本來是 `maybe`
- `是哪一層出錯`: `Stage 2 closure` + `preference-signal under-detection`
- `模型當時的主要判讀理由`: 模型認為它只是 label conversion，沒有 ranking / comparative preference / RL loop，所以直接排除。
- `全文 evidence`: `refs/2511.13936/mds/wu2023interval.md:13-24` 明說 paper 處理的是 `relative ordinal labels (ROL)`，例子就是 `"one has higher arousal than the other"`，而且資料來自同一批 speech；`refs/2511.13936/mds/wu2023interval.md:54-56` 與 `:73-82` 明寫 `ROLs encode pairwise comparisons`，且 HMM 的 transition probabilities 直接整合 relative ordinal information；`refs/2511.13936/mds/wu2023interval.md:122-124` 與 `:202-204` 又明確說 HMM 是 trained / decoded 的，不只是靜態標註整理。
- `為什麼這是一個 FP / FN`: 這是 FN。模型把這篇讀成沒有 preference signal，但全文其實把 pairwise-relative ordinal information 放在方法核心；真正難點是它學的是 label-conversion model，不是直接學 audio ranking model。
- `這是 clean model error，還是 borderline ambiguity`: `borderline ambiguity`。fulltext 的確比較像 ordinal-label learning 而不是典型 preference-ranker，但說它「完全沒有 pairwise preference signal」就過頭了。
- `如果要寫詳解，最核心的一句話是什麼`: 這篇不是沒有 preference signal，而是把 pairwise ordinal signal 用在 speech label conversion。

### 4.3 `chumbalov2020scalable`

- `paper_key`: `chumbalov2020scalable`
- `title`: Scalable and efficient comparison-based search without features
- `abstract`: We consider the problem of finding a target object t using pairwise comparisons, by asking an oracle questions of the form “Which object from the pair (i, j) is more similar to t?”. Objects live in a space of latent features, from which the oracle generates noisy answers. First, we consider the non-blind setting where these features are accessible. We propose a new Bayesian comparison-based search algorithm with noisy answers; it has low computational complexity yet is efficient in the number of queries. We provide theoretical guarantees, deriving the form of the optimal query and proving almost sure convergence to the target t. Second, we consider the blind setting, where the object features are hidden from the search algorithm. In this setting, we combine our search method and a new distributional triplet embedding algorithm into one scalable learning framework called LEARN2SEARCH. We show that the query complexity of our approach on two real-world datasets is on par with the non-blind setting, which is not achievable using any of the current state-of-the-art embedding methods. Finally, we demonstrate the efficacy of our framework by conducting an experiment with users searching for movie actors.
- `gold label`: `True`
- `predicted final verdict`: `exclude (junior:2,2)` at Stage 1; combined stayed exclude
- `是哪一層出錯`: `Stage 1 early exclude` + `audio-domain miss`
- `模型當時的主要判讀理由`: Stage 1 直接把它判成非-audio generic comparison-based search。
- `全文 evidence`: `refs/2511.13936/mds/chumbalov2020scalable.md:54-55` 只把 `music` 列成 generic data type example；真正的 audio anchoring 出現在 `refs/2511.13936/mds/chumbalov2020scalable.md:707-710` 與 `:1292-1295`，作者在 blind-setting evaluation 裡明確用了 `music dataset` / `Music artists` triplet comparisons；但同時 `refs/2511.13936/mds/chumbalov2020scalable.md:1308-1314` 又顯示另一個重點實驗其實是 movie actors face search。
- `為什麼這是一個 FP / FN`: 這是 FN，但不是很乾淨。全文不是完全無 audio；然而 audio 只是 generic triplet-search framework 的一個 application slice，不是 paper 的唯一或主要 domain。
- `這是 clean model error，還是 borderline ambiguity`: `borderline ambiguity`。
- `如果要寫詳解，最核心的一句話是什麼`: 這篇不是完全非-audio，但 audio 只佔一個側面，所以它是 domain-boundary 最模糊的一類。

### 4.4 `jayawardena2020ordinal`

- `paper_key`: `jayawardena2020ordinal`
- `title`: How Ordinal Are Your Data?
- `abstract`: Many affective computing datasets are annotated using ordinal scales, as are many other forms of ground truth involving subjectivity, e.g. depression severity. When investigating these datasets, the speech processing community has chosen classification problems in some cases, and regression in others, while ordinal regression may also arguably be the correct approach for some. However, there is currently essentially no guidance on selecting a suitable machine learning and evaluation method. To investigate this problem, this paper proposes a neural network-based framework which can transition between different modelling methods with the help of a novel multi-term loss function. Experiments on synthetic datasets show that the proposed framework is empirically well-behaved and able to correctly identify classification-like, ordinal regression-like and regression-like properties within multidimensional datasets. Application of the proposed framework to six real datasets widely used in affective computing and related fields suggests that more focus should be placed on ordinal regression instead of classifying or predicting, which are the common practices to date.
- `gold label`: `True`
- `predicted final verdict`: `exclude (senior:2)` at Stage 1; combined stayed exclude
- `是哪一層出錯`: `Stage 1 early exclude` + `pairwise/ranking/ordinal under-detection`
- `模型當時的主要判讀理由`: 模型從 title/abstract 沒抓到 audio 與 preference-learning，於是當成 generic ordinal-data methodology paper。
- `全文 evidence`: `refs/2511.13936/mds/jayawardena2020ordinal.md:38-40` 與 `:57-58` 明寫語境是 `speech processing` / `speech-based affective computing`；`refs/2511.13936/mds/jayawardena2020ordinal.md:117-123` 直接引入 `PrefNet`；`refs/2511.13936/mds/jayawardena2020ordinal.md:200-212` 更把 `pairwise preference loss` 寫成 ordinal loss term。
- `為什麼這是一個 FP / FN`: 這是 FN。雖然 paper 比較偏「怎麼判斷 classification / ordinal regression / regression 的邊界」，不是純 preference-learning application，但全文不是模型說的那種「完全沒有 audio 或 preference-learning」。
- `這是 clean model error，還是 borderline ambiguity`: `borderline ambiguity`。paper 的核心確實偏 meta-learning-choice，但 speech domain 與 pairwise preference loss 都是真訊號。
- `如果要寫詳解，最核心的一句話是什麼`: title 很 generic，但正文其實明確站在 speech affective computing，且用 pairwise preference loss 做 ordinal term。

### 4.5 `parthasarathy2018preference`

- `paper_key`: `parthasarathy2018preference`
- `title`: Preference-Learning with Qualitative Agreement for Sentence Level Emotional Annotations
- `abstract`: The perceptual evaluation of emotional attributes is noisy due to inconsistencies between annotators. The low inter-evaluator agreement arises due to the complex nature of emotions. Conventional approaches average scores provided by multiple annotators. While this approach reduces the influence of dissident annotations, previous studies have showed the value of considering individual evaluations to better capture the underlying ground-truth. One of these approaches is the qualitative agreement (QA) method, which provides an alternative framework that captures the inherent trends amongst the annotators. While previous studies have focused on using the QA method for time-continuous annotations from a fixed number of annotators, most emotional databases are annotated with attributes at the sentence-level (e.g., one global score per sentence). This study proposes a novel formulation based on the QA framework to estimate reliable sentence-level annotations for preference-learning. The proposed relative labels between pairs of sentences capture consistent trends across evaluators. The experimental evaluation shows that preference-learning methods to rank-order emotional attributes trained with the proposed QA-based labels achieve significantly better performance than the same algorithms trained with relative scores obtained by averaging absolute scores across annotators. These results show the benefits of QA-based labels for preference-learning using sentence-level annotations.
- `gold label`: `True`
- `predicted final verdict`: `exclude (junior:2,2)` at Stage 1; combined stayed exclude
- `是哪一層出錯`: `Stage 1 early exclude` + `speech/audio domain miss`
- `模型當時的主要判讀理由`: 模型承認它有 preference-learning，但因 title/abstract 沒看成 audio，就直接排除。
- `全文 evidence`: `refs/2511.13936/mds/parthasarathy2018preference.md:21-33` abstract 結尾就有 `Index Terms: speech emotion recognition, preference-learning`；`refs/2511.13936/mds/parthasarathy2018preference.md:35-39` 開頭更直接說 emotion is conveyed in `speech`；`refs/2511.13936/mds/parthasarathy2018preference.md:89-96` 與 `:437-446` 清楚寫 pairwise comparisons create relative labels，並用 preference-learning 去 rank-order emotional attributes。
- `為什麼這是一個 FP / FN`: 這是 FN。audio-domain evidence 其實在全文前幾行就很明顯，Stage 1 把它讀成非-audio 是直接漏讀。
- `這是 clean model error，還是 borderline ambiguity`: `clean model error`。
- `如果要寫詳解，最核心的一句話是什麼`: 這篇連 index terms 都寫了 `speech emotion recognition, preference-learning`，卻仍被 Stage 1 當成非-audio。

### 4.6 `huang2025step`

- `paper_key`: `huang2025step`
- `title`: Step-Audio: Unified Understanding and Generation in Intelligent Speech Interaction
- `abstract`: Real-time speech interaction, serving as a fundamental interface for human-machine collaboration, holds immense potential. However, current open-source models face limitations such as high costs in voice data collection, weakness in dynamic control, and limited intelligence. To address these challenges, this paper introduces Step-Audio, the first production-ready open-source solution. Key contributions include: 1) a 130B-parameter unified speech-text multi-modal model that achieves unified understanding and generation, with the Step-Audio-Chat version open-sourced; 2) a generative speech data engine that establishes an affordable voice cloning framework and produces the open-sourced lightweight Step-Audio-TTS-3B model through distillation; 3) an instruction-driven fine control system enabling dynamic adjustments across dialects, emotions, singing, and RAP; 4) an enhanced cognitive architecture augmented with tool calling and role-playing abilities to manage complex tasks effectively. Based on our new StepEval-Audio-360 evaluation benchmark, Step-Audio achieves state-of-the-art performance in human evaluations, especially in terms of instruction following. On open-source benchmarks like LLaMA Question, shows 9.3% average performance improvement, demonstrating our commitment to advancing the development of open-source multi-modal language technologies. Our code and models are available at https://github.com/stepfun-ai/Step-Audio.
- `gold label`: `True`
- `predicted final verdict`: `exclude (senior:2)` at Stage 1; combined stayed exclude
- `是哪一層出錯`: `Stage 1 early exclude` + `preference-vs-evaluation confusion`
- `模型當時的主要判讀理由`: 模型把 paper 看成 audio model with human evaluation，但沒有 preference-learning core，也沒有 RL loop。
- `全文 evidence`: `refs/2511.13936/mds/huang2025step.md:557-588` 明寫 `We applied Reinforcement Learning from Human Feedback (RLHF) for the AQTA task`，而 Figure 6 說 reward model 之後用 `PPO` 訓練 Step-Audio-Chat；`refs/2511.13936/mds/huang2025step.md:643-666` 詳列 `AQTA Preference Data Construction`，是對 real audio prompts 取四個 responses，再由 human annotators 打 1-5 分數，組 chosen/rejected pairs，然後用 Bradley-Terry loss 訓練 reward model；`refs/2511.13936/mds/huang2025step.md:675-689` 與 `:1155-1158` 則明說 reward model 之後還接 PPO / RLHF 做 speech LLM training。
- `為什麼這是一個 FP / FN`: 這是 FN。這篇不是 preference-for-evaluation only；human preference pairs 明確進 reward model training，之後又進 PPO / RLHF。
- `這是 clean model error，還是 borderline ambiguity`: `clean model error`。
- `如果要寫詳解，最核心的一句話是什麼`: 這篇把 audio preference pairs 用在 reward model 和 PPO，不是只做 human eval。

## 5. Error Taxonomy

### 5.1 `2409`

- `publication-form overreach`: 代表 cases 是 `goossens2023extracting`, `halioui2018bioinformatic`, `neuberger2023beyond`, `qian2020approach`, `vda_extracting_declarative_process`，以及一批被 Stage 2 收回去的 preprint-like cases。典型錯法是把 `journal pre-proof`, `LNCS conference proceedings`, 或 local metadata 缺口，一律強行解釋成 disqualifying negative。
- `target-boundary confusion`: 代表 cases 是 `bellan2022extracting`, `bellan_gpt3_2022`, `robeer2016`。典型錯法是把 entity/relation extraction、conceptual modeling、requirements modeling 這些「接近 process modeling」的工作保留為 positive，而沒有要求 target object 真的是 canonical process/decision model。
- `source-target inversion`: 代表 case 是 `azevedo2018bpmn`。典型錯法是先抓到 process-to-text / synchronization 面向，就忽略 paper 同時包含 text-to-model branch。
- `auxiliary/non-target family confusion`: `bellan2021process`, `busch2023just`, `lopez2021challenges`, `maqbool2019comprehensive`, `riefer2016mining`, `van2018challenges` 等，都落在「與 process extraction 有關，但不是 original canonical target paper」這一群。
- `stage1 vs stage2 handoff failure`: `2409` 的 pattern 很明確。Stage 1 幾乎把邊界案都送成 `maybe`，真正的傷害主要在 Stage 2 closure：有些該收掉的 target-boundary FP 沒收乾淨，有些該保留的 gold include 又被 publication-form 收太緊。

### 5.2 `2511`

- `preference-vs-evaluation confusion`: `manocha2020differentiable` 是把 perceptual discrimination 誤當 preference learning；`huang2025step` 則是相反方向，把真正進 reward model / PPO 的 preference data 誤當 evaluation-only。
- `pairwise/ranking/ordinal under-detection`: `wu2023interval`、`jayawardena2020ordinal`。典型錯法是看到 ordinal / label-conversion / loss-selection，就忘了 paper 其實明確使用 pairwise or relative ordinal signal。
- `speech/audio domain miss`: `parthasarathy2018preference` 是最乾淨的例子；`jayawardena2020ordinal` 也有這個問題；`dong2020pyramid` 與 `chumbalov2020scalable` 則比較接近 title/abstract 不明顯導致的 gating miss。
- `multimodal-audio misread`: `huang2025step` 是 speech-text multimodal，但音訊仍是 AQTA core task；把 multimodal 誤讀成非-audio，會直接漏掉這類 paper。
- `survey/review false trigger`: 在這兩個 QA runs 的 misclassified core set 中，不是主要家族；至少在這次深讀的 6 個 `2511` cases 裡，沒有看到 survey/review exclusion 被誤觸發成主因。
- `stage1 gating error`: `2511` 的大宗傷害在 Stage 1。`chumbalov2020scalable`, `dong2020pyramid`, `huang2025step`, `jayawardena2020ordinal`, `parthasarathy2018preference` 都是在還沒進 fulltext closure 前就被擋掉。

## 6. Best Detailed-Explanation Candidates

### 6.1 `2409`

- `goossens2023extracting`: 最適合拿來示範 `publication-form overreach`。它的方法、資料、評估都很乾淨，唯一被打掉的理由是把 accepted journal pre-proof 誤當成不可納入的 publication form。
- `vda_extracting_declarative_process`: 最適合拿來示範 `conference proceedings 被誤讀成 book chapter`。`CAiSE 2019, LNCS` 的線索非常明確，全文又是 textbook-level 的 target-fit + evaluation。

### 6.2 `2511`

- `manocha2020differentiable`: 最適合拿來示範 `preference boundary 過寬`。它表面上有人類 pairwise judgments，但內容其實是 same/different JND learning，不是 ranking / preferred-output learning。
- `jayawardena2020ordinal`: 最適合拿來示範 `title/abstract 過於 generic 導致 Stage 1 漏讀`。全文明明站在 speech affective computing，也用 pairwise preference loss，但 Stage 1 沒抓到。

## 7. Short Final Take

- `2409` 的錯誤主軸不是「QA 整體太保守」這麼籠統，而是兩條更具體的 fault lines：一條是 publication-form closure 過頭，另一條是 target object boundary 太鬆或太亂。
- `2511` 的錯誤主軸則更集中在 signal recognition：模型常常沒把 `speech = audio`、`pairwise/ordinal = preference signal`、以及 `RLHF reward-model training = learning component` 正確讀出來。
- 最可修的錯誤是 `goossens2023extracting`, `vda_extracting_declarative_process`, `parthasarathy2018preference`, `huang2025step` 這種全文證據非常直接、而模型卻判反的 cases。
- 最難的邊界是 `qian2020approach`, `wu2023interval`, `chumbalov2020scalable` 這些 publication metadata 或 task family 本身就有真實 ambiguity 的 cases。
