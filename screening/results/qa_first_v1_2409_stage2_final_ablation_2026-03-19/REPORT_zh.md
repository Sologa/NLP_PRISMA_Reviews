# 2409 最後一次 Stage 2 External-Policy Ablation 實驗報告

## Feasibility Check

可以。

這次實驗完全沒有動 global/shared layer，也沒有動 production。可行的依據是 second-pass / follow-up bundle 早已具備既有 hook：

- `qa_first_experiments/qa_first_experiment_v1_2409_stage2_followup_2026-03-19/templates/prompt_manifest.yaml`
  內含 `STAGE_SPECIFIC_POLICY_MD`
- shared stage2 `qa+synthesis` templates 已經接收這個 placeholder
- `qa_first_experiments/qa_first_experiment_v1_2409_stage2_followup_2026-03-19/tools/run_experiment.py`
  已內建 `paper_id + stage + arm -> stage_specific_policy_manifest.yaml` 載入邏輯

因此，本次 final ablation 可以合法地只透過：

- `templates/policies/2409_stage2_closure_policy.md`

來做 `2409.13738 + stage2 + qa+synthesis` 的局部外掛修正，不需要碰 shared template semantics、global policy、shared validator semantics、shared runner semantics 或 production criteria/runtime。

## Root-Cause Summary

上一輪 `2409` follow-up policy 混了兩種效果。

第一種是應保留的 publication-form direct negative，這部分是有效的：

- explicit `arXiv` / preprint / non-peer-reviewed publication form -> direct negative
- 不可把這種 explicit publication-form conflict 降成 minor deferred detail
- `book chapter` 單獨出現不自動構成 direct negative

這一組判斷主要對下列 case 有效：

- `kourani_process_modelling_with_llm`
- `neuberger_data_augment`
- `grohs2023large`

第二種是應撤掉或放鬆的 target/closure tightening，這部分上一輪殺掉了 recall：

- generic BPM / LLM usefulness 不算 target fit
- upstream / downstream subtask 不算 target fit
- 只有 principal evaluated task 才算 target satisfied
- auxiliary / broad / incidental fit 直接記為 not satisfied 或 unresolved-negative

這一組收得太緊，上一輪誤殺的典型 family 是：

- `goossens2023extracting`
- `qian2020approach`
- `vda_extracting_declarative_process`
- `neuberger2023beyond`

sanity cases：

- `honkisz2018concept` 支持保留「book chapter alone 不構成 direct negative」
- `elallaoui2018automatic` 不是乾淨的 stage2-only 訊號，不應拿來主導這次 policy

## Final Narrow Patch Plan

這次 final ablation 只做一件事：

- 保留 publication-form direct-negative 部分
- 撤掉 target/closure 過強 hardening 部分

### 保留的 wording 類型

- explicit `arXiv` / preprint / non-peer-reviewed conference or journal mismatch => direct negative
- explicit publication-form conflict 不可再被當成小缺口延後處理
- `book chapter` / edited volume wording alone 不足以單獨構成 direct negative

### 刪除或放鬆的 wording 類型

- 不再寫「generic BPM / LLM usefulness 不算 target fit」這種總體收緊句
- 不再寫「upstream/downstream subtask 一律不算」
- 不再寫「必須是 principal evaluated task 才算 satisfied」
- 不再寫「auxiliary / incidental => not satisfied」

### 這次替換成的較窄句型

- broad BPM relevance 本身不自動構成正向 target evidence
- 但若 evidence 已直接指出從自然語言抽取流程知識、流程模型、宣告式限制或其他 process structure，就不要只因其同時涉及鄰近 BPM/IE/LLM 任務而把它轉成 negative
- multi-task framing 本身不是 contradiction
- target-boundary 不穩時，維持 unresolved / evidence-bound；除非有 explicit contradiction，否則不要直接寫成 direct negative

這樣做仍合法，因為本次只改 `2409` 的 stage-specific external policy 文本，沒有改 shared/global 層。

## Exact Patch Scope

本次實際改動的檔案只有：

- `qa_first_experiments/qa_first_experiment_v1_2409_stage2_final_ablation_2026-03-19/manifest.json`
- `qa_first_experiments/qa_first_experiment_v1_2409_stage2_final_ablation_2026-03-19/EXPERIMENT_FRAMING.md`
- `qa_first_experiments/qa_first_experiment_v1_2409_stage2_final_ablation_2026-03-19/templates/policies/2409_stage2_closure_policy.md`
- `qa_first_experiments/qa_first_experiment_v1_2409_stage2_final_ablation_2026-03-19/tools/run_experiment.py`
  只更新 bundle-local `RESULTS_ROOT` 與 bundle metadata

本次沒有改：

