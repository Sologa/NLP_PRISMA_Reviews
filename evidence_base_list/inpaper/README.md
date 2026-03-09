# Included-study lists extracted from *within the SR paper* (TeX source)

This package contains **(title, bibkey)** pairs for SR papers whose TeX source contains a **clear included-study list** (e.g., an appendix long table, an explicit "References for Works Included" appendix, or summary tables that enumerate exactly the included corpus).

## Files
- `2307.05527_included.csv` etc: one CSV per SR, columns:
  - `bibkey`: BibTeX citation key (may be empty for a few items if the SR lists a full citation but the key can't be confidently matched).
  - `title`: title from the SR's `.bib` (or from the SR appendix list if unmatched).
  - (optional) `match_confidence`, `score`: only for SRs where bibkey was inferred by title-matching.
  - `method`: how the list was extracted.

- `*_included.jsonl`: same content as CSV, but JSON Lines.
- `manifest.json`: counts per SR.

## Notes / caveats
- **2307.05527**: the included list is an appendix enumerating *full citations* (171 items). Bibkeys were recovered by matching item titles to the SR's BibTeX entries; a small number remain unmatched or low-confidence.
- **2601.19926**: appendix indicates 337 studies; extracted unique bibkeys = 336 (likely due to one non-cited entry or a duplicate in the table).

Generated: 2026-02-27
