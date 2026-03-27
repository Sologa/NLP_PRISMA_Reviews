# All-16 Cutoff Semantic Audit

- Generated at: `2026-03-26T11:32:24.053922+00:00`
- Output dir: `screening/results/cutoff_semantic_audit_all16_2026-03-26`
- Runtime basis: current `scripts/screening/cutoff_time_filter.py` + active `cutoff_jsons/<paper_id>.json`
- PDF basis: `pdftotext -layout` on `refs/<paper_id>/<paper_id>.pdf`

## Availability Matrix

| Paper | cutoff_json | metadata | annotated_gold | pdf |
| --- | --- | --- | --- | --- |
| `2303.13365` | yes | no | no | yes |
| `2306.12834` | yes | yes | no | yes |
| `2307.05527` | yes | yes | yes | yes |
| `2310.07264` | yes | yes | no | yes |
| `2312.05172` | yes | yes | no | yes |
| `2401.09244` | yes | yes | no | yes |
| `2405.15604` | yes | yes | no | yes |
| `2407.17844` | yes | no | no | yes |
| `2409.13738` | yes | yes | yes | yes |
| `2503.04799` | yes | yes | no | yes |
| `2507.07741` | yes | yes | no | yes |
| `2507.18910` | yes | yes | no | yes |
| `2509.11446` | yes | yes | yes | yes |
| `2510.01145` | yes | yes | no | yes |
| `2511.13936` | yes | yes | yes | yes |
| `2601.19926` | yes | yes | yes | yes |

## Gold-Backed Cutoff Audit

| Paper | Total | Gold+ | Gold- | TP | FP | TN | FN | Gold+ cutoffed | Correct via cutoff exclude | Correct via cutoff pass | High risk |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `2307.05527` | 222 | 171 | 51 | 155 | 38 | 13 | 16 | 16 | 13 | 155 | yes |
| `2409.13738` | 84 | 21 | 63 | 21 | 48 | 15 | 0 | 0 | 15 | 21 | no |
| `2509.11446` | 164 | 74 | 90 | 74 | 90 | 0 | 0 | 0 | 0 | 74 | no |
| `2511.13936` | 88 | 30 | 58 | 30 | 47 | 11 | 0 | 0 | 11 | 30 | no |
| `2601.19926` | 360 | 336 | 24 | 336 | 24 | 0 | 0 | 0 | 0 | 336 | no |

## Semantic Risk Verdicts

| Paper | Primary verdict | Gold high-risk | parser | derivation | retrieval-vs-screening | scope mismatch | manual review |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `2303.13365` | `no_apparent_issue` | no | no | no | no | no | no |
| `2306.12834` | `possible_retrieval_vs_screening_confusion` | no | no | no | yes | yes | no |
| `2307.05527` | `possible_cutoff_derivation_issue` | yes | no | yes | no | yes | no |
| `2310.07264` | `possible_cutoff_derivation_issue` | no | no | yes | no | yes | no |
| `2312.05172` | `no_apparent_issue` | no | no | no | no | no | no |
| `2401.09244` | `possible_retrieval_vs_screening_confusion` | no | no | no | yes | yes | no |
| `2405.15604` | `no_apparent_issue` | no | no | no | no | no | no |
| `2407.17844` | `needs_manual_review` | no | no | no | no | no | yes |
| `2409.13738` | `possible_retrieval_vs_screening_confusion` | no | no | no | yes | yes | no |
| `2503.04799` | `no_apparent_issue` | no | no | no | no | no | no |
| `2507.07741` | `no_apparent_issue` | no | no | no | no | no | no |
| `2507.18910` | `no_apparent_issue` | no | no | no | no | no | no |
| `2509.11446` | `possible_cutoff_derivation_issue` | no | no | yes | no | yes | no |
| `2510.01145` | `no_apparent_issue` | no | no | no | no | no | no |
| `2511.13936` | `possible_cutoff_derivation_issue` | no | no | yes | no | yes | no |
| `2601.19926` | `no_apparent_issue` | no | no | no | no | no | no |

## Main Answers

