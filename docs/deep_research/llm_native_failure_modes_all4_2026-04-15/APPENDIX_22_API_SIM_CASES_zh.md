# 22 個非 criteria_or_gold_tension 錯例的 API-simulated 深讀附錄

日期：2026-04-18  
產物角色：companion appendix，對應主報告的 22-case deep-read 段落。

## 方法

- 只處理四篇 selected runs 裡 primary label 不是 `criteria_or_gold_tension` 的最終錯例，共 `22` 案。
- 每案先用 runner 真實 render 出來的 stage prompt 做 API simulation pass。
- simulation pass 不看 gold、不看既有 review output、不看 final verdict。
- 然後才打開 selected run artifacts、gold、必要的 local full text 做 forensic pass。
- 最終主判斷只保留 `reviewer_semantic_gap` 或 `paper_evidence_incomplete`。

## 總表

| Paper | Key | Error | API-sim provisional | Selected run verdict | Gold | Final diagnosis | One-line fix |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `2307.05527` | `kwon_effective_2019` | `FN` | `maybe` | `exclude (stage1:1)` | `include` | `reviewer_semantic_gap` | State explicitly that missing ethics language is not a valid exclusion when active criteria are generative-audio scope only. |
| `2307.05527` | `lemercier_analysing_nodate` | `FN` | `maybe` | `exclude (stage1:2)` | `include` | `reviewer_semantic_gap` | Add a reviewer note that generative speech restoration counts as an in-scope generative-audio application. |
| `2307.05527` | `louie_expressive_2021` | `FN` | `maybe` | `exclude (stage1:2)` | `include` | `reviewer_semantic_gap` | Add a reviewer note that generative music/interface evaluation papers can be in-scope without ethics framing. |
| `2307.05527` | `ming_feature_2019` | `FN` | `include` | `exclude (stage2:2)` | `include` | `reviewer_semantic_gap` | Block Stage 2 exclusions based solely on absent ethics language once full text confirms in-scope generative audio. |
| `2307.05527` | `sawata_versatile_nodate` | `FN` | `maybe` | `exclude (stage1:1)` | `include` | `reviewer_semantic_gap` | Add a reviewer note that diffusion-based speech enhancement/refinement is in-scope generative audio. |
| `2307.05527` | `shankar_non-parallel_2020` | `FN` | `include` | `exclude (stage2:1)` | `include` | `reviewer_semantic_gap` | Block Stage 2 exclusions based solely on absent ethics language for speech conversion papers. |
| `2307.05527` | `douwes2021energy` | `FN` | `exclude` | `exclude (stage1:2)` | `include` | `paper_evidence_incomplete` | Expose a short snippet on concrete generative-audio systems/use cases before Stage 1 hard exclusion. |
| `2307.05527` | `du_joint_2020` | `FN` | `maybe` | `exclude (stage1:2)` | `include` | `reviewer_semantic_gap` | State explicitly that enhancement systems with a generative vocoder producing the audio output count as generative-audio applications. |
| `2307.05527` | `huang2020ai` | `FN` | `maybe` | `exclude (stage2:2)` | `include` | `paper_evidence_incomplete` | Add an extracted modality summary so Stage 2 can resolve lyrics/music/audio scope explicitly. |
| `2307.05527` | `sekiguchi_semi-supervised_2019` | `FN` | `include` | `exclude (stage2:2)` | `include` | `reviewer_semantic_gap` | Clarify that speech-enhancement papers built around a deep generative speech prior can qualify as generative-audio applications. |
| `2307.05527` | `zhang_incorporating_2021` | `FN` | `exclude` | `exclude (stage1:1)` | `include` | `paper_evidence_incomplete` | Add a generative-component check or supporting snippet before hard-excluding speech-enhancement papers like this at Stage 1. |
| `2409.13738` | `lopez_assisted_declarative_process` | `FN` | `exclude` | `exclude (stage2:2)` | `include` | `paper_evidence_incomplete` | Route validation-ambiguous in-scope papers to a focused validation review instead of hard exclusion. |
| `2511.13936` | `chumbalov2020scalable` | `FN` | `exclude` | `exclude (stage1:1)` | `include` | `paper_evidence_incomplete` | Add a lightweight full-text rescue for generic comparison-learning abstracts with hidden domain evidence. |
| `2511.13936` | `jayawardena2020ordinal` | `FN` | `exclude` | `exclude (stage1:2)` | `include` | `paper_evidence_incomplete` | Use a maybe-rescue for audio papers with subjective ordinal labels when the abstract omits how those labels are operationalized. |
| `2511.13936` | `huang2025step` | `FN` | `exclude` | `exclude (stage1:2)` | `include` | `paper_evidence_incomplete` | Add a Stage 1 maybe-rescue for audio foundation-model papers whose abstracts mention human evaluation but may hide RLHF training. |
| `2511.13936` | `manocha2020differentiable` | `FP` | `include` | `include (stage2:5)` | `exclude` | `reviewer_semantic_gap` | Clarify in prompts that same/different JND judgments are not preference learning, and A/B tests count only when they drive training. |
| `2601.19926` | `Lovering2021PredictingIB` | `FN` | `maybe` | `exclude (stage1:2)` | `include` | `reviewer_semantic_gap` | Route probing-plus-linguistic-structure abstracts to maybe unless a non-syntax target is explicit. |
| `2601.19926` | `hu_prompting_2023` | `FN` | `maybe` | `exclude (stage1:2)` | `include` | `reviewer_semantic_gap` | When a paper measures linguistic knowledge in LMs, prefer maybe unless the abstract clearly says the target is non-syntactic. |
| `2601.19926` | `li_probing_2022` | `FN` | `maybe` | `exclude (stage1:2)` | `include` | `reviewer_semantic_gap` | Treat probing/pruning/head-level linguistic-property papers as maybe when task labels are omitted. |
| `2601.19926` | `mysiak_is_2023` | `FN` | `exclude` | `exclude (stage1:2)` | `include` | `paper_evidence_incomplete` | Expose dependency-tree or syntax language in the Stage 1 abstract snippet or metadata. |
| `2601.19926` | `wijnholds_assessing_2023` | `FN` | `maybe` | `exclude (stage1:2)` | `include` | `reviewer_semantic_gap` | If a TLM paper analyzes annotated linguistic phenomena, default to maybe unless a non-syntax focus is explicit. |
| `2601.19926` | `yanaka_assessing_2021` | `FN` | `exclude` | `exclude (stage1:1)` | `include` | `paper_evidence_incomplete` | Repair abstract sourcing or surface the syntactic phenomenon in the Stage 1 input. |

## 口語總結

- 這 22 案做完 API-simulated deep read 之後，主分布變成：`reviewer_semantic_gap = 13`、`paper_evidence_incomplete = 9`。
- 最大的改變出現在 `2601`：原本被當成 evidence-incomplete 的 6 案裡，有 4 案其實更像 reviewer 在 Stage 1 把「沒有明寫 syntax」誤當成「可以直接 exclude」。
- `2307` 的 imported-ethics cluster 很乾淨：paper 明明已經在 active criteria 內，但 reviewer 把 topic definition 的 ethics/social 色彩偷偷當成硬門檻。
- `2511` 則相反，很多錯例不是 reviewer 笨，而是 abstract 真的把 preference-learning 訊號藏太深，要到 full text 才看得出來。
- `2409` 那一案比較特別，它不是 target boundary，而是 validation evidence 寫得半明半暗，導致 Stage 2 很容易保守排掉。
