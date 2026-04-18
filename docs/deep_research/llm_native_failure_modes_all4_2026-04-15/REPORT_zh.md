# 四篇 SR 的 best-allowed-run 單 reviewer 深度研究重算報告

日期：2026-04-18  
報告路徑：`/Users/xjp/Desktop/NLP_PRISMA_Reviews/docs/deep_research/llm_native_failure_modes_all4_2026-04-15/REPORT_zh.md`  
範圍：`2307.05527`、`2409.13738`、`2511.13936`、`2601.19926`

## 0. 這次到底改了什麼

這一版最大的變化，不是把幾個數字重算而已，而是把 `2307/2601` 從歷史 one-stage fallback 正式換成 current-style 的 two-stage direct-review run。也就是說，現在四篇 paper 的主統計終於都來自 completed 的 two-stage direct-review allowed pool。

- `2307.05527`、`2601.19926`：現在都改用 `20260417_retry1_gpt54mini_xhigh_2stagedirect_2307_2601`。
- `2307` 這次還順手把 split cutoff 對齊 repo 現況，所以舊的 historical cutoff overlap 不再混進主統計。
- `2409.13738`、`2511.13936`：selected run 不變，沿用先前已確認的 two-stage direct-review best run。
- 主標籤仍然只保留三類：`reviewer_semantic_gap`、`paper_evidence_incomplete`、`criteria_or_gold_tension`。
- `pipeline_or_metadata_failure` 只保留 historical / resolved note，不再當主統計類別。

一句話總結：**主分析現在終於完全建立在四篇 current-style comparable 的 two-stage selected runs 上，而不是兩篇 two-stage 加兩篇 one-stage fallback 的混合母體。**

## 1. run 選擇規則與 selected runs

| Paper | Selected run | Model | run_family | selection_rule | fallback_used | F1 |
| --- | --- | --- | --- | --- | --- | ---: |
| `2307.05527` | `20260417_retry1_gpt54mini_xhigh_2stagedirect_2307_2601` | `gpt-5.4-mini xhigh` | `two_stage_direct_review` | `2307` 現在已有 completed 的 current-style two-stage run，所以 allowed pool 不再允許 one-stage fallback；本次就從 corrected two-stage pool 選 best completed run。 | `false` | 0.8673 |
| `2409.13738` | `20260406_full_gpt5_low_2stagedirect_rerun_2409_2511` | `gpt-5 low` | `two_stage_direct_review` | `2409` 只從 `two_stage_direct_review` pool 裡挑 best completed run。 | `false` | 0.8889 |
| `2511.13936` | `20260408_full_gpt54mini_xhigh_2stagedirect_2409_2511` | `gpt-5.4-mini xhigh` | `two_stage_direct_review` | `2511` 只從 `two_stage_direct_review` pool 裡挑 best completed run。 | `false` | 0.9123 |
| `2601.19926` | `20260417_retry1_gpt54mini_xhigh_2stagedirect_2307_2601` | `gpt-5.4-mini xhigh` | `two_stage_direct_review` | `2601` 現在已有 completed 的 current-style two-stage run，所以 allowed pool 不再允許 one-stage fallback；本次就從 corrected two-stage pool 選 best completed run。 | `false` | 0.8742 |

這裡最重要的口徑改動有兩個。

第一，現在四篇 paper 都不再需要 one-stage fallback。`2307/2601` 已經有 completed 的 two-stage rerun，所以主分析不能再拿歷史 one-stage 高分 run 當母體。

第二，`single_reviewer_runs_summary.csv` 只當索引，不當最後真值。最後選 run 還是要看實際 artifact，尤其是 `run_manifest.json`、`single_reviewer_batch_f1.json`、`single_reviewer_batch_results.json`。

## 2. best-allowed-run cross-paper 主標籤統計

- 總錯例數：`127`
- `reviewer_semantic_gap`：`13` (`10.2%`)
- `paper_evidence_incomplete`：`9` (`7.1%`)
- `criteria_or_gold_tension`：`105` (`82.7%`)

| 主標籤 | Count | Share | 直白解讀 |
| --- | ---: | ---: | --- |
| `reviewer_semantic_gap` | `13` | `10.2%` | 模型其實看得到夠多資訊，但語義邊界抓歪了。 |
| `paper_evidence_incomplete` | `9` | `7.1%` | paper 或 title/abstract 可觀察證據不夠乾淨，模型很難穩判。 |
| `criteria_or_gold_tension` | `105` | `82.7%` | 照 current criteria 判起來其實說得通，但和 gold 或 evidence-base boundary 沒有完全對齊。 |

這次重算之後，整個 cross-paper 結論變得非常集中：**真正主導殘差的不是 metadata failure，也不是大量 reviewer 純讀錯，而是 criteria / gold tension。**

特別是 `2601`，幾乎把整個 cross-paper 分布往 `criteria_or_gold_tension` 拉過去。`2307` 則顯示另一種問題：只要把 cutoff 修正好，很多舊的歷史噪音就消失，真正留下來的是 symbolic-vs-audio、enhancement-vs-generation、以及 reviewer 偷偷加上 ethics/social filter 這些比較像語義和 criteria 邊界的問題。

這裡再補一個這輪深讀之後很重要的統計口徑：**active cutoff 造成的最終錯例是 `0/127`**。四篇 selected runs 的最終 `FP/FN` inventory 去對 selected run 的 `cutoff_audit.json` 之後，沒有任何一個 active misclassified case 是 `cutoff_pass=false`。所以如果現在看到某個錯例很像「邊界和 gold 打架」，那幾乎都不是 cutoff bug，而是 criteria / gold / topic-definition 的對齊問題。

另外，這輪只針對最終錯例做 bounded candidate deep-read 之後，還看到一個更細的 pattern：`criteria_or_gold_tension` 裡有 **12 個 active FP boundary cases**（`2307: 4`、`2409: 4`、`2601: 4`）。這 12 個 case 全部都 `cutoff_pass=true`，而且更像是**目前 formal criteria 比 SR 原題目/topic_definition 更鬆**，不只是單純「gold 比 criteria 窄」。

### 2.1 22 個非 tension 錯例的 API-simulated deep read

這一輪我另外把 **22 個非 `criteria_or_gold_tension` 錯例**拆出來，改用更嚴格的 two-pass 流程重看一次。第一步不是先看 gold，也不是先看 selected run 的 reviewer output，而是先用 runner 真正會送進 API 的 prompt/render 路徑，把每個 case 重新做一遍。也就是說，simulation pass 直接沿用現行 `runtime_prompts.json`、stage-specific criteria、以及 two-stage direct-review bundle 的 prompt template；Stage 1 只能看 title/abstract/metadata，只有 selected run 真的進 Stage 2 的 case 才能再看 full text prompt。第二步才打開 selected run artifact、gold、必要的 local markdown 做 forensic pass。

這樣重跑之後，22 個 non-tension case 的分布變成：

- `reviewer_semantic_gap = 13`
- `paper_evidence_incomplete = 9`

這和前一版 `9 / 13` 的直覺剛好反過來。真正把分布翻過來的是 `2601`：那 6 個原本被我通通算成 Stage-1 observability miss 的 case，重新照 API 輸入面做題之後，只剩 2 個真的屬於 evidence 不夠，另外 4 個其實已經有足夠 cue 讓 reviewer 至少給 `maybe`。換句話說，那 4 個比較像 reviewer 在 Stage 1 把「一定要明講 syntax」抓得太死，而不是 paper 完全沒給訊號。

跨 paper 看，這 22 個 case 的聚類大概是這樣：

- `2307`：`8` 個 `reviewer_semantic_gap`、`3` 個 `paper_evidence_incomplete`。最乾淨的 cluster 是 imported ethics/social filter，這基本上是 reviewer 自己偷偷加嚴。
- `2409`：唯一的 non-tension case 仍然是 validation evidence 不完整。這案比較像 paper 自己沒有把 validation setup 說到足以穩判，而不是 reviewer 純讀錯。
- `2511`：`3` 個 evidence-incomplete case + `1` 個 semantic overread。也就是說，主問題還是 Stage 1 看不到 full-text 裡的 preference signal，但 `manocha2020differentiable` 那案確實是 reviewer 把 same/different JND supervision 過度解讀成 preference learning。
- `2601`：現在要改寫成 `4` 個 `reviewer_semantic_gap`、`2` 個 `paper_evidence_incomplete`。它不是單純「syntax 沒寫清楚」，而是 selected run 對 syntax wording 的要求比 active criteria 真正需要的還硬。

22-case 的逐案表我另外放在：

- `docs/deep_research/llm_native_failure_modes_all4_2026-04-15/APPENDIX_22_API_SIM_CASES_zh.md`

這份 appendix 每案都同時保留：

- pre-answer API-sim verdict
- selected run verdict
- gold
- final forensic diagnosis
- 一句 fix direction

## 3. category 4 的歷史註記

這一版主統計裡，`pipeline_or_metadata_failure` 不再是一個現役 failure mode。

- `2307`：corrected split-cutoff run 仍有 8 筆 cutoff-excluded rows，但它們全部都不在最終 41 個 FP/FN 裡。
- `2601`：`cutoff_excluded_count = 0`，完全沒有 cutoff-induced misclassification。
- `2409/2511`：主問題早就不是 category 4，而是 validation ambiguity、evidence completeness、或 gold boundary。

所以，category 4 在這份報告裡只保留成 historical / resolved note，不再進主表。

## 4. `2307.05527`