- `2511_like_candidate_papers`: `['2306.12834', '2401.09244', '2409.13738']`
- `parser_only_issue_papers`: `[]`
- `cutoff_derivation_issue_papers`: `['2307.05527', '2310.07264', '2509.11446', '2511.13936']`
- `retrieval_vs_screening_confusion_papers`: `['2306.12834', '2401.09244', '2409.13738']`
- `needs_manual_review_papers`: `['2407.17844']`
- `worth_pushing_to_github`: `['2306.12834', '2307.05527', '2310.07264', '2401.09244', '2407.17844', '2409.13738', '2509.11446', '2511.13936']`
- `not_worth_pushing_now`: `['2303.13365', '2312.05172', '2405.15604', '2503.04799', '2507.07741', '2507.18910', '2510.01145', '2601.19926']`

## Comparison vs `cutoff_only_audit_2026-03-26`

### 2307.05527
- `cutoff_status_counts` old=`{"before_start": 29, "passed": 192, "unparseable_published_date": 1}` new=`{"before_start": 29, "passed": 193}`
- `confusion_matrix` old=`{"tp": 155, "fp": 37, "tn": 14, "fn": 16}` new=`{"tp": 155, "fp": 38, "tn": 13, "fn": 16}`

### 2409.13738
- `cutoff_status_counts` old=`{"after_end": 14, "passed": 65, "unparseable_published_date": 5}` new=`{"after_end": 15, "passed": 69}`
- `confusion_matrix` old=`{"tp": 21, "fp": 44, "tn": 19, "fn": 0}` new=`{"tp": 21, "fp": 48, "tn": 15, "fn": 0}`

### 2511.13936
- `cutoff_status_counts` old=`{"before_start": 32, "passed": 51, "unparseable_published_date": 5}` new=`{"before_start": 11, "passed": 77}`
- `gold_positive_cutoffed` old=`9` new=`0`
- `confusion_matrix` old=`{"tp": 21, "fp": 30, "tn": 28, "fn": 9}` new=`{"tp": 30, "fp": 47, "tn": 11, "fn": 0}`

### 2601.19926
- `cutoff_status_counts` old=`{"passed": 354, "unparseable_published_date": 6}` new=`{"passed": 360}`
- `gold_positive_cutoffed` old=`3` new=`0`
- `confusion_matrix` old=`{"tp": 333, "fp": 21, "tn": 3, "fn": 3}` new=`{"tp": 336, "fp": 24, "tn": 0, "fn": 0}`


## Per-Paper Notes

### 2303.13365
- Primary verdict: `no_apparent_issue`
- PDF p.1: "future research directions. To achieve this, we conducted a systematic literature review to outline the current state-of-the-art of NLP and ML techniques in RF by selecting 257 papers from common used libraries. The search result is filtered by defining inclusion and exclusion criteria and 47 relevant studies between 2012 and 2022 are selected. We found that heuristic NLP approaches are the most common NLP techniques used for automatic RF, primary operating on structured and semi-structured data. This study also revealed that Deep"
- PDF p.4: "articles are investigated by third author, who is an expert in NLP domain and was not involved the distribution of the resulting papers in each year. by the search process by considering the inclusion As can be seen in this figure, in 2021 the domain and exclusion criteria. A satisfactory result is pre- gained more interest and highest number of publi- sented from pilot study, which proves the suitabil- cation were published. Additionally, Figure 2 indi-"
- PDF p.8: "7 Future Directions REFERENCES In the following we discuss directions to complete Datasets of 162 requirements and the corresponding the current actions and further future work on RF. rcm-extractor output. https://github.com/"

### 2306.12834
- Primary verdict: `possible_retrieval_vs_screening_confusion`
- Core rationale: `Current cutoff 主要來自 Stage 1 retrieval/search period，PDF 未顯示等價的 Stage 2 eligibility time rule。`
- PDF p.6: "also have been focused on analysing and identifying clinical narratives through ML or DL methods. B) Exclusion Criteria: Research works that were published as a preprint, with preliminary work or without peer review, were excluded. Editorials and review papers were also on the exclusion list. After the initial screening, the"
- PDF p.6: "7 from BioMed Central, 8 from Wiley Online Library. Of these, 119 papers were excluded based on our exclusion criteria. An additional 101 papers were identified from the reference lists of retrieved articles. Four of these titles were duplicates and thus excluded, 1 article was not available for review, and ten did not match our criteria. The remaining 127 papers were retrieved for full-text"
- PDF p.18: "aid patients with severe illnesses in articulating what they value most and wish to occur with their medical treatment. Medical professionals can use this in- formation to create a care plan based on the patient’s values and preferences. In light of the context, Lee et al. [66] developed an automated method for identifying goals of goal-of-care discussion using NLP approaches. In brief, a"

