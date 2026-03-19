# 2409 專用 Stage 2 Closure Follow-up 實驗報告

## Feasibility Check

可以。

依據：`qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19/templates/prompt_manifest.yaml` 已有 `STAGE_SPECIFIC_POLICY_MD` placeholder，且 `templates/04_stage2_qa_synthesis_reviewer_TEMPLATE.md`、`templates/05_synthesis_builder_TEMPLATE.md`、`templates/07_criteria_evaluator_from_synthesis_TEMPLATE.md`、`templates/11_stage2_senior_from_synthesis_TEMPLATE.md` 都已接上這個 placeholder。

`qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19/tools/run_experiment.py` 也已內建 `paper_id + stage + arm` 對 `templates/policies/stage_specific_policy_manifest.yaml` 的載入機制，所以這次可以只靠新增外部 `2409` policy 與一條 manifest entry 完成，不需要回頭修改 shared template semantics、global policy 或 production criteria/runtime。

## Minimal 2409-Only Patch Plan

本次 follow-up 只做一個 `2409` 專用、Stage 2 專用、`qa+synthesis` 專用的外部 policy：

- `qa_first_experiments/qa_first_experiment_v1_2409_stage2_followup_2026-03-19/templates/policies/2409_stage2_closure_policy.md`

並且只透過既有 manifest hook 掛入：

- `qa_first_experiments/qa_first_experiment_v1_2409_stage2_followup_2026-03-19/templates/policies/stage_specific_policy_manifest.yaml`
- `paper_id: 2409.13738`
- `stage: stage2`
- `arm: qa+synthesis`
- `file: 2409_stage2_closure_policy.md`

這條 policy 的實際作用是：把 `2409` Stage 2 的 publication-form closure 與 target/auxiliary-task boundary 分開處理，要求 explicit `arXiv` / preprint / non-peer-reviewed 訊號不能再被當成 minor deferred detail，同時避免 generic BPM/LLM relevance 自動被視為 target criterion satisfied。

## Exact Patch Scope

本次真的改動的檔案只有：

- `qa_first_experiments/qa_first_experiment_v1_2409_stage2_followup_2026-03-19/manifest.json`
- `qa_first_experiments/qa_first_experiment_v1_2409_stage2_followup_2026-03-19/EXPERIMENT_FRAMING.md`
- `qa_first_experiments/qa_first_experiment_v1_2409_stage2_followup_2026-03-19/templates/policies/stage_specific_policy_manifest.yaml`
- `qa_first_experiments/qa_first_experiment_v1_2409_stage2_followup_2026-03-19/templates/policies/2409_stage2_closure_policy.md`
- `qa_first_experiments/qa_first_experiment_v1_2409_stage2_followup_2026-03-19/tools/run_experiment.py`

其中 `tools/run_experiment.py` 只改 bundle-local `RESULTS_ROOT` 與 bundle description；沒有動 validation、routing、prompt injection、scoring、leak logic。

下列 shared/global layer 在這次 follow-up 中保持不變：

- `qa_first_experiments/qa_first_experiment_v1_2409_stage2_followup_2026-03-19/templates/03_stage1_qa_synthesis_reviewer_TEMPLATE.md`
- `qa_first_experiments/qa_first_experiment_v1_2409_stage2_followup_2026-03-19/templates/04_stage2_qa_synthesis_reviewer_TEMPLATE.md`
- `qa_first_experiments/qa_first_experiment_v1_2409_stage2_followup_2026-03-19/templates/05_synthesis_builder_TEMPLATE.md`
- `qa_first_experiments/qa_first_experiment_v1_2409_stage2_followup_2026-03-19/templates/07_criteria_evaluator_from_synthesis_TEMPLATE.md`
- `qa_first_experiments/qa_first_experiment_v1_2409_stage2_followup_2026-03-19/templates/09_stage1_senior_from_synthesis_TEMPLATE.md`
- `qa_first_experiments/qa_first_experiment_v1_2409_stage2_followup_2026-03-19/templates/11_stage2_senior_from_synthesis_TEMPLATE.md`
- `qa_first_experiments/qa_first_experiment_v1_2409_stage2_followup_2026-03-19/templates/policies/global_identity_hygiene_policy.md`
- `qa_first_experiments/qa_first_experiment_v1_2409_stage2_followup_2026-03-19/templates/policies/global_stage1_defer_policy.md`
- `qa_first_experiments/qa_first_experiment_v1_2409_stage2_followup_2026-03-19/tools/validate_bundle.py`
- `scripts/screening/runtime_prompts/runtime_prompts.json`
- `criteria_stage1/2409.13738.json`
- `criteria_stage2/2409.13738.json`

## Execution Summary

### 新 bundle 與新 results root

- bundle：`qa_first_experiments/qa_first_experiment_v1_2409_stage2_followup_2026-03-19`
- results root：`screening/results/qa_first_v1_2409_stage2_followup_2026-03-19`

### 實際執行的 command