- Best run：`20260417_retry1_gpt54mini_xhigh_2stagedirect_2307_2601`
- Model：`gpt-5.4-mini` / reasoning `xhigh` / `two_stage_direct_review`
- Metrics：`TP=134`、`FP=4`、`TN=47`、`FN=37`、`F1=0.8673`
- 主標籤分布：`reviewer_semantic_gap=8`、`paper_evidence_incomplete=3`、`criteria_or_gold_tension=30`

這個 selected run 現在已經是 current-style 的 `two_stage_direct_review` baseline，不再是歷史 one-stage fallback。更重要的是，它用的是 corrected split-cutoff semantics，所以舊的 historical cutoff-overlap 故事已經從 active error pool 裡消失了。雖然它比舊的 one-stage fallback（`F1=0.9169`）低，現在只剩 `0.8673`，但它終於和另外三篇站在同一種 workflow 上，這也是它必須接手主統計的原因。

Stage 1 已經留下 27 個 FN，進到 Stage 2 之後又多 10 個 FN，而 4 個 FP 完全沒有被收掉。這表示 2307 的問題不是 cutoff，而是 current criteria 下的語義邊界和 reviewer 額外加嚴。

現在真正還需要 LLM 的事：對 `2307` 來說，真正還需要 LLM 的，是分清楚一篇 paper 到底是在做 audio-only generation、symbolic generation、帶 generative prior 的 enhancement、mixed interface work，還是 detector / benchmark / meta paper。難點不是關鍵字，而是判斷 generative model 到底是不是 paper 的核心應用。

Historical note：這個 selected run 已經沒有 active 的 cutoff / category-4 failure。corrected split-cutoff audit 雖然還是排掉了 8 篇背景 paper，但它們 0 篇落在最後的 41 個 FP/FN 裡，所以現在真正留下來的都是 reviewer / criteria 層面的問題。

再往下深讀四個 active FP 後，2307 的情況比單純「gold 比 current criteria 窄」更具體：它們全部都 `cutoff_pass=true`，而且 selected run 的確是照 `criteria_stage1/2307.05527.json` / `criteria_stage2/2307.05527.json` 把它們收進來。問題是，現在的 formal criteria 幾乎把 topic operationalize 成「generative audio model / application + output entirely audio」，卻沒有真的把 SR 題目裡的 **ethical implications** 收成 hard boundary。換句話說，這四個 FP 更像是 current criteria formalization 太鬆，而不是 cutoff 還沒修乾淨。

### 全部錯例 inventory

#### `reviewer_semantic_gap` (`8`)

- `du_joint_2020` (FN) — A Joint Framework of Denoising Autoencoder and Generative Vocoder for Monaural Speech Enhancement
  - 口語解釋：stacked enhancement 加上 generative vocoder 其實仍是 generative-audio application，這裡是 reviewer 把 generative role 看得太窄。
  - 為什麼不是另外兩類：它不是 criteria_or_gold_tension，因為 paper 本身其實仍然能落在 active criteria 內；也不是 paper_evidence_incomplete，因為 paper 已經把 generative component 或 output role 說得夠清楚。；次標籤：generative_vocoder_role
- `kwon_effective_2019` (FN) — Effective parameter estimation methods for an ExcitNet model in generative text-to-speech systems
  - 口語解釋：這其實是很直的 neural TTS generative-audio paper，但 reviewer 額外引入 ethics / societal framing 造成誤殺。
  - 為什麼不是另外兩類：它不是 criteria_or_gold_tension，因為 paper 本身其實仍然能落在 active criteria 內；也不是 paper_evidence_incomplete，因為 paper 已經把 generative component 或 output role 說得夠清楚。；次標籤：imported_ethics_filter
- `lemercier_analysing_nodate` (FN) — Analysing Diffusion-based Generative Approaches versus Discriminative Approaches for Speech Restoration
  - 口語解釋：speech restoration with generative models 本來很像 active criteria 可收的 generative-audio paper，reviewer 卻額外把倫理/社會性門檻拉進來。
  - 為什麼不是另外兩類：它不是 criteria_or_gold_tension，因為 paper 本身其實仍然能落在 active criteria 內；也不是 paper_evidence_incomplete，因為 paper 已經把 generative component 或 output role 說得夠清楚。；次標籤：imported_ethics_filter
- `louie_expressive_2021` (FN) — Expressive Communication: A Common Framework for Evaluating Developments in Generative Models and Steering Interfaces
  - 口語解釋：它其實是在分析 generative music models / interfaces，本來不該單純因為沒有倫理或 systematic-review 語氣就被排掉。
  - 為什麼不是另外兩類：它不是 criteria_or_gold_tension，因為 paper 本身其實仍然能落在 active criteria 內；也不是 paper_evidence_incomplete，因為 paper 已經把 generative component 或 output role 說得夠清楚。；次標籤：imported_ethics_filter, interface_or_analysis_paper
- `ming_feature_2019` (FN) — Feature reinforcement with word embedding and parsing information in neural TTS
  - 口語解釋：neural TTS 明明很符合 active audio-model criteria，卻被 reviewer 因為缺少 ethics framing 砍掉。
  - 為什麼不是另外兩類：它不是 criteria_or_gold_tension，因為 paper 本身其實仍然能落在 active criteria 內；也不是 paper_evidence_incomplete，因為 paper 已經把 generative component 或 output role 說得夠清楚。；次標籤：imported_ethics_filter
- `sawata_versatile_nodate` (FN) — Diffiner: A Versatile Diffusion-based Generative Refiner for Speech Enhancement
  - 口語解釋：diffusion speech refiner 就是 direct generative-audio application，這裡比較像 reviewer 又偷偷加了額外倫理門檻。
  - 為什麼不是另外兩類：它不是 criteria_or_gold_tension，因為 paper 本身其實仍然能落在 active criteria 內；也不是 paper_evidence_incomplete，因為 paper 已經把 generative component 或 output role 說得夠清楚。；次標籤：imported_ethics_filter
- `sekiguchi_semi-supervised_2019` (FN) — Semi-Supervised Multichannel Speech Enhancement With a Deep Speech Prior
  - 口語解釋：它明明把 deep generative speech prior 放在 enhancement 裡當核心技術，active criteria 其實可以收，但 reviewer 還是把它排掉了。
  - 為什麼不是另外兩類：它不是 criteria_or_gold_tension，因為 paper 本身其實仍然能落在 active criteria 內；也不是 paper_evidence_incomplete，因為 paper 已經把 generative component 或 output role 說得夠清楚。；次標籤：generative_prior_in_enhancement
- `shankar_non-parallel_2020` (FN) — Non-parallel Emotion Conversion using a Deep-Generative Hybrid Network and an Adversarial Pair Discriminator
  - 口語解釋：技術上就是 voice conversion generative-audio paper，但 reviewer 又把它當成缺少 ethics framing 就不能收。
  - 為什麼不是另外兩類：它不是 criteria_or_gold_tension，因為 paper 本身其實仍然能落在 active criteria 內；也不是 paper_evidence_incomplete，因為 paper 已經把 generative component 或 output role 說得夠清楚。；次標籤：imported_ethics_filter

#### `paper_evidence_incomplete` (`3`)

- `douwes2021energy` (FN) — Energy Consumption of Deep Generative Audio Models
  - 口語解釋：它很像在分析 generative audio model 的評估指標，但 title/abstract 又有點像 meta / metric paper，observable evidence 真的不夠穩。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為歧義本來就寫在 paper 的可觀察證據裡；也不是 criteria_or_gold_tension，因為一旦把缺的證據補清楚，paper 仍有機會和 active criteria 對齊。；次標籤：metric_or_meta_boundary
- `huang2020ai` (FN) — AI Song Contest: Human-AI Co-Creation in Songwriting
  - 口語解釋：這篇把歌詞、音樂、聲音和 co-creation 混在一起講，primary output 到底是不是 current criteria 要的純 audio 並不夠乾淨。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為歧義本來就寫在 paper 的可觀察證據裡；也不是 criteria_or_gold_tension，因為一旦把缺的證據補清楚，paper 仍有機會和 active criteria 對齊。；次標籤：mixed_output_boundary, co_creation_framing
- `zhang_incorporating_2021` (FN) — Incorporating Multi-Target in Multi-Stage Speech Enhancement Model for Better Generalization
  - 口語解釋：從 stage-1 可觀察證據來看，這篇到底是 generative model 還是 denoising prior 為主其實不夠穩。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為歧義本來就寫在 paper 的可觀察證據裡；也不是 criteria_or_gold_tension，因為一旦把缺的證據補清楚，paper 仍有機會和 active criteria 對齊。；次標籤：generative_role_underdetermined

#### `criteria_or_gold_tension` (`30`)

- `ghose2020autofoley` (FP) — AutoFoley: Artificial Synthesis of Synchronized Sound Tracks for Silent Videos with Deep Learning
  - 口語解釋：video-conditioned Foley 在這次 active criteria 下仍被吃成 audio-generation application，所以錯更像 criteria 與 gold 的邊界不一致。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的判斷方向基本上跟 active audio-only / primary-focus 規則一致；也不是 paper_evidence_incomplete，因為 title/abstract 或 markdown 已經提供了足夠的邊界證據。；次標籤：video_conditioned_audio, gold_negative_but_active_criteria_positive
