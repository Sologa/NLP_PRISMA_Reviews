# Regeneration notes: 為何這次不是直接沿用 `criteria_mds/`

## 原則

這一輪資產重生只把 `criteria_mds/` 當 **形式模板**，不把它當 current production semantics 的來源。
真正的 source of truth 是 current active `criteria_stage1/*.json` 與 `criteria_stage2/*.json`。

## `2409.13738`

### 沒有沿用的 historical 風險

- `criteria_mds/2409.13738.md` 的 output examples 會把 `labels` 和 process model / BPMN / Petri net 放在很靠近的位置。
- current active stage-split criteria 明確把 label-only family 視為非目標家族的一部分。
- 因此新 spec 把 `source_object`、`target_object`、`non_target_task_signal` 分開抽，避免 question wording 先污染 decision boundary。

### 重生後的修正

- `labels` 不再被放在正向 output examples 中
- `prediction` / `matching` / `redesign` / `text-from-process generation` 全部被移到反證欄位
- Stage 1 不提前硬判 Stage 2 metadata gate

## `2511.13936`

### 沒有沿用的 historical 風險

- `criteria_mds/2511.13936.md` 混入了 2020+、arXiv citation cutoff、venue/source filter 等 retrieval logic
- 同一份 historical 文件對 multimodal/audio boundary 的表述存在 drift：有時寫 audio 為 core modality，有時又寫只要 includes audio content 即可
- current active stage-split criteria 只保留 source-faithful screening boundary：preference learning + audio domain + not survey/review + evaluation-only exclusion

### 重生後的修正

- 2020+ / citation gate / arXiv gate 全部移出 screening QA
- `multimodal_with_audio` 被單獨抽成 evidence field，避免在問題裡偷塞更嚴格的 “core modality” 門檻
- `learning_vs_evaluation_role`、`rating_to_preference_conversion`、`rl_loop_for_audio_model` 被拆成獨立欄位，避免把多個邊界混在同一題

## 為什麼 metadata spec 要拆出來

這不是單純格式喜好，而是為了避免後續 agent 把：
- retrieval policy
- metadata convenience
- content eligibility
三種不同來源的訊號混成同一個 decision layer。

拆開後，才比較容易做到：

`stage-specific QA / extraction -> evidence synthesis -> criteria evaluation`
