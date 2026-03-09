# NLP PRISMA Reviews（2023–2026）

本專案彙整 PRISMA 研究的相關文獻資料，包含 PDF、supplementary 檔案、參考文獻資料與處理腳本，目的是可追溯、可重現地管理系統性回顧流程中的文獻證據。

## 資料目錄

- `pdfs/`
  - 所有被納入的 PRISMA 研究 PDF。
- `supplements/`
  - 可直接下載到的補充檔（例如附錄、Table S1/S2），多為被納入研究清單。
- `bib/`
  - 原始 BibTeX 與清理後 BibTeX。
  - `bib/per_SR/`：原始 SR 參考清單（原始筆資料，常只有 `note` 欄位）。
  - `bib/per_SR_cleaned/`：由解析腳本輸出的清理後 BibTeX。
- `manifest.csv`、`manifest.md`
  - 各篇回顧的彙整中繼資料（模型/模型數/包含篇數、證據表位置）。
- `scripts/`
  - 已按職責分層：
  - `scripts/bib/`：BibTeX 清理、oracle 產生與 legacy wrapper。
  - `scripts/metadata/`：tmp refs 建置、驗證、修復與合併。
  - `scripts/fulltext/`：PDF/MD 轉換與全文對齊驗證。
  - `scripts/download/`：下載/擷取（collector、reference PDF downloader、manual retry）。
- `docs/`
  - 腳本與流程文件：`build_reference_oracle_from_bib_notes.md`、`scripts_catalog.md`。

## 專案概述

目前核心任務有兩件事：

1. 從 PDF/補充資料萃取 PRISMA 研究中的 included studies 與參考來源。
2. 把 `bib/per_SR/*.bib` 中多數只有 `note` 的條目，還原為可直接使用的 BibTeX，再產生 `reference_oracle.jsonl`。

## 流程拆分：`per_SR` 全量管線

### Step 1：清理 BibTeX

執行：

```bash
python3 scripts/bib/build_clean_bib_from_notes.py \
  --bib-dir bib/per_SR \
  --out-dir bib/per_SR_cleaned \
  --enable-crossref \
  --confidence-report \
  --confidence-report-all \
  --review-candidates \
  --keep-empty
```

輸出：

- `bib/per_SR_cleaned/<name>.bib`
- `bib/per_SR_cleaned/<name>_parse_report.csv`
- `bib/per_SR_cleaned/per_SR_parse_report_all.csv`
- `bib/per_SR_cleaned/review_candidates_all.csv`

### Step 2：產生 `reference_oracle.jsonl`

執行：

```bash
python3 scripts/bib/build_reference_oracle_from_bib.py \
  --bib-dir bib/per_SR_cleaned \
  --out-dir bib/per_SR_cleaned \
  --name-template '{stem}/reference_oracle.jsonl'
```

輸出：

- `bib/per_SR_cleaned/<name>/reference_oracle.jsonl`

### Step 3：批次抓取 title/abstract（from `reference_oracle.jsonl`）

輸入資料預設來自 `bib/per_SR_cleaned/*/reference_oracle.jsonl`，每篇輸出到
`refs/<paper_name>/metadata/`，固定產生：

- `title_abstracts_metadata.jsonl`
- `title_abstracts_sources.jsonl`
- `title_abstracts_source_trace.jsonl`
- `title_abstracts_full_metadata.jsonl`（預設輸出）

單篇測試（例如 `Chen2026_refs_from_pdf`）：

```bash
python3 scripts/download/collect_title_abstracts_priority.py \
  --input-root bib/per_SR_cleaned \
  --output-root refs \
  --paper-name Chen2026_refs_from_pdf \
  --include-full-metadata true
```

全量批次（預設 full metadata 開啟、embedding/ resume 關閉）：

```bash
python3 scripts/download/collect_title_abstracts_priority.py \
  --input-root bib/per_SR_cleaned \
  --output-root refs
```

## legacy 相容入口（可選）

```bash
python3 scripts/bib/build_reference_oracle_from_bib_notes.py \
  --mode parse-oracle \
  --bib-dir bib/per_SR_cleaned \
  --out-dir bib/per_SR_cleaned \
  --name-template '{stem}/reference_oracle.jsonl'

python3 scripts/bib/build_reference_oracle_from_bib_notes.py \
  --mode parse-bib \
  --bib-dir bib/per_SR \
  --out-dir bib/per_SR_cleaned
```

## 命令對照

### 1) 只處理單一檔案（clean）

```bash
python3 scripts/bib/build_clean_bib_from_notes.py \
  --bib-path bib/per_SR/Chen2026_refs_from_pdf.bib \
  --out-dir bib/per_SR_cleaned
```

### 2) 只處理單一檔案（oracle）

```bash
python3 scripts/bib/build_reference_oracle_from_bib.py \
  --bib-path bib/per_SR_cleaned/Chen2026_refs_from_pdf.bib \
  --out-dir bib/per_SR_cleaned
```

## 中文欄位說明（clean bib）

- `title`：由 note 或 Crossref 補齊的標題。
- `author`：清理後可接受的 BibTeX 作者格式（`Last, First and ...`）。
- `journal`：期刊/會議/機構名稱。
- `volume`、`number`、`pages`：可解析到的卷、期、頁。
- `year`：解析或以 Crossref 為主。
- `doi`：從 note 或 Crossref 取得。
- `url`：DOI URL 或原始來源連結。
- `note`：清理後保留的原始 note 字串。
- `sr_refnum`：原始 SR 參考號（`sr_refnum`）。
- `sr_source`：原始來源識別。

## 注意事項

- `note` 內容若包含大量網址、描述文字或會議資訊，解析仍可能有邊界差異。
- Crossref 解析需要網路，連線失敗時會自動回退本機 note 解析。
- `build_clean_bib_from_notes.py` 預設啟用 Crossref enrichment，可加 `--disable-crossref` 作離線可重現跑法。

## 目前狀態（此資料版本）

- `bib/per_SR_cleaned/` 由 note-only bib 重建，`title` 已可供 `reference_oracle` 走 `title` 優先。
- `per_SR_parse_report_all.csv` 與 `review_candidates_all.csv` 用於檢視重建品質與人工複核候選。