- `greshler_catch--waveform_2021` (FP) — Catch-A-Waveform: Learning to Generate Audio from a Single Short Example
  - 口語解釋：單一短音訊樣本生成新音訊，照 active criteria 幾乎就是直覺 include，所以這裡主要是 gold/criteria 打架。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的判斷方向基本上跟 active audio-only / primary-focus 規則一致；也不是 paper_evidence_incomplete，因為 title/abstract 或 markdown 已經提供了足夠的邊界證據。；次標籤：gold_negative_but_active_criteria_positive
- `huang2018music` (FP) — Music Transformer
  - 口語解釋：這篇照 active criteria 是乾淨的 generative-audio include，現在會變成 FP 代表主要是 gold boundary 比 current criteria 更窄。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的判斷方向基本上跟 active audio-only / primary-focus 規則一致；也不是 paper_evidence_incomplete，因為 title/abstract 或 markdown 已經提供了足夠的邊界證據。；次標籤：gold_negative_but_active_criteria_positive
- `serra_universal_2022` (FP) — Universal Speech Enhancement with Score-based Diffusion
  - 口語解釋：diffusion speech enhancement 在這個 run 的 criteria 讀法裡仍會被當成 generative-audio application，衝突點主要在 gold 怎麼切 enhancement。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的判斷方向基本上跟 active audio-only / primary-focus 規則一致；也不是 paper_evidence_incomplete，因為 title/abstract 或 markdown 已經提供了足夠的邊界證據。；次標籤：enhancement_vs_generation_boundary, gold_negative_but_active_criteria_positive
- `Li2021Robust` (FN) — Robust Detection of Machine-induced Audio Attacks in Intelligent Audio Systems with Microphone Array
  - 口語解釋：這篇主軸是 synthetic-audio attack detection / defense，不是生成音訊本體，current criteria 下排除是連貫的。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的判斷方向基本上跟 active audio-only / primary-focus 規則一致；也不是 paper_evidence_incomplete，因為 title/abstract 或 markdown 已經提供了足夠的邊界證據。；次標籤：detector_or_forensics
- `Wang2020DeepSonar` (FN) — DeepSonar: Towards Effective and Robust Detection of AI-Synthesized Fake Voices
  - 口語解釋：這是 machine-induced audio attack detection paper，不是 generative audio output paper，所以 current criteria 很自然會把它排掉。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的判斷方向基本上跟 active audio-only / primary-focus 規則一致；也不是 paper_evidence_incomplete，因為 title/abstract 或 markdown 已經提供了足夠的邊界證據。；次標籤：detector_or_forensics
- `bazin_nonoto_2019` (FN) — NONOTO: A Model-agnostic Web Interface for Interactive Music Composition by Inpainting
  - 口語解釋：interface 同時暴露 score、MusicXML、MIDI 和 audio，不是乾淨的 entirely-audio primary output。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的判斷方向基本上跟 active audio-only / primary-focus 規則一致；也不是 paper_evidence_incomplete，因為 title/abstract 或 markdown 已經提供了足夠的邊界證據。；次標籤：mixed_output_interface
- `boulianne2020study` (FN) — A Study of Inductive Biases for Unsupervised Speech Representation Learning
  - 口語解釋：paper 的輸出是 representation learning / classification，不是生成音訊本身，所以這裡更像 scope mismatch。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的判斷方向基本上跟 active audio-only / primary-focus 規則一致；也不是 paper_evidence_incomplete，因為 title/abstract 或 markdown 已經提供了足夠的邊界證據。；次標籤：representation_or_classification
- `brunner_symbolic_2018` (FN) — Symbolic Music Genre Transfer with CycleGAN
  - 口語解釋：symbolic music genre transfer 在 active audio-only criteria 下就是 out。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的判斷方向基本上跟 active audio-only / primary-focus 規則一致；也不是 paper_evidence_incomplete，因為 title/abstract 或 markdown 已經提供了足夠的邊界證據。；次標籤：symbolic_output
- `fenaux_bumblebee_2021` (FN) — BumbleBee: A Transformer for Music
  - 口語解釋：abstract 直接寫 MIDI output，這對 active audio-only criteria 來說就是 out。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的判斷方向基本上跟 active audio-only / primary-focus 規則一致；也不是 paper_evidence_incomplete，因為 title/abstract 或 markdown 已經提供了足夠的邊界證據。；次標籤：symbolic_output
- `genchel_explicitly_2019` (FN) — Explicitly Conditioned Melody Generation: A Case Study with Interdependent RNNs
  - 口語解釋：這篇是 symbolic melody-generation framing，不是 audio-only generation。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的判斷方向基本上跟 active audio-only / primary-focus 規則一致；也不是 paper_evidence_incomplete，因為 title/abstract 或 markdown 已經提供了足夠的邊界證據。；次標籤：symbolic_output
- `gillick_learning_2019` (FN) — Learning to Groove with Inverse Sequence Transformations
  - 口語解釋：full text 把 output 說成 MIDI performance，不是 audio-only generation。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的判斷方向基本上跟 active audio-only / primary-focus 規則一致；也不是 paper_evidence_incomplete，因為 title/abstract 或 markdown 已經提供了足夠的邊界證據。；次標籤：symbolic_output, fulltext_resolved
- `guo_hierarchical_2021` (FN) — Hierarchical Recurrent Neural Networks for Conditional Melody Generation with Long-term Structure
  - 口語解釋：full text 說得很清楚它在做 symbolic approach / lead-sheet melody generation，不是音訊本體。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的判斷方向基本上跟 active audio-only / primary-focus 規則一致；也不是 paper_evidence_incomplete，因為 title/abstract 或 markdown 已經提供了足夠的邊界證據。；次標籤：symbolic_output, fulltext_resolved
- `hadjeres_piano_2021` (FN) — The Piano Inpainting Application
  - 口語解釋：full text 很清楚是 MIDI piano-performance inpainting，不是 waveform audio generation。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的判斷方向基本上跟 active audio-only / primary-focus 規則一致；也不是 paper_evidence_incomplete，因為 title/abstract 或 markdown 已經提供了足夠的邊界證據。；次標籤：symbolic_output, fulltext_resolved
- `han_symbolic_nodate` (FN) — Symbolic Music Loop Generation with Neural Discrete Representations
  - 口語解釋：MIDI / symbolic loop generation 直接撞到 active audio-only rule。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的判斷方向基本上跟 active audio-only / primary-focus 規則一致；也不是 paper_evidence_incomplete，因為 title/abstract 或 markdown 已經提供了足夠的邊界證據。；次標籤：symbolic_output
- `hung_improving_2019` (FN) — Improving Automatic Jazz Melody Generation by Transfer Learning Techniques
  - 口語解釋：full text 顯示它是 melody generation over MIDI phrases，不是直接產生 audio。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的判斷方向基本上跟 active audio-only / primary-focus 規則一致；也不是 paper_evidence_incomplete，因為 title/abstract 或 markdown 已經提供了足夠的邊界證據。；次標籤：symbolic_output, fulltext_resolved
- `kaur_time_2023` (FN) — Time out of Mind: Generating Rate of Speech conditioned on emotion and speaker
  - 口語解釋：這篇輸出是 timing / SSML control，不是音訊本身，所以 active criteria 會把它視為中間表示而不是 audio output。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的判斷方向基本上跟 active audio-only / primary-focus 規則一致；也不是 paper_evidence_incomplete，因為 title/abstract 或 markdown 已經提供了足夠的邊界證據。；次標籤：intermediate_control_output
- `liang_midi-sandwich2_2019` (FN) — MIDI-Sandwich2: RNN-based Hierarchical Multi-modal Fusion Generation VAE networks for multi-track symbolic music generation
  - 口語解釋：multi-track symbolic / pianoroll generation 明確不符合 active audio-only rule。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的判斷方向基本上跟 active audio-only / primary-focus 規則一致；也不是 paper_evidence_incomplete，因為 title/abstract 或 markdown 已經提供了足夠的邊界證據。；次標籤：symbolic_output
- `liang_midi-sandwich_2019` (FN) — MIDI-Sandwich: Multi-model Multi-task Hierarchical Conditional VAE-GAN networks for Symbolic Single-track Music Generation
  - 口語解釋：single-track melody generation 也是 symbolic output，直接撞 active rule。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的判斷方向基本上跟 active audio-only / primary-focus 規則一致；也不是 paper_evidence_incomplete，因為 title/abstract 或 markdown 已經提供了足夠的邊界證據。；次標籤：symbolic_output
- `mittal_symbolic_2021` (FN) — Symbolic Music Generation with Diffusion Models
  - 口語解釋：這篇是 explicit symbolic music generation，與 active audio-only criteria 不合。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的判斷方向基本上跟 active audio-only / primary-focus 規則一致；也不是 paper_evidence_incomplete，因為 title/abstract 或 markdown 已經提供了足夠的邊界證據。；次標籤：symbolic_output
- `nakatani_maximum_2019` (FN) — Maximum likelihood convolutional beamformer for simultaneous denoising and dereverberation
  - 口語解釋：beamforming / denoising paper 不是 generative-audio model 或 application。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的判斷方向基本上跟 active audio-only / primary-focus 規則一致；也不是 paper_evidence_incomplete，因為 title/abstract 或 markdown 已經提供了足夠的邊界證據。；次標籤：beamforming_or_denoising
- `neves_generating_2022` (FN) — Generating music with sentiment using Transformer-GANs
  - 口語解釋：paper 明講 symbolic music generation，active audio-only criteria 下排除是直的。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的判斷方向基本上跟 active audio-only / primary-focus 規則一致；也不是 paper_evidence_incomplete，因為 title/abstract 或 markdown 已經提供了足夠的邊界證據。；次標籤：symbolic_output
