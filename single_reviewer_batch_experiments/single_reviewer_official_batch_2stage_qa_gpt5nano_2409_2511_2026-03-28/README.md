# 單審查者官方 Batch 2-Stage QA（`gpt-5-nano`）

這個 bundle 是隔離的 experiment-only 實作。

## 核心定義

- current-state-aligned `Stage 1 QA -> synthesis -> eval -> Stage 2 QA -> synthesis -> eval`
- 單一 reviewer lane，但允許多個依賴式 official Batch phase
- cutoff-first
- 不修改 production criteria、runtime prompts、shared helper
- 測試 paper 固定為 `2409.13738` 與 `2511.13936`

## 輸入來源

- metadata：`refs/<paper_id>/metadata/title_abstracts_metadata.jsonl`
- gold：`refs/<paper_id>/metadata/title_abstracts_metadata-annotated.jsonl`
- fulltext：`refs/<paper_id>/mds/*.md`
- Stage 1 criteria：`criteria_stage1/<paper_id>.json`
- Stage 2 criteria：`criteria_stage2/<paper_id>.json`
- cutoff：`cutoff_jsons/<paper_id>.json`

## 驗證

```bash
./.venv/bin/python single_reviewer_batch_experiments/single_reviewer_official_batch_2stage_qa_gpt5nano_2409_2511_2026-03-28/tools/validate_bundle.py \
  --check-model \
  --check-serialization
```

## Smoke

```bash
./.venv/bin/python single_reviewer_batch_experiments/single_reviewer_official_batch_2stage_qa_gpt5nano_2409_2511_2026-03-28/tools/run_experiment.py \
  --mode run \
  --phase all \
  --run-id 20260328_smoke_gpt5nano_low_2stageqa_2409_2511 \
  --papers 2409.13738 2511.13936 \
  --candidate-keys-file single_reviewer_batch_experiments/single_reviewer_official_batch_2stage_qa_gpt5nano_2409_2511_2026-03-28/smoke/smoke_candidates.json \
  --reasoning-effort low
```

## Full

```bash
./.venv/bin/python single_reviewer_batch_experiments/single_reviewer_official_batch_2stage_qa_gpt5nano_2409_2511_2026-03-28/tools/run_experiment.py \
  --mode run \
  --phase all \
  --run-id 20260328_full_gpt5nano_low_2stageqa_2409_2511 \
  --papers 2409.13738 2511.13936 \
  --reasoning-effort low
```

## 單一 phase

```bash
./.venv/bin/python single_reviewer_batch_experiments/single_reviewer_official_batch_2stage_qa_gpt5nano_2409_2511_2026-03-28/tools/run_experiment.py \
  --mode submit \
  --phase stage1_qa \
  --run-id <run_id> \
  --papers 2409.13738 \
  --reasoning-effort low
```

```bash
./.venv/bin/python single_reviewer_batch_experiments/single_reviewer_official_batch_2stage_qa_gpt5nano_2409_2511_2026-03-28/tools/run_experiment.py \
  --mode collect \
  --phase stage1_qa \
  --run-id <run_id> \
  --papers 2409.13738
```
