# How the criteria were parsed and normalized

This ZIP contains **one Markdown file per review**. Each file follows the same structure:

- **Stage 1: Retrieval Criteria (R1, R2, …)**  
  Conditions that define how the *candidate pool* was constructed (databases, time windows, query strings, language filters, citation thresholds, de-duplication rules, etc.).

- **Stage 2: Screening Criteria**  
  - **Inclusion Criteria (I1, I2, …)**: **ALL must be TRUE** for a study to be included.  
  - **Exclusion Criteria (E1, E2, …)**: **ALL must be FALSE**; if **any** exclusion criterion is TRUE, the study is excluded.

- **Quality Assessment Criteria (QA1, QA2, …)** (only when the review explicitly defines a quality checklist).  
  These are not always used as hard filters, but they are written as atomic conditions since they can be used for screening / assessment.

## Parsing procedure

For each paper:

1. **Locate explicit criteria statements**
   - Identify the *Methods / Methodology* section (or the PRISMA / “Search strategy”, “Selection criteria”, “Eligibility”, “Inclusion/Exclusion” subsections).
   - Prefer verbatim or near-verbatim phrasing whenever the paper provides a clear condition.

2. **Convert long narrative paragraphs into atomic screening conditions**
   - Split compound sentences into **single-condition items** whenever the paper packs multiple constraints into one sentence.
   - Keep examples inside parentheses when they only clarify a single condition (e.g., “knowledge-intensive tasks (open-domain QA, fact-checking, …)”).

3. **Remove non-criteria content**
   - Drop *outcomes* such as “N papers remained” or “we finally selected k studies”.
   - Keep only statements that can be interpreted as a **boolean gate** for retrieving/screening a paper.

4. **Handle redundancy between inclusion vs. exclusion**
   - When an exclusion is a pure negation of an already-present inclusion (e.g., *I: English-only* vs *E: non-English*), the criterion is kept only once (usually on the inclusion side) to avoid duplication.
   - When the exclusion adds extra meaning (e.g., excluding “review papers”), it is preserved.

5. **Repo / supplementary discovery**
   - If a paper explicitly provides a repository link (e.g., GitHub) or indicates that data/annotations are released externally, that link is recorded under **Related repository / supplementary**.
   - If no explicit link is present in the extracted criteria text, the field is left as “not explicitly provided…”.

## Important limitations

- Some reviews provide complete boolean strings and tables in the PDF/appendix; when only a partial snippet was available in the extracted text, the file notes this explicitly (without inventing missing tokens).
- If a paper mentions future release of code/data “upon acceptance” without a link, it is recorded as such.