- `pati_learning_2019` (FN) — Learning to Traverse Latent Spaces for Musical Score Inpainting
  - 口語解釋：musical-score inpainting 就是 symbolic-output paper。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的判斷方向基本上跟 active audio-only / primary-focus 規則一致；也不是 paper_evidence_incomplete，因為 title/abstract 或 markdown 已經提供了足夠的邊界證據。；次標籤：symbolic_output
- `purwins2019deep` (FN) — Deep Learning for Audio Signal Processing
  - 口語解釋：這篇是 broad audio deep learning review，generative audio 只是一部分，current criteria 會把它當成主題太廣。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的判斷方向基本上跟 active audio-only / primary-focus 規則一致；也不是 paper_evidence_incomplete，因為 title/abstract 或 markdown 已經提供了足夠的邊界證據。；次標籤：broad_review_not_primary_focus
- `thio_minimal_2019` (FN) — A Minimal Template for Interactive Web-based Demonstrations of Musical Machine Learning
  - 口語解釋：template / demo paper 不是主要在做 generative-audio research contribution。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的判斷方向基本上跟 active audio-only / primary-focus 規則一致；也不是 paper_evidence_incomplete，因為 title/abstract 或 markdown 已經提供了足夠的邊界證據。；次標籤：template_or_demo
- `wang_armor_2021` (FN) — Armor: A Benchmark for Meta-evaluation of Artificial Music
  - 口語解釋：這篇是 benchmark / evaluation paper，不是 generative model 或 application paper，criteria 跟 gold 的範圍不一致才會留下來。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的判斷方向基本上跟 active audio-only / primary-focus 規則一致；也不是 paper_evidence_incomplete，因為 title/abstract 或 markdown 已經提供了足夠的邊界證據。；次標籤：benchmark_or_evaluation_paper
- `wu_jazz_2020` (FN) — The Jazz Transformer on the Front Line: Exploring the Shortcomings of AI-composed Music through Quantitative Measures
  - 口語解釋：lead-sheet / MIDI 중심 的輸出讓它在 active criteria 下還是 symbolic paper。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的判斷方向基本上跟 active audio-only / primary-focus 規則一致；也不是 paper_evidence_incomplete，因為 title/abstract 或 markdown 已經提供了足夠的邊界證據。；次標籤：symbolic_output, fulltext_resolved
- `wu_power_2022` (FN) — The Power of Fragmentation: A Hierarchical Transformer Model for Structural Segmentation in Symbolic Music Generation
  - 口語解釋：title 就是 symbolic music generation，排除符合 active audio-only criteria。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的判斷方向基本上跟 active audio-only / primary-focus 規則一致；也不是 paper_evidence_incomplete，因為 title/abstract 或 markdown 已經提供了足夠的邊界證據。；次標籤：symbolic_output
- `you_self-supervised_2021` (FN) — Self-supervised Contrastive Cross-Modality Representation Learning for Spoken Question Answering
  - 口語解釋：spoken QA / answer prediction 不是 generative audio output，所以 active criteria 下很自然會被排掉。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的判斷方向基本上跟 active audio-only / primary-focus 規則一致；也不是 paper_evidence_incomplete，因為 title/abstract 或 markdown 已經提供了足夠的邊界證據。；次標籤：spoken_qa_not_generation
- `zhao_review_2022` (FN) — A Review of Intelligent Music Generation Systems
  - 口語解釋：這篇 survey 橫跨 symbolic 和 audio music generation，對 active audio-only criteria 來說還是太寬。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的判斷方向基本上跟 active audio-only / primary-focus 規則一致；也不是 paper_evidence_incomplete，因為 title/abstract 或 markdown 已經提供了足夠的邊界證據。；次標籤：survey_broader_than_audio_only

### 這篇真正值得留給 LLM 的 judgment tasks

- 先做 literal-criteria check：不要被 broad topic rhetoric 帶走，直接照 enumerated inclusion / exclusion rules 判。
- 做 output-modality check：primary output 到底是 audio-only、symbolic / MIDI、mixed，還是根本非音訊。
- 做 primary-focus check：這篇到底主要在做 generative audio model / application，還是 detector、benchmark、metric paper、interface、representation learner、broad survey。
- 做 generative-role-in-enhancement check：對 enhancement / restoration paper，要判 generative model 是核心應用，還是只是輔助 prior、vocoder、control module。

工程底線：corrected split-cutoff rerun 之後，`2307` 已經不是 cutoff 問題。大部分殘差都是 symbolic-vs-audio、task-family scope 這種 criteria / gold tension；比較小的一塊 reviewer gap，則是因為 run 偷偷把 ethics / social-impact filter 加嚴了。

## 5. `2409.13738`

- Best run：`20260406_full_gpt5_low_2stagedirect_rerun_2409_2511`
- Model：`gpt-5` / reasoning `low` / `two_stage_direct_review`
- Metrics：`TP=20`、`FP=4`、`TN=59`、`FN=1`、`F1=0.8889`
- 主標籤分布：`reviewer_semantic_gap=0`、`paper_evidence_incomplete=1`、`criteria_or_gold_tension=4`

這個 selected run 是依你指定的 allowed pool 從 `two_stage_direct_review` 裡挑出來的，不是 production authority，也不是在跟歷史 one-stage 高分賽跑。雖然 repo 裡還有一個 `merged_two_stage_*` run 分數略高，但這次刻意不納入，因為你要看的就是 direct-review family 自己的殘差結構。

現在真正還需要 LLM 的事：對 `2409` 來說，真正還需要 LLM 的，不只是 `target-boundary`，還包括 `validation-boundary`。也就是說，模型要同時回答兩件事：這篇到底是不是在從自然語言抽 process / decisional model？它到底做的是實證驗證，還是只有看起來 promising 的 NLP-assisted support？

Historical note：這篇現在已經不是 category 4 的問題。主殘差就是一篇 validation 描述不夠乾淨的 FN，加上四個 Bellan family 的 gold / criteria boundary case。

對 `2409` 來說，bounded deep-read 之後，這四個 Bellan-family FP 也更像是 **criteria formalization 對「process extraction」放得太寬**，不只是 gold 太窄。它們全部都 `cutoff_pass=true`，而且 selected run 真的用 active `criteria_stage1/2409.13738.json` / `criteria_stage2/2409.13738.json` 把它們收進來；但 paper 本體做的比較像 process entities / relations extraction、dataset construction、baseline benchmarking，離 topic_definition 裡的 **final process-model extraction** 還有一步。也就是說，如果你問「要不要重跑」，答案不是去改 cutoff，而是先決定 criteria 到底要不要把 intermediate representation / dataset paper 排掉。

### 全部錯例 inventory

#### `reviewer_semantic_gap` (`0`)

- 這類在這個 selected run 裡沒有留下錯例。

#### `paper_evidence_incomplete` (`1`)

- `lopez_assisted_declarative_process` (FN) — Assisted Declarative Process Creation from Natural Language Descriptions
  - 口語解釋：這篇其實就在 in-scope 的邊上，但 empirical validation 寫得半開半關，所以 stage2 會保守排掉並不奇怪。gold 之所以還把它算正例，主要是因為 validation 證據沒有被 paper 自己寫乾淨。
  - 為什麼不是另外兩類：不是 `reviewer_semantic_gap`，因為 reviewer 是順著 paper 自己的保留語氣在判；也不是 `criteria_or_gold_tension`，因為只要 validation evidence 再寫明確一點，current criteria 和 gold 其實還有機會對齊。；次標籤：validation_ambiguity, semi_automatic_support, declarative_models

#### `criteria_or_gold_tension` (`4`)

- `bellan_gpt3_2022` (FP) — Extracting Business Process Entities and Relations from Text Using Pre-trained Language Models and In-Context Learning
  - 口語解釋：照 current criteria 看，這篇被 include 很合理。paper 明講自己在做 process extraction from text，也給了 GPT-3 method 和 empirical assessment，所以衝突點更像 gold 或 boundary definition，而不是 reviewer 看錯。
  - 為什麼不是另外兩類：不是 `reviewer_semantic_gap`，因為 reviewer 的讀法和 paper、criteria 是對得上的；也不是 `paper_evidence_incomplete`，因為 method 和 evaluation 都寫得很明。；次標籤：duplicate_variant, intermediate_representation, gpt3_method
- `bellan_pet_23` (FP) — PET: An Annotated Dataset for Process Extraction from Natural Language Text Tasks
  - 口語解釋：它雖然是 dataset / resource paper，但不只是丟資料集而已，還有 extraction baselines 和 evaluation。也就是說，current criteria 其實比 gold 更容易把它放進來。
  - 為什麼不是另外兩類：不是 `reviewer_semantic_gap`，因為 include 本身就有 paper scope 和 experiments 支撐；也不是 `paper_evidence_incomplete`，因為 contribution 與 evaluation 都寫得清楚。；次標籤：dataset_paper, baseline_methods, duplicate_variant
- `bellan2022process` (FP) — Process extraction from natural language text: the PET dataset and annotation guidelines
  - 口語解釋：這其實就是 PET paper 的 title variant。它還是在做 process extraction from text，也有 baseline evaluation，所以在 current criteria 下被 include 很正常，但 gold 還是把它算負例。
  - 為什麼不是另外兩類：不是 `reviewer_semantic_gap`，因為 include 跟 text 和 criteria 都對得上；也不是 `paper_evidence_incomplete`，因為 paper 對 contribution 和 experiment 都寫得很清楚。；次標籤：title_variant, dataset_paper, baseline_methods
