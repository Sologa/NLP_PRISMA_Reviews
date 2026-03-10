# Screening Smoke-5 Runbook

## 1) Script 放哪裡

- `scripts/screening/prepare_review_smoke_inputs.py`
- `scripts/screening/run_review_smoke5.sh`
- `scripts/screening/run_review_full_and_f1.sh`
- `scripts/screening/evaluate_review_f1.py`

這兩支都是 screening 用，不在 `scripts/` 根目錄。

## 2) Data 放哪裡（全部在本 repo）

- Source data:
  - `screening/data/source/cads/arxiv_metadata.json`
  - `screening/data/source/cads/criteria.json`
- Smoke data (`top-k=5`):
  - `screening/data/cads_smoke5/arxiv_metadata.top5.json`
  - `screening/data/cads_smoke5/manifest.json`
- Review output:
  - `screening/results/cads_smoke5/latte_review_results.json`

也可直接用既有 paper（不需先手動轉檔）：
- Metadata source: `refs/<PAPER_ID>/metadata/title_abstracts_metadata.jsonl`
- Criteria source: `criteria_jsons/<PAPER_ID>.json`
- Prepared input: `screening/data/<PAPER_ID>_smoke<TOP_K>/`
- Output: `screening/results/<PAPER_ID>_smoke<TOP_K>/`

## 3) 執行

```bash
python3 scripts/screening/prepare_review_smoke_inputs.py --top-k 5
bash scripts/screening/run_review_smoke5.sh
python3 scripts/screening/review_results_debug.py
```

直接跑既有 paper：

```bash
bash scripts/screening/run_review_full_and_f1.sh 2511.13936
```

直接跑既有 paper：

```bash
PAPER_ID=2511.13936 TOP_K=30 \
PIPELINE_PYTHON=/path/to/python \
bash scripts/screening/run_review_smoke5.sh
```

備註：若使用 `gpt-5*`，不要自行傳 `temperature`（API 不支援自訂，使用預設行為）。

若要 debug 漂移，可保留兩次輸出比較：

```bash
RUN_TAG=run1 bash scripts/screening/run_review_smoke5.sh
RUN_TAG=run2 bash scripts/screening/run_review_smoke5.sh
python3 scripts/screening/review_results_debug.py \
  --results screening/results/cads_smoke5/latte_review_results.run2.json \
  --compare screening/results/cads_smoke5/latte_review_results.run1.json
```

若你的預設 Python 沒有安裝套件，可指定：

```bash
PIPELINE_PYTHON=/path/to/python bash scripts/screening/run_review_smoke5.sh
```

## 4) Data 形狀

`arxiv_metadata.top5.json`
- 型別：`list[object]`
- 筆數：`5`
- 常見欄位：保留來源原始 metadata 欄位；流程只要求有 `title` 與 `abstract` 可做 title/abstract screening。

`criteria.json`
  - 核心欄位：`topic`, `topic_definition`, `summary`, `summary_topics`, `inclusion_criteria`, `exclusion_criteria`, `sources`

`prepare_review_smoke_inputs.py` 支援：
- metadata: `.json`（list）或 `.jsonl`
- criteria: `.json`（手動轉好的 structured criteria）

## 5) 快速檢查

```bash
python3 - <<'PY'
import json
from pathlib import Path
m = Path('screening/data/cads_smoke5/arxiv_metadata.top5.json')
c = Path('screening/data/cads_smoke5/criteria.json')
print('metadata_count=', len(json.loads(m.read_text())))
print('criteria_keys=', list(json.loads(c.read_text()).keys()))
PY
```

## 6) 已記錄待辦（先不做）

### A. 固定 criteria 格式與分流判斷

先記錄規格，暫不實作：

1. 先手動把 criteria 整理成固定 structured 格式。
2. 判斷分流：
   - 時間條件：程式 deterministic pre-filter。
   - 非時間條件：交給 agent（包含是否為 secondary research）。
3. 手動整理結果需先由使用者驗收，再切換流程。

### B. 保留雙 setting + args 控制

先記錄規格，暫不實作：

1. 保留兩種 metadata 餵法：
   - `fields`（結構化欄位）
   - `raw_text`（metadata 整串字串）
2. 保留兩種 criteria 路徑：
   - `structured_split`
   - `legacy_raw`
3. 後續以 args 控制並做實驗比較（A/B）。

建議預留參數（尚未實作）：

```bash
--metadata-mode fields|raw_text
--criteria-mode structured_split|legacy_raw
--experiment-tag <name>
```
