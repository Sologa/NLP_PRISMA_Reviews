# 雙欄 academic PDF 轉 LLM 輸入研究報告

日期：2026-04-23  
報告路徑：`/Users/xjp/Desktop/NLP_PRISMA_Reviews/docs/deep_research/pdf_double_column_extraction_2026-04-23/REPORT_zh.md`  
範圍：雙欄 academic PDF 的文字抽取、reading order、layout-aware parser、OCR fallback，並對應本 repo 現行 `mds/*.md` → stage-2 inline review 流程。

## 0. 結論先講

如果 PDF 是 **born-digital 的雙欄學術論文**，預設不應該直接上 full-page OCR。真正要處理的是：

1. 先處理 **reading order / column order**
2. 再把結果序列化成給 LLM 的 text / markdown
3. OCR 只留給掃描件、壞掉的 text layer、或原生抽取明顯失真時

對這個 repo 而言，最小風險的插入點不是 reviewer prompt，而是 **上游 `refs/<paper_id>/mds/*.md` 的生成層**。也就是說，先把 PDF 轉成更乾淨的 `mds/<key>.md`，再沿用現在 stage-2 的 `reference cut + 24k/12k` 流程。

## 1. 目前 repo 的真實接點

目前 production fulltext 流程不是讀 PDF，而是直接讀 `refs/<paper_id>/mds/<key>.md`：

- `scripts/screening/run_review_smoke5.sh`
- `scripts/screening/vendor/scripts/topic_pipeline.py`
- `scripts/screening/vendor/src/pipelines/topic_pipeline.py`

關鍵事實：

- `run_latte_fulltext_review()` 會推導或接受 `fulltext_root`，然後在 `refs/<paper_id>/mds/` 下做 `key.md` lookup。
- 目前 production 是 `inline` only；`file_search` / `hybrid` 尚未實作。
- 讀到的 fulltext 會再經過：
  - `_normalize_fulltext_text()`
  - `_truncate_fulltext_before_references()`
  - `_apply_head_tail_limit()`
- 目前 char budget 預設是 `24000` head + `12000` tail。

所以如果要加「比較會處理雙欄 PDF」的 backend，最自然的路徑是：

- `首選`：改善 `mds/*.md` 的生成流程
- `次選`：把 `topic_pipeline.py` 內 `read_text(...)` 的地方改成可 fallback 到 PDF parser

## 2. 本地驗證：雙欄問題不是抽字而已，是 reading order 問題

我用 repo 內的 [`refs/2303.13365/2303.13365.pdf`](/Users/xjp/Desktop/NLP_PRISMA_Reviews/refs/2303.13365/2303.13365.pdf) 做了本地抽樣。

同一頁雙欄內容的觀察：

- `pdftotext` 預設模式：會把左右欄壓成單一路徑，欄位之間的切換不穩。
- `pdftotext -layout`：會保留左右欄的空間結構，比較容易後續自己做欄位切分。
- `PyMuPDF page.get_text()`：預設仍可能按 page content stream 順序吐字。
- `PyMuPDF page.get_text(sort=True)`：會按 bbox 排序，至少把左右欄分開顯示出來。
- `PyMuPDF get_text("blocks")`：可以直接拿到左右欄 block bbox，適合自己做 column-aware 重建。

本地重點不是哪個工具「完美」，而是：

- plain text extraction 不等於正確閱讀順序
- `bbox-aware extraction` 才是可以做工程控制的基礎

## 3. 研究結果：幾條主路線

### A. 快速文字層方案：`pdftotext` / `PyMuPDF` / `pdfplumber` / `pdfminer.six`

這一類不是 parser-first，而是「先拿到 text + coordinates，再自己修 reading order」。

適合：

- born-digital PDF
- 版面規律
- 你想自己控制 pipeline
- 想把依賴和 runtime 壓低

不適合：

- 複雜表格 / captions / sidebar / appendix-heavy 頁面
- 掃描件
- 你希望直接得到高品質 markdown

實務上最有價值的兩個 low-level baseline：

- `pdftotext -layout -nodiag`
- `PyMuPDF get_text("blocks", sort=True)` 再自己做欄位重建

如果只是要一個便宜 baseline，`pdftotext -layout` 很夠用；如果要可控性，`PyMuPDF` 比較好。

### B. parser-first 路線：`Marker` / `Docling` / `GROBID` / `MinerU`

這一類的核心不是「抽字」，而是「先做 layout understanding，再輸出 markdown / JSON / TEI」。

#### `Marker`

最像「直接拿來餵 LLM」的工具。官方 README 明確把 academic PDF、multi-column、markdown/json 當主場景。

我的判讀：

- 如果你的首要目標是 **快點得到 LLM-ready markdown**
- 而且 PDF 多半是 born-digital academic papers

那它是最值得先試的第一順位。

風險：

- 極複雜 layout 仍會失敗
- 需要 PyTorch
- 若要更高精度，常會進一步打開 `--use_llm`

#### `Docling`

Docling 的優點是文件結構表示比較完整，且支援 `DoclingDocument` / JSON / DocTags。

我的判讀：

- 如果你願意把 **JSON / DocTags** 當 source of truth，而不是只信 markdown
- 它會比單純抽 text 更穩

但官方 issue 已經有 multi-column crossing 的案例，所以不應把「Docling 產出的 markdown」直接當無條件真值。

#### `GROBID`

GROBID 仍然是 scholarly PDF 專用 parser 裡最有學術結構味道的一條路。它強項不是 markdown，而是：

- metadata
- section structure
- references
- TEI

