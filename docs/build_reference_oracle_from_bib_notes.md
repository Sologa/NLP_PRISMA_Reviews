# `per_SR` BibTeX 流程重構說明（2026）

## 1) 目標

把之前 `scripts/bib/build_reference_oracle_from_bib_notes.py` 的「note parse」與 `reference_oracle` 輸出拆成兩個獨立腳本：

1. `scripts/bib/build_clean_bib_from_notes.py`：從 `note` 重建 `bib/per_SR_cleaned/*.bib`（含完整 `title`）。
2. `scripts/bib/build_reference_oracle_from_bib.py`：從清理後 `.bib` 產生 `reference_oracle.jsonl`。

`scripts/bib/build_reference_oracle_from_bib_notes.py` 保留為薄版相容入口，逐步導向新腳本。

## 2) 兩條主流程

### A. Clean pipeline（建議）

```bash
python3 scripts/bib/build_clean_bib_from_notes.py \
  --bib-dir bib/per_SR \
  --out-dir bib/per_SR_cleaned \
  --confidence-report \
  --confidence-report-all \
  --review-candidates \
  --keep-empty
```

輸出：

- `bib/per_SR_cleaned/<name>.bib`
- `bib/per_SR_cleaned/<name>_parse_report.csv`（`--confidence-report` 時）
- `bib/per_SR_cleaned/per_SR_parse_report_all.csv`（`--confidence-report-all` 時）
- `bib/per_SR_cleaned/review_candidates_all.csv`（`--review-candidates` 時）

交互參數：

- `--disable-crossref`：關閉 Crossref enrich（預設開啟）
- `--enable-crossref`：相容旗標，行為同預設（保留於舊命令兼容）
- `--crossref-cache`：快取路徑

### B. Oracle pipeline（建議）

```bash
python3 scripts/bib/build_reference_oracle_from_bib.py \
  --bib-dir bib/per_SR_cleaned \
  --out-dir bib/per_SR_cleaned \
  --name-template '{stem}/reference_oracle.jsonl'
```

輸出：每個輸入 `.bib` 一個 `reference_oracle.jsonl`，欄位固定為下游相容 schema：

- `key`, `entry_type`, `query_title`, `normalized_title`, `matched`, `match_score`, `arxiv`, `sources`, `raw`
- `raw` 保留 `{"local": <原 raw_fields>}`
- `query_title` 優先取 `title`，若缺值再 fallback 到 `note` 抽取

## 3) `scripts/bib/build_reference_oracle_from_bib_notes.py`（相容入口）

保留舊 CLI：`--mode parse-bib | parse-oracle`，但行為只做參數轉接：

- `--mode parse-bib` => 呼叫 `build_clean_bib_from_notes.py`
- `--mode parse-oracle` => 呼叫 `build_reference_oracle_from_bib.py`
- `--emit-bib`、`--out-jsonl` 僅做 legacy 相容，不建議新流程使用

## 4) 兼容建議

請以新入口分開運行，不要把 `clean` 與 `oracle` 混寫於單一檔案：

1. `build_clean_bib_from_notes.py` 先處理 `bib/per_SR`。
2. `build_reference_oracle_from_bib.py` 再處理 `bib/per_SR_cleaned`。

## 5) 重跑命令（對應你要求）

```bash
python3 scripts/bib/build_clean_bib_from_notes.py \
  --bib-dir bib/per_SR \
  --out-dir bib/per_SR_cleaned \
  --enable-crossref \
  --confidence-report \
  --confidence-report-all \
  --review-candidates \
  --keep-empty

python3 scripts/bib/build_reference_oracle_from_bib.py \
  --bib-dir bib/per_SR_cleaned \
  --out-dir bib/per_SR_cleaned \
  --name-template '{stem}/reference_oracle.jsonl'
```
