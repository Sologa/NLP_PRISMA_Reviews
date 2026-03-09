# `scripts/` 檔案總覽與使用手冊（2026-03-05）

這份文件覆蓋 `scripts/` 目錄下的「手寫可維護檔案」：

- `scripts/bib/*.py`
- `scripts/metadata/*.py`
- `scripts/metadata/*.sh`
- `scripts/fulltext/*.py`
- `scripts/download/*.py`
- `scripts/download/*.sh`
- `scripts/lib/*.py`

不含自動生成或暫存檔：

- `scripts/__pycache__/`
- `scripts/lib/__pycache__/`
- `scripts/.DS_Store`

## 0) 結構調整與文件覆蓋現況

- 下載相關腳本已集中到 `scripts/download/`，避免與清理/修復腳本混在同層。
- 目前目錄內 CLI 腳本（不含 `scripts/lib/`）共 19 支；本文件已全數收錄路徑。
- 其中 8 支仍待補「完整章節說明」：
  - `scripts/bib/extract_inpaper_from_tex_appendix.py`
  - `scripts/metadata/finalize_missing_metadata_manual.py`
  - `scripts/download/manual_match_single_sr.py`
  - `scripts/download/manual_single_round_retry.py`
  - `scripts/fulltext/manual_verify_inpaper_title_abstract.py`
  - `scripts/fulltext/postprocess_md_zip_single_sr.py`
  - `scripts/metadata/repair_metadata_quality.py`
  - `scripts/fulltext/verify_pdf_metadata_alignment.py`

## 1) CLI 腳本（可直接執行）

### `scripts/bib/build_clean_bib_from_notes.py`

- 目的：把 `bib/per_SR/*.bib` 中偏 `note` 型條目清理成可用 BibTeX。
- 輸入：`--bib-path` 或 `--bib-dir`。
- 輸出：清理後 `.bib`、解析報表 CSV（依 flags）。
- 常用指令：

```bash
python3 scripts/bib/build_clean_bib_from_notes.py \
  --bib-dir bib/per_SR \
  --out-dir bib/per_SR_cleaned \
  --confidence-report \
  --confidence-report-all \
  --review-candidates
```

### `scripts/bib/build_reference_oracle_from_bib.py`

- 目的：從清理後 BibTeX 產生 `reference_oracle.jsonl`。
- 輸入：`--bib-path` 或 `--bib-dir`（通常是 `bib/per_SR_cleaned`）。
- 輸出：`<paper>/reference_oracle.jsonl`。
- 常用指令：

```bash
python3 scripts/bib/build_reference_oracle_from_bib.py \
  --bib-dir bib/per_SR_cleaned \
  --out-dir bib/per_SR_cleaned \
  --name-template '{stem}/reference_oracle.jsonl'
```

### `scripts/bib/build_reference_oracle_from_bib_notes.py`（legacy wrapper）

- 目的：相容舊命令；內部轉接到 `build_clean_bib_from_notes.py` 與 `build_reference_oracle_from_bib.py`。
- 輸入：同舊版旗標（`--mode parse-bib|parse-oracle`）。
- 輸出：取決於 mode（clean bib 或 oracle）。
- 建議：新流程優先直接用兩支新腳本，不再依賴此 wrapper。

### `scripts/download/collect_title_abstracts_priority.py`

- 目的：依來源優先序回填 title/abstract 與來源追蹤。
- 輸入：`reference_oracle.jsonl`（預設在 `bib/per_SR_cleaned/<paper>/`）。
- 輸出（每篇）：`title_abstracts_metadata.jsonl`、`title_abstracts_sources.jsonl`、`title_abstracts_source_trace.jsonl`、`title_abstracts_full_metadata.jsonl`（`--include-full-metadata true` 時）。
- 常用指令：

```bash
python3 scripts/download/collect_title_abstracts_priority.py \
  --input-root bib/per_SR_cleaned \
  --output-root refs
```

### `scripts/metadata/build_tmp_refs_from_missing.py`

- 目的：把 `refs/` 中缺值項目抽成 `tmp_refs/` 的最小修補集合。
- 輸入：`refs/*/metadata/title_abstracts_metadata.jsonl` + `bib/per_SR_cleaned/*/reference_oracle.jsonl`。
- 輸出：`tmp_refs/<paper>/reference_oracle.jsonl`、`missing_manifest.jsonl`。
- 常用指令：

```bash
python3 scripts/metadata/build_tmp_refs_from_missing.py \
  --refs-root refs \
  --oracle-root bib/per_SR_cleaned \
  --tmp-root tmp_refs
```

### `scripts/metadata/validate_tmp_refs.py`