我的判讀：

- 如果你在乎引用、章節、作者資訊、bibliography fidelity
- 並且可以接受 `TEI-first`

GROBID 很強。

但如果你的需求是「今天就想把 PDF 變成好用 markdown 給 LLM」，它沒有 Marker 那麼直接。

#### `MinerU`

MinerU 對 layout、formula、table、reading-order-sorted JSON 的 ambition 很高，官方 README 也明確主打 multi-column。

我的判讀：

- layout-heavy / formula-heavy / multimodal academic pages，有很高上限
- 但部署面和 backend surface 較重
- 官方自己也建議先用 sample 測

所以它比較像「高上限但 operational variance 較大」的選項。

### C. OCR / vision-heavy fallback：`Nougat` / `Surya` / `PaddleOCR PP-StructureV3` / `OCRmyPDF`

這條線不該是 born-digital PDF 的預設，但對 hard cases 很重要。

#### `Nougat`

專門為 academic PDF 做 page-to-markdown。優點是：

- 直接輸出 `.mmd`
- 對公式和學術頁面很友好

缺點是：

- 不是 bbox-first
- 有 real-world table / page failure issues
- 比較適合作為 academic hard cases 的 fallback，而不是所有 PDF 的統一路徑

#### `Surya` / `PaddleOCR PP-StructureV3`

比較像 building blocks / structured parser service：

- layout boxes
- reading order
- table recognition
- formula OCR
- JSON / markdown

如果你要的是「可觀察、可視化、可做 region-level chunking」的 pipeline，它們很有價值。

#### `OCRmyPDF` / `Tesseract`

最適合：

- 掃描 PDF
- image-only page
- 壞掉的 text layer
- searchable PDF

最不適合：

- born-digital academic paper 的主要 parser
- 需要數學式 / 表格 / markdown fidelity 的場景

## 4. 這次研究的總結排序

如果目標是 **born-digital 雙欄 research PDF → LLM input**，我建議的實測順序是：

1. `Marker`
2. `Docling`
3. `GROBID`
4. `MinerU`
5. `PyMuPDF` 自己做 bbox/column reconstruction
6. `Nougat` / `Surya` / `PP-StructureV3` 作為 hard-case fallback
7. `OCRmyPDF` / `Tesseract` 只留給 scan / broken text layer

排序理由：

- `Marker`：最 markdown-first、最接近 LLM ingestion 目標
- `Docling`：結構表示佳，但最好別只信 markdown
- `GROBID`：最 scholarly-structured，但 TEI-first
- `MinerU`：高上限，但 operational surface 較大
- `PyMuPDF`：如果你要自己掌控每一步，是最務實的 low-level 路線

## 5. 對本 repo 的實際建議

### 建議 A：不要先改 reviewer，先改 `mds` 生成層

目前 reviewer 吃的是 `mds/*.md`。所以最小風險方案是新增一條更好的 PDF→MD backend，讓 stage 2 不必改 prompt / routing。

建議做法：

- 新增一個上游 builder，例如 `scripts/fulltext/build_mds_from_pdf_layout.py`
- 輸入：`ref_pdfs/<paper_id>/<key>.pdf` 或既有 PDF 根目錄
- 輸出：`refs/<paper_id>/mds/<key>.md`
- backend 先支援：
  - `marker`
  - `docling`
  - `pymupdf_blocks`
  - `pdftotext_layout`

然後把目前 stage-2 既有的：

- reference cut
- head/tail limit
- fulltext gate

全部保留不動。

### 建議 B：先做兩層 fallback，而不是一次賭一個 parser

實務建議：

1. 先跑 `Marker`
2. 如果失敗或品質差，再退到 `PyMuPDF blocks`
3. 如果發現是 scan / bad OCR layer，再走 `Nougat` 或 `PP-StructureV3`

這比「全 corpus 一次換單一 parser」穩很多。

### 建議 C：把 `bbox-aware intermediate` 留下來

即使最後輸出是 markdown，也建議保留中間 artifact：

- page number
- block bbox
- column id
- parser backend
- extraction warnings

原因很直接：之後如果 stage-2 又出現 evidence interpretation 爭議，你可以回頭看是不是 parser 把欄位順序搞壞了，而不是 reviewer 真讀錯。

## 6. 如果現在就要一個務實答案

最務實版本如下：

- born-digital 雙欄 academic PDF：先不要 OCR
- 先試 `Marker`
- 若不想引入大 parser，至少改成 `PyMuPDF blocks + explicit column reconstruction`
- 對這個 repo，先把結果落到 `refs/<paper_id>/mds/*.md`
- 讓當前 stage-2 inline review 繼續吃 `mds`

一句話總結：

**雙欄 PDF 的核心不是把字抽出來，而是把正確的閱讀順序和版面邊界先處理好；對本 repo，最小成本且最穩的做法是把這件事放在 `mds` 生成層。**

## 7. 來源清單

本報告綜合了：

- repo 內現行 fulltext 路徑與本地 PDF 實測
- 官方文件 / 官方 repo / 官方 issue
- GitHub 上可重現的 maintainer 建議與實作討論

主要外部來源：

- Poppler `pdftotext` man page
- PyMuPDF docs / discussions / utilities
- pdfminer.six docs / issues
- pdfplumber README / issues / discussions
- GROBID docs / repo / `pdfalto`
- Docling docs / repo / issues
- Marker repo
- MinerU repo / issues
- Nougat repo / paper / issues
- Surya repo
- PaddleOCR PP-StructureV3 docs / issues
- OCRmyPDF docs / issues