- `bellan2022extracting` (FP) — Extracting business process entities and relations from text using pre-trained language models and in-context learning
  - 口語解釋：這則是 GPT-3 Bellan paper 的 normalized-title variant。它同樣把 process-extraction framing、具體 extraction task 和 empirical assessment 都擺得很完整，所以 mismatch 還是在 gold 那邊切得比較窄。
  - 為什麼不是另外兩類：不是 `reviewer_semantic_gap`，因為 include logic 本身是自洽的；也不是 `paper_evidence_incomplete`，因為 paper 提供了 method、task 和 result。；次標籤：title_variant, duplicate_variant, gpt3_method

### 這篇真正值得留給 LLM 的 judgment tasks

- 先逼 reviewer 回答：paper 最終抽出的 object 到底是 process / decisional model，還是 entity、relation、dataset、guideline 之類的中間產物。
- 讀 validation 語句時，不要只看 paper 有沒有 claim；要看它到底有沒有把 empirical validation 寫到足以進 evidence base。
- 當 gold scope 比 current criteria 更窄時，要把 dataset / resource paper、entity-relation extraction、final process-model extraction 這幾類東西分乾淨。

工程底線：一旦 `2409` 被鎖回 allowed two-stage direct-review pool，殘差就不像單純 reviewer 笨判，而更像 validation ambiguity 加上一團很緊的 Bellan-family gold-boundary knot。

## 6. `2511.13936`

- Best run：`20260408_full_gpt54mini_xhigh_2stagedirect_2409_2511`
- Model：`gpt-5.4-mini` / reasoning `xhigh` / `two_stage_direct_review`
- Metrics：`TP=26`、`FP=1`、`TN=57`、`FN=4`、`F1=0.9123`
- 主標籤分布：`reviewer_semantic_gap=1`、`paper_evidence_incomplete=3`、`criteria_or_gold_tension=1`

這個 best run 一樣來自 allowed `two_stage_direct_review` pool，而且是後來的 `2026-04-08` artifact；如果只看 baseline CSV，其實根本抓不到它。所以 `2511` 這次能選對 run，本身就說明了為什麼最後還是得直接讀 later run artifacts。

現在真正還需要 LLM 的事：對 `2511` 來說，真正還需要 LLM 的，是把 learning signal ledger 記乾淨。也就是要把 ranking、pairwise preference、RLHF，跟 MOS-only prediction、JND discrimination、evaluation-only human tests 分開，而且還要能看出關鍵 preference signal 是不是藏在 abstract 之外。

Historical note：這篇現在也不是 category 4。selected run 的主殘差就是 stage1 看不到 preference-learning 關鍵證據，以及一篇把 same/different JND supervision 誤讀成 preference learning 的 FP。

### 全部錯例 inventory

#### `reviewer_semantic_gap` (`1`)

- `manocha2020differentiable` (FP) — A differentiable perceptual audio metric learned from just noticeable differences
  - 口語解釋：reviewer 把 same-versus-different 的 JND supervision，外加 downstream A/B test，直接擴讀成 preference learning。照 current criteria 嚴格看，這一步其實跨太大了。
  - 為什麼不是另外兩類：不是 `paper_evidence_incomplete`，因為 paper 已經把 supervision 和 evaluation setup 說得很清楚；也不是 `criteria_or_gold_tension`，因為只要把 same/different 和 ranking / preference 分開，gold negative 跟 current criteria 其實是對齊的。；次標籤：same_vs_different, evaluation_only_ab, stage2_false_positive

#### `paper_evidence_incomplete` (`3`)

- `chumbalov2020scalable` (FN) — Scalable and efficient comparison-based search without features
  - 口語解釋：abstract 一眼看上去很不像 audio paper，最後還收在 movie-actor search experiment；跟 audio 有關的關鍵證據要到 full text 才看得比較清楚，所以 Stage 1 很容易直接漏掉。
  - 為什麼不是另外兩類：不是 `reviewer_semantic_gap`，因為 Stage 1 並沒有漏看明確的 abstract evidence；也不是 `criteria_or_gold_tension`，因為 full paper 其實還是可以和 current criteria 對齊。；次標籤：stage1_gate, audio_buried_in_fulltext, triplet_comparisons
- `jayawardena2020ordinal` (FN) — How Ordinal Are Your Data?
  - 口語解釋：abstract 只把它包成 ordinal regression on speech / affective data，但真正決定它能不能算進來的 pairwise-preference loss 要到 full text 才會冒出來。
  - 為什麼不是另外兩類：不是 `reviewer_semantic_gap`，因為 abstract 真的沒有把關鍵 pairwise-preference detail 講出來；也不是 `criteria_or_gold_tension`，因為 full paper 一旦把 loss construction 看清楚，還是能跟 current criteria 對齊。；次標籤：ordinal_to_pairwise, abstract_underspecification, speech_affective_data
- `huang2025step` (FN) — Step-Audio: Unified Understanding and Generation in Intelligent Speech Interaction
  - 口語解釋：abstract 只講 benchmarked human evaluation，看起來很像 evaluation-only paper；但 full text 後面其實把 RLHF、chosen/rejected pairs、reward model、PPO 都攤出來了，所以關鍵 learning signal 根本藏在 abstract 之外。
  - 為什麼不是另外兩類：不是 `reviewer_semantic_gap`，因為 reviewer 在 Stage 1 看到的真的只是 evaluation-looking language；也不是 `criteria_or_gold_tension`，因為 full paper 其實很清楚地支持 gold positive。；次標籤：rlhf_hidden_in_fulltext, preference_data, reward_model

#### `criteria_or_gold_tension` (`1`)

- `dong2020pyramid` (FN) — Pyramid BLSTM for Real-time and Non-intrusive Prediction of Crowdsourced Speech-Quality Ratings
  - 口語解釋：不管 abstract 還是 full text，這篇都一直停在收 subjective ratings、再拿來預測 MOS。它沒有真的給 ranking、pairwise preference 或 RL loop，所以 negative decision 反而比 positive gold 更像 current criteria 的讀法。
  - 為什麼不是另外兩類：不是 `reviewer_semantic_gap`，因為 reviewer 的 objection 和 current criteria 很貼；也不是 `paper_evidence_incomplete`，因為 full paper 最後還是沒有把缺的 preference-learning mechanism 補出來。；次標籤：mos_only, ratings_not_rankings, mushra

### 這篇真正值得留給 LLM 的 judgment tasks

- 追蹤 training signal 到底是不是 ranking、pairwise preference、RLHF，而不是只有 MOS prediction 或 post-hoc evaluation。
- 偵測 abstract 有沒有把關鍵 preference signal 藏起來，結果要到 full text 才看得到 pairwise loss、chosen/rejected pairs、reward model、PPO。
- 把 pairwise perceptual discrimination、same-vs-different supervision，和真正的 preference learning 分開。

工程底線：一旦 `2511` 被鎖回 allowed two-stage direct-review pool，殘差其實很乾淨地分成兩群：一群是 stage1 看不到、但 full text 其實有的 preference evidence；另一群則是一個很典型的 semantic overread，把 same/different JND supervision 誤認成 preference learning。

## 7. `2601.19926`

- Best run：`20260417_retry1_gpt54mini_xhigh_2stagedirect_2307_2601`
- Model：`gpt-5.4-mini` / reasoning `xhigh` / `two_stage_direct_review`
- Metrics：`TP=264`、`FP=4`、`TN=20`、`FN=72`、`F1=0.8742`
- 主標籤分布：`reviewer_semantic_gap=4`、`paper_evidence_incomplete=2`、`criteria_or_gold_tension=70`

這個 selected run 現在也已經是 current-style 的 `two_stage_direct_review` baseline，不再是歷史 one-stage fallback。跟舊的 one-stage fallback（`F1=0.9594`）相比，新 run 掉到 `0.8742`，主因不是 precision 崩掉，而是 recall 很早就開始掉：Stage 1 已經先留下 60 個 FN，最後整體累積成 72 個 FN。好處是，這個新 run 終於跟 current cutoff-first two-stage workflow 對齊，也順便證明了 `2601` 現在根本不是 cutoff 問題。

Stage 1 已經留下 60 個 FN；Stage 2 雖然把 FP 從 7 壓到 4，但同時又新增 12 個 FN。換句話說，2601 的 two-stage gain 幾乎都用在壓 FP，代價是 recall 被明顯吃掉。

現在真正還需要 LLM 的事：對 `2601` 來說，真正還需要 LLM 的，是判斷 syntax 到底是不是 transformer-language-model paper 的 primary empirical target，而不是 incidental benchmark、semantics / pragmatics study、architecture note、或 broad interpretability paper。難點不是 paper 有沒有提到 language，而是它到底在測 syntax，還是在測別的東西。

Historical note：這個 corrected selected run 完全沒有 active cutoff / category-4 problem。`cutoff_excluded_count = 0`，而且 76 個 active FP/FN 裡有 0 個是 cutoff-filtered。現在真正留下來的，幾乎全都是 criteria / gold tension，外加一小塊 non-tension 尾巴。