### 2307.05527
- Primary verdict: `possible_cutoff_derivation_issue`
- Core rationale: `PDF/criteria 使用 submitted/published 語義，但 current cutoff 只投到 published_date。`
- Gold-positive cutoffed: `16`
- PDF p.3: "does not include extended abstracts or book chapters, nor any other 1 Initially, the search was targeted around “deep generative audio models”, but it became form of writing outside of full research papers. The main text and clear quite quickly that the “deep” part of the term was too narrow and not widely included appendices were analyzed, but no supplemental materials adopted until recently (this search only resulted in 242 articles)."
- PDF p.3: "(in Section 3.1.1), a keyword search was iteratively performed until positive broader impacts beyond their scientific scope. the desired pool of research was included by the cast net. After many iterations of specific keywords such as “music”, “speech”, 2.3 Research Questions and “sound”, the author eventually expanded the search to sim-"
- PDF p.11: "cross-domain singing voice conversion. arXiv preprint arXiv:2008.02830 (2020). [50] Aditya Ramesh, Prafulla Dhariwal, Alex Nichol, Casey Chu, and Mark Chen. 2022. Hierarchical text-conditional image generation with clip latents. arXiv A REFERENCES FOR WORKS INCLUDED IN preprint arXiv:2204.06125 (2022). [51] Melanie R Roberts. 2009. Realizing societal benefit from academic research: SYSTEMATIC LITERATURE REVIEW"

### 2310.07264
- Primary verdict: `possible_cutoff_derivation_issue`
- Core rationale: `Active time_policy 依賴 operational fallback，而不是 paper-literal 的明確時間條款。`
- PDF p.1: "techniques for this purpose. We will systematically review the literature on the automatic clas- sification of dysarthria severity levels. Sources of information will include electronic databases and grey literature. Selection criteria will be established based on relevance to the research questions. Data extraction will include methodologies used, the type of features extracted for classification, and AI techniques employed. The findings of this systematic review will"
- PDF p.11: "recognition and evaluated on the TORGO dataset, which This publication was made by International Research contains diverse severity samples. Still, there is no spe- Collaboration Co-Fund (IRCC) Cycle 06 (2023-2024) cific classification model based on these features. No. IRCC-2023-223 from the Qatar National Research Microprosody Analysis: Investigate features that Fund (a member of the Qatar Foundation). The state- capture fine-grained temporal variations within short ments made herein are solely the responsibility of the"
- PDF p.12: "[13] Y.-J. Park, J.-M. Lee, Effect of acupuncture intervention and [35] L. Xu, J. Liss, V. Berisha, Dysarthria detection based on a manipulation types on poststroke dysarthria: a systematic re- deep learning model with a clinically-interpretable layer, JASA view and meta-analysis, Evidence-Based Complementary and Express Letters 3 (2023) 015201. Alternative Medicine 2020 (2020). [36] R. D. Kent, G. Weismer, J. F. Kent, H. K. Vorperian, J. R. Duffy, [14] A. K. Shanmugam, R. Marimuthu, A critical analysis and Acoustic studies of dysarthric speech: Methods, progress, and"

### 2312.05172
- Primary verdict: `no_apparent_issue`
- PDF p.3: "works providing a full-text article; and iv) journal and conference publications. Unpublished works such as dissertation studies, theses and technical reports were excluded from this review. Due to the large number of works, studies with few citations (less than 10 citations in total) that were published prior to 2017 were also excluded from this review. All articles were collected by searching relevant papers in the following databases: i) Google Scholar; ii) Scopus; iii) ACM Digital Library; iv) Springer Digital Library; v) IEEE Explore Digital Library; and vi) ArXiv. In addition, the"
- PDF p.3: "way. We initially searched using all the specified criteria for the years 2000 to 2022, limiting our search to the first 300 records in each database to maintain a manageable result pool. We then repeated this process for the years 2023 to 2025, limiting our search to 30 records per database, as no relevant results were found beyond this threshold. A total of 1,633 records were collected via digital databases (Google Scholar n = 330, Scopus n = 330, ACM Digital Library n = 330, Springer Digital Library n = 330, IEEE Explore Digital Library n = 129, ArXiv n = 120) and hand"
- PDF p.3: "All articles were collected by searching relevant papers in the following databases: i) Google Scholar; ii) Scopus; iii) ACM Digital Library; iv) Springer Digital Library; v) IEEE Explore Digital Library; and vi) ArXiv. In addition, the reference lists of the extracted papers were manually searched for additional relevant papers. The following search query was used to identify relevant papers: (“sentence summarization” OR “sentence compression” OR “sentence splitting” OR “split and rephrase”). We arrived at this query by starting from (‘sentence compression”"

