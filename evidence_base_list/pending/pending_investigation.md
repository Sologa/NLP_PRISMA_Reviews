# Follow-up investigation report: SRs without extractable included-study lists (yet)

Generated: 2026-02-27

This report lists SRs where an **explicit included-study list** (with bibkeys) was not extractable via the provided TeX sources or via an author repo text file.

## Already extracted

- In-paper explicit lists: 2601.19926, 2511.13936, 2509.11446, 2409.13738, 2307.05527

- Repo-provided list: 2401.09244 (GitHub table)


## Pending / needs additional work

### 2303.13365
- The provided file `2303.13365.tar.gz` is actually a **PDF**, not a TeX source archive. Need the real source (or parse the PDF references + any appendix tables) to recover bibkeys.

### 2306.12834
- Contains synthesis tables (models/preprocessing/tools) with many citations, but no dedicated included-study enumeration. Extracting evidence base would require disambiguation rules + manual/LLM-assisted classification.

### 2310.07264
- No explicit included-paper list found in TeX (no appendix section listing papers). Likely would require: (a) PDF table extraction if tables list studies; or (b) request replication package from authors.

### 2312.05172
- No explicit included-paper list; TeX links are to **datasets/tools** repos rather than a list of included studies.

### 2405.15604
- TeX source does **not** contain a paper-by-paper included list. The paper points to a GitHub repo (https://github.com/jonas-becker/text-generation), but the likely data artifacts (e.g., `output.zip`, PDFs) are **binary** and cannot be fetched in this environment; need a text export (CSV/JSON/BibTeX) or an alternative hosting.

### 2407.17844
- The provided file `2407.17844.tar.gz` is actually a **PDF**, not a TeX source archive. Need the real TeX source (or parse the PDF appendix tables) to recover bibkeys.

### 2503.04799
- No explicit included-paper list found in TeX; would require similar disambiguation or supplementary materials.

### 2507.07741
- Appendix exists but focuses on **dataset/language/metric breakdowns** and does not enumerate included papers with citation keys (no \cite keys in appendix).

### 2507.18910
- No explicit included-paper list found in TeX (mentions screening conceptually, but no enumerated list).

### 2510.01145
- Appendix exists and contains citations, but appears to support **dataset/benchmark/detail tables** rather than a full included-paper bibliography/list.


## Suggested next actions (if you want me to continue)

1. For the two 'PDF-not-TeX' cases (2303.13365, 2407.17844): either provide the correct TeX source archives, or allow PDF-based extraction of appendix tables.

2. For 2405.15604: if you can provide `output.zip` (or the underlying CSV/JSON) locally, I can extract the 244-paper list + map to BibTeX keys.

3. For the remaining SRs: decide whether to treat 'included papers' as (a) those in PRISMA final set (if listed somewhere) or (b) all empirical studies discussed in Results tables; then I can build a deterministic extractor per paper.