```bash
cp -R qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19   qa_first_experiments/qa_first_experiment_v1_2409_stage2_followup_2026-03-19
./.venv/bin/python qa_first_experiments/qa_first_experiment_v1_2409_stage2_followup_2026-03-19/tools/validate_bundle.py
./.venv/bin/python qa_first_experiments/qa_first_experiment_v1_2409_stage2_followup_2026-03-19/tools/run_experiment.py   --papers 2409.13738   --arms qa+synthesis   --concurrency 6   --record-batch-size 6
```

### validate 結果

- `bundle_validation: ok`

### 產出檔案

- `screening/results/qa_first_v1_2409_stage2_followup_2026-03-19/run_manifest.json`
- `screening/results/qa_first_v1_2409_stage2_followup_2026-03-19/REPORT_zh.md`
- `screening/results/qa_first_v1_2409_stage2_followup_2026-03-19/2409.13738__qa+synthesis/stage1_f1.json`
- `screening/results/qa_first_v1_2409_stage2_followup_2026-03-19/2409.13738__qa+synthesis/combined_f1.json`
- `screening/results/qa_first_v1_2409_stage2_followup_2026-03-19/2409.13738__qa+synthesis/latte_review_results.json`
- `screening/results/qa_first_v1_2409_stage2_followup_2026-03-19/2409.13738__qa+synthesis/latte_fulltext_review_results.json`
- `screening/results/qa_first_v1_2409_stage2_followup_2026-03-19/2409.13738__qa+synthesis/hygiene_summary.json`
- `screening/results/qa_first_v1_2409_stage2_followup_2026-03-19/2409.13738__qa+synthesis/validation_failures.jsonl`
- `screening/results/qa_first_v1_2409_stage2_followup_2026-03-19/2409.13738__qa+synthesis/selected_for_stage2.keys.txt`

### Hygiene 現況

- `validation_failures.jsonl`：存在，總數 `51`
- `hygiene_summary.json`：`validation_failure_count = 51`
- failure breakdown：`review_leak = 45`、`stage1_scoring = 2`、`bad_request = 4`、`identity_mismatch = 0`
- final output exact-literal leak：`title = 0`、`topic = 0`
- 結論：transient retry failures 仍存在，但 final outputs 是 hygiene clean。

## Result Comparison

### 五組來源與檔案

- current production：`screening/results/2409.13738_full/stage1_f1.stage_split_criteria_migration.json` / `screening/results/2409.13738_full/combined_f1.stage_split_criteria_migration.json`
- v0 qa+synthesis：`screening/results/qa_first_v0_2409_2511_2026-03-18/2409.13738__qa+synthesis/stage1_f1.json` / `screening/results/qa_first_v0_2409_2511_2026-03-18/2409.13738__qa+synthesis/combined_f1.json`
- v1 first-pass qa+synthesis：`screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18/2409.13738__qa+synthesis/stage1_f1.json` / `screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18/2409.13738__qa+synthesis/combined_f1.json`
- v1 second-pass qa+synthesis：`screening/results/qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19/2409.13738__qa+synthesis/stage1_f1.json` / `screening/results/qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19/2409.13738__qa+synthesis/combined_f1.json`
- 2409 follow-up qa+synthesis：`screening/results/qa_first_v1_2409_stage2_followup_2026-03-19/2409.13738__qa+synthesis/stage1_f1.json` / `screening/results/qa_first_v1_2409_stage2_followup_2026-03-19/2409.13738__qa+synthesis/combined_f1.json`

### 指標總表

| Source | Stage 1 P/R/F1 | Combined P/R/F1 | Stage 2 selected | Stage 1 maybe | senior-finalized | final title leak | final topic leak |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| current production | `0.6000 / 1.0000 / 0.7500` | `0.6667 / 0.9524 / 0.7843` | `40` | `3` | `32` | `0` | `0` |
| v0 qa+synthesis | `0.5526 / 1.0000 / 0.7119` | `0.7407 / 0.9524 / 0.8333` | `38` | `8` | `36` | `0` | `16` |
| v1 first-pass qa+synthesis | `0.4038 / 1.0000 / 0.5753` | `0.7407 / 0.9524 / 0.8333` | `52` | `51` | `66` | `0` | `19` |
| v1 second-pass qa+synthesis | `0.5122 / 1.0000 / 0.6774` | `0.6667 / 0.8571 / 0.7500` | `41` | `41` | `55` | `0` | `0` |
| 2409 follow-up qa+synthesis | `0.5405 / 0.9524 / 0.6897` | `0.8333 / 0.7143 / 0.7692` | `37` | `37` | `46` | `0` | `0` |

### Follow-up 的核心變化

- 相對 second-pass，follow-up 的 Combined precision 從 `0.6667` 升到 `0.8333`。
- 但 Combined recall 從 `0.8571` 掉到 `0.7143`。
- 因此 Combined F1 只到 `0.7692`，沒有救回 `0.8333`。
- Stage 2 selected 也從 `41` 降到 `37`，說明這條 `2409` policy 的實際效果是更保守地關閉 closure。

### Case-Level Inspection

#### `elallaoui2018automatic`

