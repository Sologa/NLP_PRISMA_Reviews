# SR Included-Study Lists (Combined Package)

This zip bundles the outputs from the previous steps into a **single archive**.

## Folder structure

- `inpaper/`
  - Included-study lists that were **explicitly enumerated inside the SR paper itself** (TeX source).
  - For each SR: `*_included.csv` and `*_included.jsonl`.
  - `manifest.json`: counts per SR.
  - `README.md`: extraction notes.

- `repo/`
  - Included-study lists that were **provided via an author repository**.
  - Contains the extracted list file(s) and normalized tables.
  - `README.md` inside this folder includes the corresponding repository URL(s).

- `pending/`
  - `pending_investigation.md`: SRs where an explicit included-study list was not extractable yet (needs further investigation).

## File formats

- CSV columns (typical): `paper_id`, `bibkey`, `title`, plus optional confidence/notes.
- JSONL: one JSON object per included study (stable for downstream pipelines).

