# Included-study lists extracted from *author-provided repositories*

This package contains included-study lists that the SR authors published in a public repository (outside the SR PDF/LaTeX manuscript).

## 2401.09244 (Cross-lingual Offensive Language Detection: A Systematic Review...)
- Repo: https://github.com/aggiejiang/crosslingual-offensive-language-survey
- Source file used: `CLTL_surveyed_papers.md` (markdown table, 67 papers)
- Output:
  - `2401.09244_included_from_repo.csv`: full table exported to CSV, plus `bibkey` columns (bibkeys inferred by matching titles to the SR’s own `.bib` entries in the provided TeX source).
  - `2401.09244_included_title_bibkey.csv`: minimal (title, bibkey, confidence).

### Bibkeys
The repo file does not provide BibTeX keys. I therefore **derived** `bibkey` by fuzzy-matching each repo title to the SR's BibTeX database in the TeX source.
- `bibkey_confidence=high` roughly corresponds to title-similarity >= 0.85.
- `low` is 0.75–0.85.
- `none` means no reliable match; the row retains the title only.

## 2405.15604 (Text Generation: A Systematic Literature Review...)
- Repo: https://github.com/jonas-becker/text-generation
- Status: the repo front page references an **output.zip** and PDFs (binary assets). In this environment I can reliably fetch text files from GitHub raw, but binary assets (zip/pdf) cannot be fetched, so I could not extract the 244-paper list from the repo yet.
  - I include this SR in the *investigation report* (see separate file) for follow-up options.

Generated: 2026-02-27