- case family：target-boundary / object-boundary
- gold label：`False`
- second-pass stage1/full：`maybe (senior:3)` / `exclude (senior:2)`
- follow-up stage1/full：`exclude (senior:2)` / `None`
- 判讀：follow-up 未進 Stage 2，因為這次 rerun 的 Stage 1 已經改判為 exclude；這不是新 stage2 policy 的直接效果，而是 rerun 變異。

#### `honkisz2018concept`

- case family：publication-form / closure wobble
- gold label：`True`
- second-pass stage1/full：`maybe (senior:3)` / `include (junior:4,5)`
- follow-up stage1/full：`maybe (senior:3)` / `include (senior:5)`
- 判讀：follow-up 保持 include，且 senior 最終給 5；這表示新 policy 沒把 book-chapter 類 wording 直接硬壓成 publication-form 負證據。

#### `kourani_process_modelling_with_llm`

- case family：publication-form + target-boundary
- gold label：`False`
- second-pass stage1/full：`maybe (senior:3)` / `include (senior:4)`
- follow-up stage1/full：`maybe (senior:3)` / `exclude (senior:2)`
- 判讀：follow-up 由 second-pass include 轉為 exclude，主要來自新 policy 把 explicit arXiv preprint 視為不可再 deferred 的 publication-form 直接負證據。

#### `neuberger_data_augment`

- case family：auxiliary-subtask / target-boundary
- gold label：`False`
- second-pass stage1/full：`maybe (senior:3)` / `include (junior:5,5)`
- follow-up stage1/full：`maybe (senior:3)` / `exclude (senior:2)`
- 判讀：follow-up 由 include 轉為 exclude，實際模型採用的是 publication-form 直接負證據路徑；雖然 case 本身也有 auxiliary-subtask 邊界問題，但這次修正主要落在 closure。

#### `grohs2023large`

- case family：publication-form + broad multi-task target-boundary
- gold label：`False`
- second-pass stage1/full：`maybe (senior:3)` / `include (junior:4,4)`
- follow-up stage1/full：`maybe (senior:3)` / `exclude (senior:2)`
- 判讀：follow-up 由 include 轉為 exclude，同樣主要靠 explicit preprint / publication-form closure，而不是更細的 multi-task target decomposition。

### follow-up 對 5 個指定 case 的實際效果

- `elallaoui2018automatic`：沒有由新 stage2 policy 改寫；它在這次 rerun 的 Stage 1 就已經掉出 Stage 2。
- `honkisz2018concept`：保住 include，代表外掛 policy 沒把 publication-form wording 過度硬化。
- `kourani_process_modelling_with_llm`：成功從 second-pass 的 FP include 收回成 exclude。
- `neuberger_data_augment`：成功從 second-pass 的 FP include 收回成 exclude。
- `grohs2023large`：成功從 second-pass 的 FP include 收回成 exclude。

### 為什麼 F1 還是沒有回到 `0.8333`

- 這條 policy 幾乎只修到了 FP 端，沒有修到 recall。
- follow-up 的 Combined FN 變成更多，主要反映在 `vda_extracting_declarative_process`、`goossens2023extracting`、`neuberger2023beyond`、`qian2020approach` 等 case。
- 也就是說：這次 `2409-only` external policy 成功把 second-pass 的 closure 過寬問題收斂了，但收得太緊，導致整體 recall 受損。

## Exit Decision

1. 是否救回至少 `0.8333`：**否**。follow-up Combined F1 = `0.7692`。
2. 是否保持 hygiene clean：**是**。final outputs 的 protected title/topic exact-literal 命中都為 `0`。
3. 這個 `2409-only` 外掛式 policy 是否值得保留為實驗分支：**值得保留，但只作為失敗但有訊號的實驗分支**。理由是它明確證明：在不碰 global layer 的前提下，可以用 stage-specific external policy 明顯壓低 second-pass 的 FP，但單靠這條路無法同時保住 recall。
4. 是否現在就能再談更大範圍下一步：**還不行**。這條 follow-up 沒達到成功門檻，不應擴到 `qa-only`、也不應擴到四篇 regression。

## Recommended Next Move

- 不要擴跑。
- 不要回頭偷改 shared template 或 global policy。
- 對 `2409` 而言，這次結果已經把問題縮得很小：單靠 `stage2` publication-form / closure 外掛 policy，會把 precision 拉高，但 recall 拉低。
- 因此下一步若還要留在同樣的限制框架內，只值得做更窄的 `2409 stage2` follow-up：
  1. 保留 explicit preprint direct-negative 這條已證明有效的 publication-form closure。
  2. 不再額外收緊那些會把 `goossens2023extracting`、`qian2020approach`、`vda_extracting_declarative_process` 等 case 壓掉的 target/closure wording。
- 如果做不到這種更窄的 third-pass micro-adjustment，就應明確接受：在不動 global layer 的前提下，`2409` 無法只靠 stage-specific external closure policy 被救回到 `0.8333`。

若後面又同時分出多條 `2409` follow-up 線，建議改用 `www.k-dense.ai` 管理 workflow，避免在多個對話串重複搬運同一份 handoff。