但這裡有一個這輪 API-simulated deep read 才看清楚的修正：`2601` 原本那 6 個 non-tension case，我先前都粗分成 `paper_evidence_incomplete`。重新按 runner 真正會送進 API 的 Stage 1 輸入面做題之後，結論得改成 **`4` 個 `reviewer_semantic_gap` + `2` 個 `paper_evidence_incomplete`**。白話講，就是 selected run 把「一定要在摘要裡直接講 syntax」抓得太死了。像 probing、linguistic knowledge、linguistic phenomena 這些 cue，在 current criteria 下其實已經足夠讓 reviewer 至少留在 `maybe`，不該在 Stage 1 直接砍掉。

對 `2601` 也有一個和 `2307/2409` 類似、但更乾淨的 deep-read 結論：那四個 active FP benchmark cases（`perez-mayos`、`xiang`、`song`、`taktasheva`）全部都 `cutoff_pass=true`，而且 selected run 的確是照 active `criteria_stage1/2601.19926.json` / `criteria_stage2/2601.19926.json` 收進來。它們之所以會被 include，不是因為 cutoff 出錯，而是因為 formal criteria 只要求「empirically assesses syntactic knowledge in TLMs」，卻沒有把 topic_definition 裡更窄的 **interpretability research on how/where syntax is manifested inside the model** 收成硬邊界。這表示這四個 FP 更像是 current criteria 比 SR 題目鬆，而不是 gold 單方面亂標。

### 全部錯例 inventory

#### `reviewer_semantic_gap` (`4`)

- `Lovering2021PredictingIB` (FN) — Predicting Inductive Biases of Pre-Trained Models
  - 口語解釋：title/abstract 已經把 probing 和 linguistic structure 擺上檯面了，這種 case 至少該留在 `maybe`，不該因為沒把 syntax 兩個字講死就直接排掉。
  - 為什麼不是另外兩類：它不是 paper_evidence_incomplete，因為 API-sim pass 只靠 Stage 1 輸入就已經能做出 `maybe`；也不是 criteria_or_gold_tension，因為 full paper 和 active criteria 並沒有根本打架。；次標籤：stage1_strict_literalism
- `hu_prompting_2023` (FN) — Prompting is not a substitute for probability measurements in large language models
  - 口語解釋：這篇雖然沒在摘要裡把 syntax 反覆喊出來，但 linguistic knowledge measurement 搭配 LM probability setup，已經夠形成 syntax-target 的弱訊號。
  - 為什麼不是另外兩類：它不是 paper_evidence_incomplete，因為 API-sim replay 只看可觀察輸入也能給 `maybe`；也不是 criteria_or_gold_tension，因為問題不在 criteria 太窄，而在 reviewer 把 wording threshold 設太高。；次標籤：stage1_strict_literalism
- `li_probing_2022` (FN) — Probing via Prompting
  - 口語解釋：看到 probing、prompting、linguistic information 這組訊號，其實就該先留活口。這案比較像 reviewer 過早硬砍，而不是 paper 完全沒給線索。
  - 為什麼不是另外兩類：它不是 paper_evidence_incomplete，因為 title/abstract 已經足夠支撐 `maybe`；也不是 criteria_or_gold_tension，因為一旦留下來，後面和 active criteria 是能對上的。；次標籤：stage1_strict_literalism
- `wijnholds_assessing_2023` (FN) — Assessing Monotonicity Reasoning in Dutch through Natural Language Inference
  - 口語解釋：TLM + linguistic phenomena（negation / conjunction / disjunction 這類）其實已經是很像 syntax-evaluation 的邊界案，照 current criteria 更合理的動作是先進 `maybe`，不是直接排除。
  - 為什麼不是另外兩類：它不是 paper_evidence_incomplete，因為 API-sim pass 已經能從現有摘要看出 enough-to-hold 的訊號；也不是 criteria_or_gold_tension，因為這裡不是 gold 和 criteria 打架，而是 reviewer 在 Stage 1 太早下死刑。；次標籤：stage1_strict_literalism

#### `paper_evidence_incomplete` (`2`)

- `mysiak_is_2023` (FN) — Is German secretly a Slavic language? What BERT probing can tell us about language groups
  - 口語解釋：這篇真的比較像資訊藏太深。摘要正面寫的是 language-group classification，dependency-tree / syntax probing 的角色要到更後面才比較清楚。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為只看 Stage 1 輸入時確實很難穩定看出 syntax target；也不是 criteria_or_gold_tension，因為補到 full paper 之後仍能和 active criteria 對齊。；次標籤：stage1_observability_gap
- `yanaka_assessing_2021` (FN) — Assessing the Generalization Capacity of Pre-trained Language Models through Japanese Adversarial Natural Language Inference
  - 口語解釋：這案比較慘，Stage 1 可見面幾乎把重點都放在 adversarial NLI，真正的 garden-path / syntax target 很不顯眼，所以被漏掉不算太意外。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為 API-sim pass 只靠現有輸入也很難給出穩定正向判斷；也不是 criteria_or_gold_tension，因為補足全文之後仍然能跟 active criteria 接起來。；次標籤：stage1_observability_gap

#### `criteria_or_gold_tension` (`70`)

- `perez-mayos:etal:2021` (FP) — Assessing the Syntactic Capabilities of Transformer-based Multilingual Language Models
  - 口語解釋：這篇在 active criteria 下幾乎就是 direct syntax/TLM match，殘差主要來自 gold boundary 比 current criteria 更窄。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：gold_negative_but_current_criteria_positive
- `song:etal:2022` (FP) — SLING: Sino Linguistic Evaluation of Large Language Models
  - 口語解釋：這篇在 active criteria 下幾乎就是 direct syntax/TLM match，殘差主要來自 gold boundary 比 current criteria 更窄。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：gold_negative_but_current_criteria_positive
- `taktasheva:etal:2024` (FP) — RuBLiMP: Russian Benchmark of Linguistic Minimal Pairs
  - 口語解釋：這篇在 active criteria 下幾乎就是 direct syntax/TLM match，殘差主要來自 gold boundary 比 current criteria 更窄。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：gold_negative_but_current_criteria_positive
- `xiang:etal:2021` (FP) — CLiMP: A Benchmark for Chinese Language Model Evaluation
  - 口語解釋：這篇在 active criteria 下幾乎就是 direct syntax/TLM match，殘差主要來自 gold boundary 比 current criteria 更窄。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：gold_negative_but_current_criteria_positive
- `Peters:etal:2018` (FN) — Deep Contextualized Word Representations
  - 口語解釋：paper 的主體是非目標 architecture、MT / encoder-decoder setting、resource paper，或 mixed family rather than transformer-LM syntax analysis，所以 current criteria 會把它排掉。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：architecture_or_setting_mismatch
- `WILCOX2025104650` (FN) — Bigger is not always better: The importance of human-scale language modeling for psycholinguistics
  - 口語解釋：這篇屬於 benchmark、robustness、broad interpretability、architecture、multilinguality 或 general LM behavior work，syntax 不是 primary empirical object。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_incidental_or_absent
- `aljaafari_interpreting_2025` (FN) — Interpreting token compositionality in LLMs: A robustness analysis
  - 口語解釋：這篇屬於 benchmark、robustness、broad interpretability、architecture、multilinguality 或 general LM behavior work，syntax 不是 primary empirical object。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_incidental_or_absent
- `alt_probing_2020` (FN) — Probing Linguistic Features of Sentence-Level Representations in Relation Extraction
  - 口語解釋：paper 的主體是非目標 architecture、MT / encoder-decoder setting、resource paper，或 mixed family rather than transformer-LM syntax analysis，所以 current criteria 會把它排掉。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：architecture_or_setting_mismatch
- `aoyama_language_2025` (FN) — Language Models Grow Less Humanlike beyond Phase Transition
  - 口語解釋：這篇屬於 benchmark、robustness、broad interpretability、architecture、multilinguality 或 general LM behavior work，syntax 不是 primary empirical object。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_incidental_or_absent
- `arehalli_neural_2024` (FN) — Neural Networks as Cognitive Models of the Processing of Syntactic Constraints
  - 口語解釋：paper 的主體是非目標 architecture、MT / encoder-decoder setting、resource paper，或 mixed family rather than transformer-LM syntax analysis，所以 current criteria 會把它排掉。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：architecture_or_setting_mismatch
- `asher_limits_2023` (FN) — Limits for learning with language models
  - 口語解釋：paper 的主要 empirical target 是 semantics、pragmatics、reasoning 或 broader interpretability，而不是 syntax 本身。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_not_primary_target
- `chang-etal-2021-convolutions` (FN) — Convolutions and Self-Attention: Re-interpreting Relative Positions in Pre-trained Language Models
  - 口語解釋：這篇屬於 benchmark、robustness、broad interpretability、architecture、multilinguality 或 general LM behavior work，syntax 不是 primary empirical object。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_incidental_or_absent
- `chang_bergen_2022` (FN) — Word Acquisition in Neural Language Models
  - 口語解釋：這篇屬於 benchmark、robustness、broad interpretability、architecture、multilinguality 或 general LM behavior work，syntax 不是 primary empirical object。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_incidental_or_absent
- `chang_when_2024` (FN) — When Is Multilinguality a Curse? Language Modeling for 250 High- and Low-Resource Languages
  - 口語解釋：這篇屬於 benchmark、robustness、broad interpretability、architecture、multilinguality 或 general LM behavior work，syntax 不是 primary empirical object。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_incidental_or_absent
- `clark_cross-linguistic_2023` (FN) — A Cross-Linguistic Pressure for Uniform Information Density in Word Order
  - 口語解釋：paper 的主體是非目標 architecture、MT / encoder-decoder setting、resource paper，或 mixed family rather than transformer-LM syntax analysis，所以 current criteria 會把它排掉。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：architecture_or_setting_mismatch