### 2401.09244
- Primary verdict: `possible_retrieval_vs_screening_confusion`
- Core rationale: `Current cutoff 主要來自 Stage 1 retrieval/search period，PDF 未顯示等價的 Stage 2 eligibility time rule。`
- PDF p.4: "Database Records Total Identified records Full-text records Article included in the (n=643) Total Identified records assessed for screening assessed for eligibility systematic review"
- PDF p.4: "“between language”, “cross linguistic”, “transfer”, “code switch”, “zero shot”, “few shot”. Search Process. In addition to studies matching the 99 keyword pairs above, we also identify and include 5 additional studies cited in relevant surveys. This search was conducted on July 29th, 2023. Eligibility Criteria. Following removal of duplicates and irrelevant papers, the remainder 455 publications were checked against the inclusion / exclusion criteria in Table 1."
- PDF p.1: "we shed light on the current challenges and future research opportunities in this field. Furthermore, we have made our survey resources available online, including two comprehensive tables that provide accessible references to the multilingual datasets and CLTL methods used in the reviewed literature. CCS Concepts: • Computing methodologies → Natural language processing; Machine learning; • Human- centered computing → Collaborative and social computing."

### 2405.15604
- Primary verdict: `no_apparent_issue`
- PDF p.5: "2.3 Manual Assessment Eligibility criteria. We manually assess the titles and abstracts of 279 works from 2017 to 2023 to judge their relevance regarding text generation. We remove papers that are too specific for the scope of this review (e.g., multimodality) and eliminate works that employ studies to another field of study (e.g., medicine). We release a table of our relevance"
- PDF p.4: "Select top 5 papers by infl. 1127 31 Exclude irrelevant papers citations per query and year Exclude papers until 2021 58"
- PDF p.35: "In Proceedings of the 61st Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers). Association for Computational Linguistics. https://doi.org/10.18653/v1/2023.acl-long.179 [239] Renjie Zheng, Mingbo Ma, and Liang Huang. 2018. Multi-Reference Training with Pseudo-References for Neural Translation and Text Generation. In Proc. of EMNLP. Association for Computational Linguistics, Brussels, Belgium, 3188–3197. https://doi.org/10.18653/v1/D18-1357 [240] Wanjun Zhong, Duyu Tang, Zenan Xu, et al. 2020. Neural Deepfake Detection with Factual Structure of Text. In Proc. of EMNLP. Association for"

### 2407.17844
- Primary verdict: `needs_manual_review`
- Core rationale: `Abstract/summary 與 methodology 都提到 2020–2024 範圍，但其是 review scope 還是 hard screening gate 仍偏灰區。`
- PDF p.3: "open-source resources for PD classification, up to March 2024. The rest of the paper is structured as follows. In Section 2, the eligibility criteria, exclusion criteria, and search procedure are described. In Section 3, E2E learning approaches based on applied Deep Neural Network (DNN) architectures, such as Convolutional Neural Networks (CNNs), Long Short-Term Memory networks (LSTMs), and Transformers, are"
- PDF p.4: "2.1. Search Procedure and Identification Criteria The search was performed in April 2024, using the following databases: Google Scholar, SpringerLink, and IEEE Xplore. The year filter was 2020 onwards. The search comprised the following search terms: “speech processing Parkinson”, “speech recognition"
- PDF p.17: "Table A1. Publicly available speech-based datasets for PD research. # and ↑ stand for number of (speakers) and ascending order of publication, respectively. Data Dataset (Year) ↑ Source & References # Speakers Transcripts Disease Severity Language Overall Speech Time Quality Speech Task(s)"

### 2409.13738
- Primary verdict: `possible_retrieval_vs_screening_confusion`
- Core rationale: `PDF 表示 search/retrieval 沒有 publication-year hard restriction，但 active cutoff 仍把 search-side 時間線投成全域 eligibility。`
- Gold-positive cutoffed: `0`
- PDF p.3: "The rest of the paper is structured as follows. Section 2 discusses other review papers on automated process extraction. Section 3 outlines our systematic review approach, including source databases, keywords, exclusion and inclusion criteria, and classification criteria. Sections 4-7 present our data synthesis results, including answers to the research questions. Section 8 summarises important observations from"
- PDF p.7: "Following title and abstract screening, 70 articles were retained for full-text screening. In the end, 20 articles were found to fully meet our inclusion/exclusion criteria. Our search queries were executed in June 2023 and the found papers span a time period 7"
- PDF p.6: "Process Extraction “Process Extraction” OR Process Management “Process Management” OR Business Process Elicita- “Business Process Elicitation” OR tion Decision Model and Nota- “Decision Model and Notation” OR"

