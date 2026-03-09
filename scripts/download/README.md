# scripts/download

本資料夾集中放置「需要連網下載/抓取資料」的腳本，避免與本地清理/修復腳本混在 `scripts/` 根目錄。

## 腳本

- `collect_title_abstracts_priority.py`
  - 依來源優先序抓取並回填 `title/abstract` metadata。
- `run_tmp_refs_collect.sh`
  - 批次對 `tmp_refs/*/reference_oracle.jsonl` 執行 collector。
- `download_refs_reference_pdfs.py`
  - 依 `title_abstracts_full_metadata.jsonl` 批次下載 reference PDFs。
- `manual_match_single_sr.py`
  - 針對單篇 SR 的失敗項目進行手動候選 URL 比對與下載補救。
- `manual_single_round_retry.py`
  - 對單回合失敗 key 進行 retry 與來源 API 候選補抓。

## 常用命令

```bash
python3 scripts/download/collect_title_abstracts_priority.py --input-root bib/per_SR_cleaned --output-root refs
bash scripts/download/run_tmp_refs_collect.sh --input-root tmp_refs --output-root tmp_refs
python3 scripts/download/download_refs_reference_pdfs.py --refs-root refs --output-root ref_pdfs
```