- `clouatre_local_2022` (FN) — Local Structure Matters Most in Most Languages
  - 口語解釋：這篇屬於 benchmark、robustness、broad interpretability、architecture、multilinguality 或 general LM behavior work，syntax 不是 primary empirical object。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_incidental_or_absent
- `clouatre_local_2022-1` (FN) — Local Structure Matters Most: Perturbation Study in NLU
  - 口語解釋：這篇屬於 benchmark、robustness、broad interpretability、architecture、multilinguality 或 general LM behavior work，syntax 不是 primary empirical object。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_incidental_or_absent
- `conia_probing_2022` (FN) — Probing for Predicate Argument Structures in Pretrained Language Models
  - 口語解釋：paper 的主要 empirical target 是 semantics、pragmatics、reasoning 或 broader interpretability，而不是 syntax 本身。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_not_primary_target
- `constantinescu_investigating_2025` (FN) — Investigating Critical Period Effects in Language Acquisition through Neural Language Models
  - 口語解釋：這篇屬於 benchmark、robustness、broad interpretability、architecture、multilinguality 或 general LM behavior work，syntax 不是 primary empirical object。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_incidental_or_absent
- `dalvi_analyzing_2020` (FN) — Analyzing Redundancy in Pretrained Transformer Models
  - 口語解釋：這篇屬於 benchmark、robustness、broad interpretability、architecture、multilinguality 或 general LM behavior work，syntax 不是 primary empirical object。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_incidental_or_absent
- `duan_unnatural_2025` (FN) — Unnatural Languages Are Not Bugs but Features for LLMs
  - 口語解釋：這篇屬於 benchmark、robustness、broad interpretability、architecture、multilinguality 或 general LM behavior work，syntax 不是 primary empirical object。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_incidental_or_absent
- `dufter-schutze-2020-identifying` (FN) — Identifying Elements Essential for BERT’s Multilinguality
  - 口語解釋：這篇屬於 benchmark、robustness、broad interpretability、architecture、multilinguality 或 general LM behavior work，syntax 不是 primary empirical object。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_incidental_or_absent
- `elgaar_ling-cl_2023` (FN) — Ling-CL: Understanding NLP Models through Linguistic Curricula
  - 口語解釋：這篇屬於 benchmark、robustness、broad interpretability、architecture、multilinguality 或 general LM behavior work，syntax 不是 primary empirical object。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_incidental_or_absent
- `ettinger_what_2020` (FN) — What BERT Is Not: Lessons from a New Suite of Psycholinguistic Diagnostics for Language Models
  - 口語解釋：paper 的主要 empirical target 是 semantics、pragmatics、reasoning 或 broader interpretability，而不是 syntax 本身。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_not_primary_target
- `georges_gabriel_charpentier_not_2023` (FN) — Not all layers are equally as important: Every Layer Counts BERT
  - 口語解釋：這篇屬於 benchmark、robustness、broad interpretability、architecture、multilinguality 或 general LM behavior work，syntax 不是 primary empirical object。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_incidental_or_absent
- `gupta_bert_2021` (FN) — BERT & Family Eat Word Salad: Experiments with Text Understanding
  - 口語解釋：這篇屬於 benchmark、robustness、broad interpretability、architecture、multilinguality 或 general LM behavior work，syntax 不是 primary empirical object。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_incidental_or_absent
- `gurnee_finding_2023` (FN) — Finding Neurons in a Haystack: Case Studies with Sparse Probing
  - 口語解釋：這篇屬於 benchmark、robustness、broad interpretability、architecture、multilinguality 或 general LM behavior work，syntax 不是 primary empirical object。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_incidental_or_absent
- `hewitt-etal-2023-backpack` (FN) — Backpack Language Models
  - 口語解釋：這篇屬於 benchmark、robustness、broad interpretability、architecture、multilinguality 或 general LM behavior work，syntax 不是 primary empirical object。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_incidental_or_absent
- `hlavnova_empowering_2023` (FN) — Empowering Cross-lingual Behavioral Testing of NLP Models with Typological Features
  - 口語解釋：這篇屬於 benchmark、robustness、broad interpretability、architecture、multilinguality 或 general LM behavior work，syntax 不是 primary empirical object。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_incidental_or_absent
- `huang_rigorously_2023` (FN) — Rigorously Assessing Natural Language Explanations of Neurons
  - 口語解釋：這篇屬於 benchmark、robustness、broad interpretability、architecture、multilinguality 或 general LM behavior work，syntax 不是 primary empirical object。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_incidental_or_absent
- `k_cross-lingual_2020` (FN) — Cross-Lingual Ability of Multilingual BERT: An Empirical Study
  - 口語解釋：這篇屬於 benchmark、robustness、broad interpretability、architecture、multilinguality 或 general LM behavior work，syntax 不是 primary empirical object。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_incidental_or_absent
- `kahardipraja-etal-2020-exploring` (FN) — Exploring Span Representations in Neural Coreference Resolution
  - 口語解釋：這篇屬於 benchmark、robustness、broad interpretability、architecture、multilinguality 或 general LM behavior work，syntax 不是 primary empirical object。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_incidental_or_absent
- `kasthuriarachchy_general_2021` (FN) — From General Language Understanding to Noisy Text Comprehension
  - 口語解釋：這篇屬於 benchmark、robustness、broad interpretability、architecture、multilinguality 或 general LM behavior work，syntax 不是 primary empirical object。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_incidental_or_absent
- `kervadec_unnatural_2023` (FN) — Unnatural language processing: How do language models handle machine-generated prompts?
  - 口語解釋：這篇屬於 benchmark、robustness、broad interpretability、architecture、multilinguality 或 general LM behavior work，syntax 不是 primary empirical object。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_incidental_or_absent
- `kim_testing_2021` (FN) — theories of grammatical category
  - 口語解釋：paper 的主體是非目標 architecture、MT / encoder-decoder setting、resource paper，或 mixed family rather than transformer-LM syntax analysis，所以 current criteria 會把它排掉。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：architecture_or_setting_mismatch
- `krasnowska-kieras-wroblewska-2019-empirical` (FN) — Empirical Linguistic Study of Sentence Embeddings
  - 口語解釋：paper 的主體是非目標 architecture、MT / encoder-decoder setting、resource paper，或 mixed family rather than transformer-LM syntax analysis，所以 current criteria 會把它排掉。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：architecture_or_setting_mismatch
- `marecek_balustrades_2019` (FN) — From Balustrades to Pierre Vinken: Looking for Syntax in Transformer Self-Attentions
  - 口語解釋：paper 的主體是非目標 architecture、MT / encoder-decoder setting、resource paper，或 mixed family rather than transformer-LM syntax analysis，所以 current criteria 會把它排掉。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：architecture_or_setting_mismatch
- `marks_geometry_2024` (FN) — The Geometry of Truth: Emergent Linear Structure in Large Language Model Representations of True/False Datasets
  - 口語解釋：這篇屬於 benchmark、robustness、broad interpretability、architecture、multilinguality 或 general LM behavior work，syntax 不是 primary empirical object。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_incidental_or_absent
- `marks_sparse_2024` (FN) — Sparse Feature Circuits: Discovering and Editing Interpretable Causal Graphs in Language Models
  - 口語解釋：這篇屬於 benchmark、robustness、broad interpretability、architecture、multilinguality 或 general LM behavior work，syntax 不是 primary empirical object。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_incidental_or_absent
- `mccoy_embers_2023` (FN) — Embers of autoregression show how large language models are shaped by the problem they are trained to solve
  - 口語解釋：這篇屬於 benchmark、robustness、broad interpretability、architecture、multilinguality 或 general LM behavior work，syntax 不是 primary empirical object。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_incidental_or_absent
- `michael_asking_2020` (FN) — Asking without Telling: Exploring Latent Ontologies in Contextual Representations
  - 口語解釋：paper 的主要 empirical target 是 semantics、pragmatics、reasoning 或 broader interpretability，而不是 syntax 本身。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_not_primary_target
- `mueller_cross-linguistic_2020` (FN) — Cross-Linguistic Syntactic Evaluation of Word Prediction Models
  - 口語解釋：paper 的主體是非目標 architecture、MT / encoder-decoder setting、resource paper，或 mixed family rather than transformer-LM syntax analysis，所以 current criteria 會把它排掉。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：architecture_or_setting_mismatch
- `petersen_lexical_2023` (FN) — Lexical Semantics with Large Language Models: A Case Study of English “break”
  - 口語解釋：paper 的主要 empirical target 是 semantics、pragmatics、reasoning 或 broader interpretability，而不是 syntax 本身。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_not_primary_target
- `ravishankar_effects_2022` (FN) — The Effects of Corpus Choice and Morphosyntax on Multilingual Space Induction
  - 口語解釋：這篇屬於 benchmark、robustness、broad interpretability、architecture、multilinguality 或 general LM behavior work，syntax 不是 primary empirical object。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_incidental_or_absent
- `ribeiro_beyond_2020` (FN) — Beyond Accuracy: Behavioral Testing of NLP Models with CheckList
  - 口語解釋：這篇屬於 benchmark、robustness、broad interpretability、architecture、multilinguality 或 general LM behavior work，syntax 不是 primary empirical object。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_incidental_or_absent
- `salvatore_logical-based_2019` (FN) — A logical-based corpus for cross-lingual evaluation
  - 口語解釋：paper 的主體是非目標 architecture、MT / encoder-decoder setting、resource paper，或 mixed family rather than transformer-LM syntax analysis，所以 current criteria 會把它排掉。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：architecture_or_setting_mismatch