- 目的：檢查 `tmp_refs` 回填結果是否能安全併回 `refs`。
- 輸入：`tmp_refs/` 及其 manifest。
- 輸出：JSON/Markdown 驗證報告（通常放 `issues/`）。
- 常用指令：

```bash
python3 scripts/metadata/validate_tmp_refs.py \
  --tmp-root tmp_refs \
  --output-json issues/validate_tmp_refs.json \
  --output-markdown issues/validate_tmp_refs.md
```

### `scripts/metadata/merge_tmp_refs_back.py`

- 目的：把 `tmp_refs` 修復後 metadata 安全合併回 `refs`（支援 dry-run/backup）。
- 輸入：`refs/`、`tmp_refs/`、`missing_manifest.jsonl`。
- 輸出：更新後 `refs/*/metadata/*.jsonl` + 合併報告 + 備份。
- 常用指令（先 dry-run）：

```bash
python3 scripts/metadata/merge_tmp_refs_back.py \
  --refs-root refs \
  --tmp-root tmp_refs \
  --dry-run \
  --report-json issues/metadata_repair_report.json \
  --report-markdown issues/metadata_repair_report.md
```

### `scripts/metadata/run_metadata_repair_pipeline.sh`

- 目的：串起 tmp 建置、收集、驗證、合併的一鍵流程。
- 輸入：`refs/`、`bib/per_SR_cleaned/`，可用 `--paper-id` 限定單篇。
- 輸出：`issues/` 下驗證與修復報告；`--apply` 時會實際回寫 `refs`。
- 常用指令：

```bash
bash scripts/metadata/run_metadata_repair_pipeline.sh --paper-id 2405.15604
```

### `scripts/download/run_tmp_refs_collect.sh`

- 目的：批次對 `tmp_refs/*/reference_oracle.jsonl` 跑 collector。
- 輸入：`tmp_refs` 目錄。
- 輸出：`tmp_refs/*/metadata/*.jsonl`。
- 常用指令：

```bash
bash scripts/download/run_tmp_refs_collect.sh \
  --input-root tmp_refs \
  --output-root tmp_refs
```

### `scripts/download/download_refs_reference_pdfs.py`

- 目的：依 `refs/*/metadata/title_abstracts_full_metadata.jsonl` 批次抓 reference PDF。
- 輸入：`refs/` metadata。
- 輸出：下載 PDF（預設 `ref_pdfs/`）與 `issues/ref_pdf_download/` 報告。
- 常用指令：

```bash
python3 scripts/download/download_refs_reference_pdfs.py \
  --refs-root refs \
  --output-root ref_pdfs
```

### `scripts/fulltext/convert_arxiv_pdf_to_md.py`

- 目的：把 arXiv ID 命名的 PDF 轉成 Markdown 文字檔。
- 輸入：`--pdf-dir`（預設 `pdfs/`）。
- 輸出：`--output-dir`（預設 `mds/`）的 `.md`。
- 常用指令：

```bash
python3 scripts/fulltext/convert_arxiv_pdf_to_md.py \
  --pdf-dir pdfs \
  --output-dir mds
```

## 2) `scripts/lib/` 共用模組

### `scripts/lib/bib_parser.py`

- 角色：BibTeX 解析工具（供 clean/oracle 腳本共用）。

### `scripts/lib/note_parser.py`

- 角色：從 `note` 欄位抽取 DOI、title、author 等啟發式解析。

### `scripts/lib/crossref_client.py`

- 角色：Crossref 查詢與本機 cache。

### `scripts/lib/oracle_writer.py`

- 角色：把 parsed Bib entry 組成 `reference_oracle` schema。

### `scripts/lib/title_normalizer.py`

- 角色：title 正規化（去格式噪音、比對前清理）。

### `scripts/lib/__init__.py`

- 角色：套件化入口（匯出共用 helpers）。

## 3) 推薦執行順序（主流程）

```bash
python3 scripts/bib/build_clean_bib_from_notes.py --bib-dir bib/per_SR --out-dir bib/per_SR_cleaned
python3 scripts/bib/build_reference_oracle_from_bib.py --bib-dir bib/per_SR_cleaned --out-dir bib/per_SR_cleaned --name-template '{stem}/reference_oracle.jsonl'
python3 scripts/download/collect_title_abstracts_priority.py --input-root bib/per_SR_cleaned --output-root refs
```

## 4) 維護規範（之後新增腳本時）

- 新增腳本時，同步更新本檔與 `README.md`。
- 每支 CLI 腳本需保留 module docstring（用途）、`--help` 與至少一個可複製執行的指令範例。
- 若輸出會回寫 `refs/`，需先有 dry-run 或備份機制。
