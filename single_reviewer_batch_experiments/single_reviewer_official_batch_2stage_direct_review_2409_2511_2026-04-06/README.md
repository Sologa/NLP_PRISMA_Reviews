# 單審查者官方 Batch 兩階段直審基線

這個 bundle 是隔離的 experiment-only 實作，用來修正 single reviewer baseline 為真正的 two-stage direct review。

## 核心定義

- 單一審查者
- 官方 Batch API
- 兩階段直審
- cutoff-first
- 不修改 production prompt source
- 不修改 production criteria files

## 輸入來源

- metadata：`refs/<paper_id>/metadata/title_abstracts_metadata.jsonl`
- gold：`refs/<paper_id>/metadata/title_abstracts_metadata-annotated.jsonl`
- fulltext：`refs/<paper_id>/mds/*.md`
- Stage 1 criteria：`criteria_stage1/<paper_id>.json`
- Stage 2 criteria：`criteria_stage2/<paper_id>.json`
- cutoff：`cutoff_jsons/<paper_id>.json`

`--phase all` 僅支援 `--mode run`。因為 `stage2_review` 依賴 `stage1_review` collect 後的 gating 結果；若要分段執行，請明確指定 `stage1_review` 或 `stage2_review`。

## 指令

驗證 bundle：

```bash
./.venv/bin/python single_reviewer_batch_experiments/single_reviewer_official_batch_2stage_direct_review_2409_2511_2026-04-06/tools/validate_bundle.py
```

驗證 bundle、model 與 request serialization：

```bash
./.venv/bin/python single_reviewer_batch_experiments/single_reviewer_official_batch_2stage_direct_review_2409_2511_2026-04-06/tools/validate_bundle.py \
  --check-model \
  --check-serialization
```

小型一鍵冒煙：

```bash
./.venv/bin/python single_reviewer_batch_experiments/single_reviewer_official_batch_2stage_direct_review_2409_2511_2026-04-06/tools/run_experiment.py \
  --mode run \
  --phase all \
  --papers 2409.13738 2511.13936 \
  --candidate-keys-file single_reviewer_batch_experiments/single_reviewer_official_batch_2stage_direct_review_2409_2511_2026-04-06/smoke/smoke_candidates.json \
  --reasoning-effort low
```

完整 `gpt-5-mini low`：

```bash
./.venv/bin/python single_reviewer_batch_experiments/single_reviewer_official_batch_2stage_direct_review_2409_2511_2026-04-06/tools/run_experiment.py \
  --mode run \
  --phase all \
  --run-id 20260406_full_gpt5mini_low_2stagedirect_2409_2511 \
  --papers 2409.13738 2511.13936 \
  --reasoning-effort low
```

完整 `gpt-5 low`：

```bash
./.venv/bin/python single_reviewer_batch_experiments/single_reviewer_official_batch_2stage_direct_review_2409_2511_2026-04-06/tools/run_experiment.py \
  --mode run \
  --phase all \
  --run-id 20260406_full_gpt5_low_2stagedirect_2409_2511 \
  --model gpt-5 \
  --papers 2409.13738 2511.13936 \
  --reasoning-effort low
```