- `sevastjanova_lmfingerprints_2022` (FN) — LMFingerprints: Visual Explanations of Language Model Embedding Spaces through Layerwise Contextualization Scores
  - 口語解釋：這篇屬於 benchmark、robustness、broad interpretability、architecture、multilinguality 或 general LM behavior work，syntax 不是 primary empirical object。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_incidental_or_absent
- `sharma-etal-2023-learning` (FN) — Learning Non-linguistic Skills without Sacrificing Linguistic Proficiency
  - 口語解釋：這篇屬於 benchmark、robustness、broad interpretability、architecture、multilinguality 或 general LM behavior work，syntax 不是 primary empirical object。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_incidental_or_absent
- `sieker_when_2023` (FN) — When Your Language Model Cannot Even Do Determiners Right: Probing for Anti-Presuppositions and the Maximize Presupposition! Principle
  - 口語解釋：paper 的主要 empirical target 是 semantics、pragmatics、reasoning 或 broader interpretability，而不是 syntax 本身。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_not_primary_target
- `sinha_curious_2022` (FN) — The Curious Case of Absolute Position Embeddings
  - 口語解釋：這篇屬於 benchmark、robustness、broad interpretability、architecture、multilinguality 或 general LM behavior work，syntax 不是 primary empirical object。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_incidental_or_absent
- `sorodoc_probing_2020` (FN) — Probing for Referential Information in Language Models
  - 口語解釋：paper 的主要 empirical target 是 semantics、pragmatics、reasoning 或 broader interpretability，而不是 syntax 本身。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_not_primary_target
- `srivastava_beyond_2023` (FN) — Beyond the Imitation Game: Quantifying and extrapolating the capabilities of language models
  - 口語解釋：這篇屬於 benchmark、robustness、broad interpretability、architecture、multilinguality 或 general LM behavior work，syntax 不是 primary empirical object。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_incidental_or_absent
- `sundararaman_syntax-infused_2019` (FN) — Syntax-Infused Transformer and BERT models for Machine Translation and Natural Language Understanding
  - 口語解釋：paper 的主體是非目標 architecture、MT / encoder-decoder setting、resource paper，或 mixed family rather than transformer-LM syntax analysis，所以 current criteria 會把它排掉。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：architecture_or_setting_mismatch
- `tran:etal:2018` (FN) — The Importance of Being Recurrent for Modeling Hierarchical Structure
  - 口語解釋：paper 的主體是非目標 architecture、MT / encoder-decoder setting、resource paper，或 mixed family rather than transformer-LM syntax analysis，所以 current criteria 會把它排掉。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：architecture_or_setting_mismatch
- `turner_steering_2024` (FN) — Steering Language Models with Activation Engineering
  - 口語解釋：這篇屬於 benchmark、robustness、broad interpretability、architecture、multilinguality 或 general LM behavior work，syntax 不是 primary empirical object。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_incidental_or_absent
- `van_schijndel_quantity_2019` (FN) — Quantity doesn’t buy quality syntax with neural language models
  - 口語解釋：paper 的主體是非目標 architecture、MT / encoder-decoder setting、resource paper，或 mixed family rather than transformer-LM syntax analysis，所以 current criteria 會把它排掉。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：architecture_or_setting_mismatch
- `vig_analyzing_2019` (FN) — Analyzing the Structure of Attention in a Transformer Language Model
  - 口語解釋：這篇屬於 benchmark、robustness、broad interpretability、architecture、multilinguality 或 general LM behavior work，syntax 不是 primary empirical object。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_incidental_or_absent
- `wang_interpretability_2022` (FN) — Interpretability in the Wild: a Circuit for Indirect Object Identification in GPT-2 Small
  - 口語解釋：paper 的主要 empirical target 是 semantics、pragmatics、reasoning 或 broader interpretability，而不是 syntax 本身。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_not_primary_target
- `wang_superglue_2019` (FN) — SuperGLUE: A Stickier Benchmark for General-Purpose Language Understanding Systems
  - 口語解釋：這篇屬於 benchmark、robustness、broad interpretability、architecture、multilinguality 或 general LM behavior work，syntax 不是 primary empirical object。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_incidental_or_absent
- `wettig_should_2023` (FN) — Should You Mask 15% in Masked Language Modeling?
  - 口語解釋：這篇屬於 benchmark、robustness、broad interpretability、architecture、multilinguality 或 general LM behavior work，syntax 不是 primary empirical object。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_incidental_or_absent
- `wu_beto_2019` (FN) — Beto, Bentz, Becas: The Surprising Cross-Lingual Effectiveness of BERT
  - 口語解釋：這篇屬於 benchmark、robustness、broad interpretability、architecture、multilinguality 或 general LM behavior work，syntax 不是 primary empirical object。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_incidental_or_absent
- `wu_infusing_2021` (FN) — Infusing Finetuning with Semantic Dependencies
  - 口語解釋：paper 的主要 empirical target 是 semantics、pragmatics、reasoning 或 broader interpretability，而不是 syntax 本身。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_not_primary_target
- `yamakoshi_causal_2023` (FN) — Causal interventions expose implicit situation models for commonsense language understanding
  - 口語解釋：paper 的主要 empirical target 是 semantics、pragmatics、reasoning 或 broader interpretability，而不是 syntax 本身。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_not_primary_target
- `yanaka-etal-2019-neural` (FN) — Can Neural Networks Understand Monotonicity Reasoning?
  - 口語解釋：paper 的主要 empirical target 是 semantics、pragmatics、reasoning 或 broader interpretability，而不是 syntax 本身。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_not_primary_target
- `yanaka-etal-2020-neural` (FN) — Do Neural Models Learn Systematicity of Monotonicity Inference in Natural Language?
  - 口語解釋：paper 的主要 empirical target 是 semantics、pragmatics、reasoning 或 broader interpretability，而不是 syntax 本身。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_not_primary_target
- `zhang_closer_2023` (FN) — A Closer Look at Transformer Attention for Multilingual Translation
  - 口語解釋：paper 的主體是非目標 architecture、MT / encoder-decoder setting、resource paper，或 mixed family rather than transformer-LM syntax analysis，所以 current criteria 會把它排掉。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：architecture_or_setting_mismatch
- `zhang_dependency-based_2021` (FN) — Dependency-based syntax-aware word representations
  - 口語解釋：paper 的主體是非目標 architecture、MT / encoder-decoder setting、resource paper，或 mixed family rather than transformer-LM syntax analysis，所以 current criteria 會把它排掉。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：architecture_or_setting_mismatch
- `zhang_probing_2022` (FN) — Probing GPT-3's Linguistic Knowledge on Semantic Tasks
  - 口語解釋：paper 的主要 empirical target 是 semantics、pragmatics、reasoning 或 broader interpretability，而不是 syntax 本身。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_not_primary_target
- `zhang_unveiling_2024` (FN) — Unveiling Linguistic Regions in Large Language Models
  - 口語解釋：這篇屬於 benchmark、robustness、broad interpretability、architecture、multilinguality 或 general LM behavior work，syntax 不是 primary empirical object。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_incidental_or_absent
- `zimmerman_tokens_2025` (FN) — Tokens, the oft-overlooked appetizer: Large language models, the distributional hypothesis, and meaning
  - 口語解釋：這篇屬於 benchmark、robustness、broad interpretability、architecture、multilinguality 或 general LM behavior work，syntax 不是 primary empirical object。
  - 為什麼不是另外兩類：它不是 reviewer_semantic_gap，因為這裡的決策方向大致符合 current criteria；也不是 paper_evidence_incomplete，因為 scoped text 已經把主要 out-of-scope cue 或 gold-vs-criteria 衝突說得夠清楚。；次標籤：syntax_incidental_or_absent

### 這篇真正值得留給 LLM 的 judgment tasks

- 做 Stage1 observable-fit gate：只看 title / abstract 時，要先判 syntax 與 transformer-LM fit 是 explicit、indirect、還是根本 absent。
- 做 model-name to TLM normalization：像 BERT、RoBERTa、mBERT、GPT-2 這種名字，要能正常映射到 transformer evidence，而不是每次都硬等 literal 的 `Transformer` 字樣。
- 做 syntax-central vs syntax-incidental：syntax 到底是這篇 paper 的 primary empirical target，還是只是 benchmark、capability、interpretability study 裡的一個 ingredient。
- 做 exclusion-setting classifier：快速認出 non-transformer-primary、MT encoder-decoder、resource-only、mixed-family 這些 current criteria 會排掉的 setting。

工程底線：`2601` 現在已經不是 cutoff issue，也幾乎不是 reviewer 純讀錯的問題。這個 corrected two-stage run 主要是在揭露一個很大的 current-criteria-vs-gold mismatch，外加一塊比較小、但真的存在的 Stage-1 observability problem。

## 8. 附錄：為什麼這版不再討論 one-stage fallback

因為現在 `2307/2601` 已經各自有 completed 的 current-style two-stage direct-review run，主統計就必須改用它們。舊的 one-stage fallback 可以拿來做歷史比較，但不能再留在 main analysis 裡。

如果只看數字，one-stage fallback 的確比較高：`2307` 從 `0.9169` 掉到 `0.8673`，`2601` 從 `0.9594` 掉到 `0.8742`。但那不是這次要回答的問題。你現在要的是 current-style comparable runs 的 failure structure，而不是歷史最高分 run 的漂亮數字。
