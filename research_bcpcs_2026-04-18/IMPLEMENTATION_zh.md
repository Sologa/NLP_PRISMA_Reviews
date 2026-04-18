# BCPCS 實作細節導讀

這份文件說明目前 `research_bcpcs_2026-04-18/` 裡已經有什麼實作、每支 script 做什麼、輸入輸出在哪裡，以及目前還沒做到什麼。

## 目前不是只有文檔

目前資料夾內有四類東西：

1. 研究設計文檔
2. Machine-readable schemas
3. Prototype scripts
4. 已產生的 validation / dry-run / smoke outputs

也就是說，現在已經有最小可跑通的 scaffold，但還不是完整 BCPCS benchmark。

## 已有的實作檔案

### `src/bcpcs_utils.py`

共用工具函式。

主要功能：

- 找 repo root 和 research root。
- 強制所有輸出只能寫在 `research_bcpcs_2026-04-18/` 裡。
- 讀 JSON / JSONL。
- 寫 JSON / JSONL / Markdown。
- 讀 current `results_manifest.json`。
- 根據 `criteria_stage1/<paper_id>.json` 和 `criteria_stage2/<paper_id>.json` 產生 stub eligibility graph。
- 重算現有 authority metrics。
- 建立 lexical evidence stub，也就是用簡單 token match 產生 smoke-test 用的 evidence span。

重要限制：

- 這不是正式 verifier。
- 這不是正式 retriever。
- 它目前只用於 structural dry-run 和 baseline recheck。

### `src/validate_artifacts.py`

Schema validator。

主要功能：

- 讀三個 JSON schema：
  - `schemas/eligibility_graph.schema.json`
  - `schemas/evidence_ledger.schema.json`
  - `schemas/boundary_atlas.schema.json`
- 驗證 valid sample。
- 驗證 invalid sample 會被拒絕。
- 驗證 dry-run 產生的 eligibility graphs。
- 驗證 dry-run / smoke 產生的 evidence ledger JSONL。

輸出：

- `runs/schema_validation/schema_validation.json`
- `reports/schema_validation.md`

執行方式：

```bash
python3 -B research_bcpcs_2026-04-18/src/validate_artifacts.py
```

### `src/dry_run_loader.py`

Dry-run loader。

主要功能：

- 讀取 current repo authority：
  - `screening/results/results_manifest.json`
  - `criteria_stage1/<paper_id>.json`
  - `criteria_stage2/<paper_id>.json`
  - `refs/<paper_id>/metadata/title_abstracts_metadata.jsonl`
  - `refs/<paper_id>/metadata/title_abstracts_metadata-annotated.jsonl`
  - `cutoff_jsons/<paper_id>.json`
- 對四篇 paper 各自產生 Stage 1 / Stage 2 stub eligibility graph。
- 產生少量 sample Stage 1 evidence ledger rows。

輸出：

- `runs/dry_run_loader/criteria_summary.json`
- `runs/dry_run_loader/stub_graphs/*.eligibility_graph.json`
- `runs/dry_run_loader/sample_stage1_ledger.jsonl`

執行方式：

```bash
python3 -B research_bcpcs_2026-04-18/src/dry_run_loader.py
```

目前結果：

- 讀了 4 篇 repo papers。
- 產生 8 個 stub eligibility graphs。
- 產生 24 筆 sample ledger rows。

### `src/baseline_recheck.py`

Current authority metric rechecker。

主要功能：

- 讀 `screening/results/results_manifest.json`。
- 對每篇 paper 的 Stage 1 / Combined current authority metric artifact 重新計算 metrics。
- 對 combined reports 自動推回 base review results，避免錯把 Stage 2 subset 當全量結果。
- 明確記錄 `2409.13738` current combined F1 是 `0.7500`。

輸出：

- `runs/baseline_recheck/baseline_recheck.json`
- `reports/baseline_recheck.md`

執行方式：

```bash
python3 -B research_bcpcs_2026-04-18/src/baseline_recheck.py
```

目前結果：

- 重算 8 個 authority metric artifacts。
- 全部 match manifest。
- 沒有修改任何 production metric file。

### `src/smoke_experiment.py`

Structural smoke experiment。

主要功能：

- 選 `2409.13738` 和 `2511.13936` 的小 subset。
- 讀 stub eligibility graph。
- 用 lexical stub 產生 evidence ledger。
- 用簡單 graph decision stub 產生 `include` / `exclude` / `route` decisions。

輸出：

- `runs/smoke/smoke_ledger.jsonl`
- `runs/smoke/smoke_decisions.jsonl`
- `runs/smoke/smoke_summary.json`
- `reports/smoke_report.md`
- `reports/results.md`

執行方式：

```bash
python3 -B research_bcpcs_2026-04-18/src/smoke_experiment.py
```

目前結果：

- 6 個 candidates。
- 24 筆 ledger rows。
- 3 個 routed cases。
- 3 個 auto include cases。
- 0 個 auto exclude cases。

重要：這個 smoke run 不能當 performance claim。它只證明 interface 和 artifact flow 可以跑通。

## 已有的 schema 實作

### `schemas/eligibility_graph.schema.json`

定義每個 review / stage 的 typed eligibility claims。

核心欄位：

- `review_id`
- `stage`
- `criterion_source_path`
- `claim_id`
- `claim_text`
- `claim_type`
- `required_status`
- `decision_operator`
- `source_criterion_ids`
- `stage_observability`

### `schemas/evidence_ledger.schema.json`

定義每個 candidate 對每個 claim 的 evidence record。

核心欄位：

- `candidate_key`
- `stage`
- `claim_id`
- `evidence_status`
- `support_spans`
- `refute_spans`
- `missingness_reason`
- `confidence`
- `quote`
- `location`
- `source_path`
- `span_validated`

### `schemas/boundary_atlas.schema.json`

定義 leakage-controlled boundary examples。

核心欄位：

- `review_id`
- `split_scope`
- `archetype_id`
- `archetype_type`
- `allowed_use`
- `source_provenance`
- `contrast_claim_ids`
- `forbidden_eval_keys`

## 目前還沒實作的部分

以下仍是下一階段工作：

- 真正的 criteria-to-claim compiler。
- 真正的 support/refute retriever。
- 真正的 evidence verifier。
- Boundary atlas builder。
- SeniorLead evidence handoff。
- Selective routing calibration。
- Full internal diagnostic benchmark。
- Ablation suite。
- External public benchmark integration。
- Evidence-span human validation workflow。

## 實作邊界

目前所有 scripts 都遵守一個原則：

> 讀 existing repo inputs，但只寫 `research_bcpcs_2026-04-18/`。

因此 prototype 可以安全地探索 BCPCS，而不污染 production workflow。