### 2503.04799
- Primary verdict: `no_apparent_issue`
- PDF p.8: "state-of-the-art advancements in direct Speech-to-Speech Translation (S2ST) enabled by machine learning techniques. It includes extensive literature search, clearly ar- ticulated inclusion and exclusion criteria, and rigorous assessment protocols ensur- ing proper integration of relevant research and high-quality research for an effective overview. Relevant articles for this analysis is collected through in-depth searching on"
- PDF p.44: "[38] Jaffer Khan, Alamelu Raman, Nithya Sambamoorthy, and Kanniga Prashanth. Research Methodology (Methods, Approaches And Techniques). 09 2023. [39] Robert Streijl and David Hands. Mean opinion score (mos) revisited: methods"
- PDF p.24: "of each model to build stronger features in S2ST systems by extracting individ- ual features, normalizing them, and combining them through weighted averaging or concatenation. By utilizing these complementary strengths, fused features enhance translation quality and improve generalization across various acoustic conditions, with the ESPnet-ST-v2 achieving significant improvements in BLEU scores. For ex-"

### 2507.07741
- Primary verdict: `no_apparent_issue`
- PDF p.2: "or dialects between sentences) and intra-sentential currently represents the mainstream in ASR tech- code-switching, where language switches happen nology. Furthermore, our analysis includes all pa- within a single sentence. The latter is most chal- pers that fit our search and inclusion criteria, which lenging for speech systems and what is typically is constrained only by the recency of the studied addressed in the surveyed literature. E2E systems; indeed, over half of the papers in our"
- PDF p.1: "banking and financial, healthcare, and retail (Grand 1.1 Code-switching View Research, 2024). Such widespread adoption of ASR highlights the need and desire for high People engage in CS in their communication for performing systems across different languages and many and varied reasons, such as a speaker’s fa-"
- PDF p.11: "language model for code-switching automatic speech recognition. In 2024 Tenth International Conference References on Communications and Electronics (ICCE), pages 387–391. Ahmed Amine Ben Abdallah, Ata Kabboudi, Amir Ka-"

### 2507.18910
- Primary verdict: `no_apparent_issue`
- PDF p.3: "Anthology, IEEE Xplore, ACM Digital Library, and • English Language: For consistency and to Google Scholar. We included documents published support thorough evaluation, only English texts from 2017 up to the end of mid 2025, covering early were included. end 3"
- PDF p.2: "loop [e.g., 35, 10]. In parallel, industry adoption Since its formal introduction in the seminal work of RAG has been swift: leading tech companies of [52] in 2020, Retrieval-Augmented Generation have integrated retrieval-augmented generators into (RAG) has witnessed rapid advancements, marked search engines, virtual assistants, and enterprise by a significant surge in research interest and question-answering applications [33, 60]. RAG now"
- PDF p.3: "on the above-listed databases, resulting in a pool of strategy, inclusion/exclusion criteria, and approach references that included journal articles, conference to data synthesis. Section 3 (Foundations papers, technical reports, and white papers."

### 2509.11446
- Primary verdict: `possible_cutoff_derivation_issue`
- Core rationale: `Active time_policy 依賴 operational fallback，而不是 paper-literal 的明確時間條款。`
- Gold-positive cutoffed: `0`
- PDF p.16: "A total of 74 primary studies on the use of LLMs for requirements en- gineering were published between 2023 and 2024. Although the search time had no boundary, no paper in the field referred to LLMs before 2023 ac- cording to our search results. Despite the fact that generative pre-trained transformers already existed already in 2018 with GPT-1, we argue that"
- PDF p.55: "i.e., Scopus. To address these problems, we piloted the search string and also integrated part of the consolidated string from Zhao et al. [27], which was focused on NLP4RE. Furthermore, we included a secondary search, system- atically analysing a wide range of relevant RE and SE venues. This approach aimed to improve coverage and capture any relevant papers that the initial"
- PDF p.12: "database coverage. The search focused on primary studies published between 2020 to 2024 in major SE/RE conferences and journals. Table 1 illustartes the selected venues for manual search. On December 18, 2024, we perfomed the secondary search using publications from these venues. After removing duplicates, screening them, and after using the same inclusion and exclusion"