- shared reviewer / synthesis / evaluator / senior templates
- `templates/policies/global_identity_hygiene_policy.md`
- `templates/policies/global_stage1_defer_policy.md`
- `tools/validate_bundle.py`
- 所有 schema / sample / contract
- `scripts/screening/runtime_prompts/runtime_prompts.json`
- `criteria_stage1/2409.13738.json`
- `criteria_stage2/2409.13738.json`
- 任何 `2511`、`qa-only`、四篇 regression 相關內容

另外，`templates/policies/stage_specific_policy_manifest.yaml` 在新 bundle 中保持原樣，沒有新增新 hook，也沒有改 hook semantics。

## Execution Summary

### New bundle 與 new results root

- bundle：
  `qa_first_experiments/qa_first_experiment_v1_2409_stage2_final_ablation_2026-03-19`
- results root：
  `screening/results/qa_first_v1_2409_stage2_final_ablation_2026-03-19`

### 實際執行的 command

```bash
cp -R qa_first_experiments/qa_first_experiment_v1_2409_stage2_followup_2026-03-19 \
  qa_first_experiments/qa_first_experiment_v1_2409_stage2_final_ablation_2026-03-19

./.venv/bin/python qa_first_experiments/qa_first_experiment_v1_2409_stage2_final_ablation_2026-03-19/tools/validate_bundle.py

./.venv/bin/python qa_first_experiments/qa_first_experiment_v1_2409_stage2_final_ablation_2026-03-19/tools/run_experiment.py \
  --papers 2409.13738 \
  --arms qa+synthesis \
  --concurrency 6 \
  --record-batch-size 6
```

### Validation

- `bundle_validation: ok`

### 只跑的 arm

- `2409.13738__qa+synthesis`

### 產出檔案

- `screening/results/qa_first_v1_2409_stage2_final_ablation_2026-03-19/run_manifest.json`
- `screening/results/qa_first_v1_2409_stage2_final_ablation_2026-03-19/REPORT_zh.md`
- `screening/results/qa_first_v1_2409_stage2_final_ablation_2026-03-19/2409.13738__qa+synthesis/stage1_f1.json`
- `screening/results/qa_first_v1_2409_stage2_final_ablation_2026-03-19/2409.13738__qa+synthesis/combined_f1.json`
- `screening/results/qa_first_v1_2409_stage2_final_ablation_2026-03-19/2409.13738__qa+synthesis/latte_review_results.json`
- `screening/results/qa_first_v1_2409_stage2_final_ablation_2026-03-19/2409.13738__qa+synthesis/latte_fulltext_review_results.json`
- `screening/results/qa_first_v1_2409_stage2_final_ablation_2026-03-19/2409.13738__qa+synthesis/hygiene_summary.json`
- `screening/results/qa_first_v1_2409_stage2_final_ablation_2026-03-19/2409.13738__qa+synthesis/validation_failures.jsonl`
- `screening/results/qa_first_v1_2409_stage2_final_ablation_2026-03-19/2409.13738__qa+synthesis/selected_for_stage2.keys.txt`

## Result Comparison

### Metrics 總表

| Source | Stage 1 P/R/F1 | Combined P/R/F1 | Stage 2 selected | Stage 1 maybe | Stage 1 senior-finalized | final title leak | final topic leak |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| current production | `0.6000 / 1.0000 / 0.7500` | `0.6667 / 0.9524 / 0.7843` | `40` | `3` | `32` | `0` | `0` |
| v0 `2409 qa+synthesis` | `0.5526 / 1.0000 / 0.7119` | `0.7407 / 0.9524 / 0.8333` | `38` | `8` | `36` | `0` | `16` |
| v1 second-pass `2409 qa+synthesis` | `0.5122 / 1.0000 / 0.6774` | `0.6667 / 0.8571 / 0.7500` | `41` | `41` | `55` | `0` | `0` |
| `2409 stage2 follow-up` | `0.5405 / 0.9524 / 0.6897` | `0.8333 / 0.7143 / 0.7692` | `37` | `37` | `46` | `0` | `0` |
| 本次 final ablation | `0.5405 / 0.9524 / 0.6897` | `0.7857 / 0.5238 / 0.6286` | `37` | `37` | `53` | `0` | `0` |

### 指標解讀

- 本次 final ablation 的 Stage 1 指標與上一輪 follow-up 完全沒有救回：
  - Stage 1 F1 仍是 `0.6897`
  - Stage 1 maybe 仍是 `37`
- Combined precision 從上一輪 follow-up 的 `0.8333` 小幅下降到 `0.7857`
- Combined recall 從上一輪 follow-up 的 `0.7143` 進一步掉到 `0.5238`
- 因此 Combined F1 直接跌到 `0.6286`
- 這不只是沒有回到 `0.8333`，甚至比 current production `0.7843`、second-pass `0.7500`、上一輪 follow-up `0.7692` 都更差

### Hygiene Verification

- `validation_failures.jsonl`：存在，共 `51` 筆
- `hygiene_summary.json`：`validation_failure_count = 51`
- failure breakdown：
  - `review_leak`: `42`
  - `stage1_positive_fit`: `5`
  - `qa_source_path_mismatch`: `1`
  - `stage1_direct_negative_conflict`: `1`
  - `bad_request`: `2`
- final exact-literal leak：
  - `latte_review_results.json`：title `0`、topic `0`
  - `latte_fulltext_review_results.json`：title `0`、topic `0`

結論：

- 中途 retry failure 很多，但 final outputs 維持 hygiene clean
- 本次失敗不是因為 final title/topic leak 回來

### Case-Level Inspection

| Case | Family | v1 second-pass | 2409 follow-up | final ablation | 判讀 |
| --- | --- | --- | --- | --- | --- |
| `kourani_process_modelling_with_llm` | publication-form direct negative | `include (senior:4)` | `exclude (senior:2)` | `exclude (senior:2)` | 支持保留 publication-form direct negative |
| `neuberger_data_augment` | publication-form direct negative | `include (junior:5,5)` | `exclude (senior:2)` | `exclude (senior:2)` | 支持保留 publication-form direct negative |
| `grohs2023large` | publication-form direct negative | `include (junior:4,4)` | `exclude (senior:2)` | `exclude (senior:2)` | 支持保留 publication-form direct negative |
| `goossens2023extracting` | recall case / target-boundary over-tightening | `include (junior:4,5)` | `exclude (senior:2)` | `include (senior:5)` | 這次有救回，說明移除 target hardening 對部分 recall case 有效 |
| `qian2020approach` | recall case / target-boundary over-tightening | `include (junior:5,5)` | `exclude (senior:2)` | `exclude (senior:2)` | 沒有救回，表示問題不只來自上一輪 target hardening |
| `vda_extracting_declarative_process` | recall case / target-boundary over-tightening | `include (junior:5,4)` | `exclude (senior:2)` | `maybe (senior:3)` | 有部分回升，但沒有回到 include |
| `neuberger2023beyond` | recall case / target-boundary over-tightening | `include (junior:5,5)` | `exclude (junior:2,2)` | `exclude (junior:2,2)` | 沒有救回 |
| `honkisz2018concept` | sanity / book-chapter not auto-negative | `include (junior:4,5)` | `include (senior:5)` | `exclude (senior:2)` | 這次反而退化，說明單靠 stage2-only ablation 仍不穩 |
| `elallaoui2018automatic` | 非乾淨 stage2-only signal | `exclude (senior:2)` | `not selected` | `not selected` | 不應拿來主導 policy 成敗 |

### Case-level 結論

- publication-form direct negative 這條線本身是有效的，`kourani / neuberger_data_augment / grohs` 都持續被正確收回
- 拿掉上一輪過強的 target/closure wording 後，確實救回了部分 recall family，例如 `goossens`
- 但 `qian / neuberger2023beyond / honkisz` 仍然沒有保住
- `vda_extracting_declarative_process` 只回到 `maybe`，沒有回到 `include`
- 因此這次 final ablation 雖然成功拆開了部分效果，但沒有產生足以把 Combined F1 拉回 `0.8333` 的整體回報

## Stop/Go Decision

### 成功門檻檢查

1. `Combined F1 >= 0.8333`
   - **不成立**
   - 本次 final ablation = `0.6286`

2. final title/topic leak = `0`
   - **成立**
   - final outputs exact-literal clean

### 結論

**Stop。**

這次 final ablation 明確失敗。失敗原因不是 hygiene 不乾淨，而是：

- publication-form direct negative 雖然保住了 precision 端的部分訊號
- 但 recall family 沒有被穩定救回
- 最終 Combined F1 只有 `0.6286`

因此，必須直接宣告：

**在 freeze 條件下，2409 這條 patch 線到此為止。**

## Recommended Final Next Move

- 不再對 `2409` 追加第四輪 stage2 external-policy patch
- 不擴跑 `2511`
- 不擴跑 `qa-only`
- 不擴跑四篇 regression
- 把這次 final ablation 保留為一條失敗但有訊號的實驗分支，用來支持最終結論：
  - publication-form direct negative 本身有效
  - 但在 freeze 條件下，單靠 `2409` 的 stage2-only external policy，無法把 `2409 qa+synthesis` 救回到 `Combined F1 = 0.8333`

如果後續還要再開新方向，那就不應再假裝是同一條 freeze 內 patch 線，而應明確開一條新的 global/shared experiment 線。若之後平行分支變多，改用 `www.k-dense.ai` 管理 workflow，會比在多個對話串重複搬運 handoff 更乾淨。