### 2510.01145
- Primary verdict: `no_apparent_issue`
- PDF p.2: "circumstances make text-based digital systems inaccessible to most of the population. Africans primarily speak in their local languages, and hence they do not use English or French locally, so automatic speech recognition (ASR) emerges as a significant research field for digital inclusion. Despite this need, mainstream voice assistants like Siri, Alexa, and Google Assistant recognize no African languages. Early efforts like ALFFA [18] created Swahili, Hausa, Amharic, and Wolof,"
- PDF p.1: "Automatic Speech Recognition (ASR) has achieved remarkable global progress, yet African low-resource languages remain rigorously underrepresented, producing barriers to digital inclusion across the continent with more than +2000 languages. This systematic literature review (SLR) explores research on ASR for African languages with a focus on datasets, models and training methods, evaluation techniques, challenges, and recommends future directions. We employ the PRISMA 2020 procedures and search DBLP, ACM Digital"
- PDF p.1: "with more than +2000 languages. This systematic literature review (SLR) explores research on ASR for African languages with a focus on datasets, models and training methods, evaluation techniques, challenges, and recommends future directions. We employ the PRISMA 2020 procedures and search DBLP, ACM Digital Library, Google Scholar, Semantic Scholar, and arXiv for studies published between January 2020 and July 2025. We include studies related to ASR datasets, models or metrics for African languages, while excluding"

### 2511.13936
- Primary verdict: `possible_cutoff_derivation_issue`
- Core rationale: `Active time_policy 依賴 operational fallback，而不是 paper-literal 的明確時間條款。`
- Gold-positive cutoffed: `0`
- PDF p.7: "3.5 Final Selection and Inclusion In total, this search yielded 116 published papers, 345 arXiv papers, and 60 cited works for potential inclusion in the literature review. For each paper, the abstract, introduction, and conclusion were read to assess eligibility. A paper was deemed eligible if it satisfied the following criteria:"
- PDF p.7: "cited works from 60 to 22. During the review process no duplicates were identified. These identified papers were then read in full for final considerations of inclusion. During the full read-through, we further exclude 4 published works, 2 arXiv works, and 9 cited works. 30 total works were thus included in this survey, 10 from the venue search, 7 from arXiv, and 13 cited works. Figure 2 summarizes the literature screening and selection process following the PRISMA framework. We provide"
- PDF p.22: "[12] Paul F Christiano, Jan Leike, Tom Brown, Miljan Martic, Shane Legg, and Dario Amodei. 2017. Deep reinforcement learning from human preferences. Advances in neural information processing systems 30 (2017). [13] Yunfei Chu, Jin Xu, Qian Yang, Haojie Wei, Xipin Wei, Zhifang Guo, Yichong Leng, Yuanjun Lv, Jinzheng He, Junyang Lin, et al. 2024. Qwen2-audio"

### 2601.19926
- Primary verdict: `no_apparent_issue`
- Gold-positive cutoffed: `0`
- PDF p.2: "exclusion. This is both for transparency and to facilitate fur- tion, selection, and annotation. We set our cut-off ther studies regarding aspects other than those covered in the date for inclusion to July 31, 2025. present review."
- PDF p.1: "become the engine behind a global shift in AI, based architectures, acquire rich syntactic repre- producing fluent text across diverse languages. A sentations early during pretraining (Chang and growing body of research is examining how mod- Bergen, 2023), localize much of this information ern LMs acquire, represent, and deploy linguistic in their middle layers, and encode at least some knowledge (Rogers et al., 2020; Zhou et al., 2025; syntactic relations via specialized attention heads"
- PDF p.2: "Keyword Review-based Search Snowballing identification stage, we followed a broad-stroke (i) All references cited by reviews Reviews"


## Conclusion

- 值得 push 上 GitHub 繼續追：`['2306.12834', '2307.05527', '2310.07264', '2401.09244', '2407.17844', '2409.13738', '2509.11446', '2511.13936']`
- 暫時不值得：`['2303.13365', '2312.05172', '2405.15604', '2503.04799', '2507.07741', '2507.18910', '2510.01145', '2601.19926']`
