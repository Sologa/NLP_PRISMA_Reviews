# Gate LLM Prompt And Output

這個檔案放的是 `primary_evidence_gate` 的 LLM I/O 形狀。完整 raw artifacts 仍以同目錄 JSON 為準。

## Where

- run: `screening/results/primary_evidence_gate_overlay_2026-05-16/runs/20260516_gpt5nano_high_primary_gate_3papers_v2`
- batch input: `batch_jobs/primary_evidence_gate/gpt-5-nano/input.jsonl`
- parsed output: `batch_jobs/primary_evidence_gate/gpt-5-nano/parsed_results.json`
- normalized gate rows: `primary_gate_results.json`
- rendered prompt example: `rendered_prompt_example.md`

## Output Shape

每一筆 LLM 回傳一個 strict JSON object：

```json
{
  "is_primary": "boolean. True means the row passed the source-form gate as primary/primary-like, or at least not clearly non-primary.",
  "gate_decision": "pass_primary | exclude_non_primary | unclear_pass",
  "publication_type": "primary_empirical | secondary_review_or_survey | position_or_commentary | standards_or_book_or_tool_doc | non_empirical_other | unknown",
  "criteria_exception_applied": "boolean. True only if criteria explicitly allow secondary/review papers.",
  "short_rationale": "short explanation for the source-form decision.",
  "evidence_fields_used": "list of candidate metadata fields used, usually title/abstract.",
  "title_abstract_quotes": "candidate title/abstract snippets supporting the source-form call."
}
```

實作上 normalized row 會再加上 `paper_id`、`key`、`title`、`criteria_primary_gate_policy`、`custom_id`，寫入 `primary_gate_results.json`。

## Prompt Template

這是實際使用的 template；每筆 request 會把 `{{...}}` placeholder 換成該 candidate 的 metadata 與 criteria policy。

```markdown
# Primary Evidence Gate

You are running an experiment-only pre-review gate. Classify the candidate's
publication form using only title/abstract-visible metadata and the supplied
criteria policy.

The criteria JSON and policy describe the systematic review's screening rules,
not the candidate paper. Never quote the review topic, review title, criteria
source, or criteria wording as evidence about the candidate's publication form.
Candidate evidence must come from the Candidate Metadata block, especially the
candidate `title` and `abstract`.

## Decision Boundary

The default gate is active unless the criteria policy says secondary or survey
papers are explicitly allowed.

Return `exclude_non_primary` only when the candidate title, abstract, or
metadata clearly shows that the candidate is not a primary empirical/original
research study. Examples include survey, review, systematic review, scoping
review, position paper, editorial/commentary, reporting guideline,
standards/specification document, or dataset/tool documentation without an
empirical analysis.

Return `pass_primary` when the title/abstract indicates an original empirical,
experimental, methodological, dataset-with-evaluation, or analytic study.
Replication or reproduction studies with experiments/analysis should pass.
Book chapters or proceedings chapters should pass when the abstract reports
original experiments, analyses, or empirical results.

Return `unclear_pass` when the publication form is ambiguous from title and
abstract. Do not exclude merely because the abstract is short or the empirical
component is not fully proven from the abstract.

For every `exclude_non_primary` decision, include at least one
`title_abstract_quotes` item that is copied from the candidate title or abstract
and directly signals the non-primary publication form. If you cannot quote such
a candidate-specific signal, return `unclear_pass`.

If `criteria_exception_allows_secondary` is true, do not exclude a candidate
only for being a secondary/survey/review paper. In that case, set
`criteria_exception_applied` to true and use `pass_primary` or `unclear_pass`
as appropriate.

## Required JSON Output

Return only the strict JSON object requested by the response schema.

## Paper

`{{PAPER_ID}}`

## Candidate Metadata

```json
{{METADATA_JSON}}
```

## Criteria Primary-Gate Policy

```json
{{CRITERIA_PRIMARY_GATE_POLICY_JSON}}
```

## Stage 1 Criteria

```json
{{STAGE1_CRITERIA_JSON}}
```
```

## Rendered Prompt Example

完整第一筆 rendered prompt 已存在同目錄：`rendered_prompt_example.md`。下面只放前段，避免這個檔案太長。

```markdown
# Primary Evidence Gate

You are running an experiment-only pre-review gate. Classify the candidate's
publication form using only title/abstract-visible metadata and the supplied
criteria policy.

The criteria JSON and policy describe the systematic review's screening rules,
not the candidate paper. Never quote the review topic, review title, criteria
source, or criteria wording as evidence about the candidate's publication form.
Candidate evidence must come from the Candidate Metadata block, especially the
candidate `title` and `abstract`.

## Decision Boundary

The default gate is active unless the criteria policy says secondary or survey
papers are explicitly allowed.

Return `exclude_non_primary` only when the candidate title, abstract, or
metadata clearly shows that the candidate is not a primary empirical/original
research study. Examples include survey, review, systematic review, scoping
review, position paper, editorial/commentary, reporting guideline,
standards/specification document, or dataset/tool documentation without an
empirical analysis.

Return `pass_primary` when the title/abstract indicates an original empirical,
experimental, methodological, dataset-with-evaluation, or analytic study.
Replication or reproduction studies with experiments/analysis should pass.
Book chapters or proceedings chapters should pass when the abstract reports
original experiments, analyses, or empirical results.

Return `unclear_pass` when the publication form is ambiguous from title and
abstract. Do not exclude merely because the abstract is short or the empirical
component is not fully proven from the abstract.

For every `exclude_non_primary` decision, include at least one
`title_abstract_quotes` item that is copied from the candidate title or abstract
and directly signals the non-primary publication form. If you cannot quote such
a candidate-specific signal, return `unclear_pass`.

If `criteria_exception_allows_secondary` is true, do not exclude a candidate
only for being a secondary/survey/review paper. In that case, set
`criteria_exception_applied` to true and use `pass_primary` or `unclear_pass`
as appropriate.

## Required JSON Output

Return only the strict JSON object requested by the response schema.

## Paper

`2409.13738`

## Candidate Metadata

```json
{
  "key": "straw2020artificial",
  "query_title": "Artificial Intelligence in mental health and the biases of language based models",
  "title": "Artificial Intelligence in mental health and the biases of language based models",
  "abstract": "Background The rapid integration of Artificial Intelligence (AI) into the healthcare field has occurred with little communication between computer scientists and doctors. The impact of AI on health outcomes and inequalities calls for health professionals and data scientists to make a collaborative effort to ensure historic health disparities are not encoded into the future. We present a study that evaluates bias in existing Natural Language Processing (NLP) models used in psychiatry and discuss how these biases may widen health inequalities. Our approach systematically evaluates each stage of model development to explore how biases arise from a clinical, data science and linguistic perspective. Design/Methods A literature review of the uses of NLP in mental health was carried out across multiple disciplinary databases with defined Mesh terms and keywords. Our primary analysis evaluated biases within ‘GloVe’ and ‘Word2Vec’ word embeddings. Euclidean distances were measured to assess relationships between psychiatric terms and demographic labels, and vector similarity functions were used to solve analogy questions relating to mental health. Results Our primary analysis of mental health terminology in GloVe and Word2Vec embeddings demonstrated significant biases with respect to religion, race, gender, nationality, sexuality and age. Our literature review returned 52 papers, of which none addressed all the areas of possible bias that we identify in model development. In addition, only one article existed on more than one research database, demonstrating the isolation of research within disciplinary silos and inhibiting cross-disciplinary collaboration or communication. Conclusion Our findings are relevant to professionals who wish to minimize the health inequalities that may arise as a result of AI and data-driven algorithms. We offer primary research identifying biases within these technologies and provide recommendations for avoiding these harms in the future.",
  "source": "crossref",
  "source_id": "10.1371/journal.pone.0240376",
  "match_status": "exact_doi",
  "published_date": "2020-12-17",
  "artifact_gate_pass": null,
  "artifact_gate_reason": ""
}
```

## Criteria Primary-Gate Policy

```json
{
  "paper_id": "2409.13738",
  "gate_default_active": true,
  "criteria_exception_allows_secondary": false,
  "matched_exclusion_markers": [
    "secondary research articles are excluded",
    "primary research artic

...[truncated here; see rendered_prompt_example.md for full prompt]...
```

## Real LLM Output Examples

### `pass_primary` example: `2409.13738/Devlin2019BERTPO`

Raw assistant JSON from `parsed_results.json`:

```json
{
  "is_primary": true,
  "gate_decision": "pass_primary",
  "publication_type": "primary_empirical",
  "criteria_exception_applied": false,
  "short_rationale": "The title/abstract describe an original model pre-training approach (BERT) and report empirical results across multiple NLP tasks, indicating an original empirical research study.",
  "evidence_fields_used": [
    "title",
    "abstract"
  ],
  "title_abstract_quotes": []
}
```

Normalized row excerpt:

```json
{
  "paper_id": "2409.13738",
  "key": "Devlin2019BERTPO",
  "title": "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
  "is_primary": true,
  "gate_decision": "pass_primary",
  "publication_type": "primary_empirical",
  "short_rationale": "The title/abstract describe an original model pre-training approach (BERT) and report empirical results across multiple NLP tasks, indicating an original empirical research study.",
  "evidence_fields_used": [
    "title",
    "abstract"
  ],
  "title_abstract_quotes": []
}
```

### `exclude_non_primary` example: `2409.13738/Page2021`

Raw assistant JSON from `parsed_results.json`:

```json
{
  "is_primary": false,
  "gate_decision": "exclude_non_primary",
  "publication_type": "standards_or_book_or_tool_doc",
  "criteria_exception_applied": false,
  "short_rationale": "Non-primary publication: the candidate is a guideline/standards document describing reporting guidelines for systematic reviews; no original empirical analysis is reported.",
  "evidence_fields_used": [
    "title",
    "abstract"
  ],
  "title_abstract_quotes": [
    "an updated guideline for reporting systematic reviews",
    "an update to the guideline.",
    "includes new reporting guidance that reflects advances in methods to identify, select, appraise, and synthesise studies."
  ]
}
```

Normalized row excerpt:

```json
{
  "paper_id": "2409.13738",
  "key": "Page2021",
  "title": "The PRISMA 2020 statement: an updated guideline for reporting systematic reviews",
  "is_primary": false,
  "gate_decision": "exclude_non_primary",
  "publication_type": "standards_or_book_or_tool_doc",
  "short_rationale": "Non-primary publication: the candidate is a guideline/standards document describing reporting guidelines for systematic reviews; no original empirical analysis is reported.",
  "evidence_fields_used": [
    "title",
    "abstract"
  ],
  "title_abstract_quotes": [
    "an updated guideline for reporting systematic reviews",
    "an update to the guideline.",
    "includes new reporting guidance that reflects advances in methods to identify, select, appraise, and synthesise studies."
  ]
}
```

### `unclear_pass` example: `2409.13738/dumas2018fundamentals`

Raw assistant JSON from `parsed_results.json`:

```json
{
  "is_primary": false,
  "gate_decision": "unclear_pass",
  "publication_type": "unknown",
  "criteria_exception_applied": false,
  "short_rationale": "No abstract is provided for the candidate; the title 'Fundamentals of Business Process Management' is indicative of a textbook or reference work rather than a clearly identifiable primary empirical study. Without abstract content to confirm empirical methods or results, the publication form remains unclear.",
  "evidence_fields_used": [
    "title",
    "abstract"
  ],
  "title_abstract_quotes": []
}
```

Normalized row excerpt:

```json
{
  "paper_id": "2409.13738",
  "key": "dumas2018fundamentals",
  "title": "Fundamentals of Business Process Management",
  "is_primary": false,
  "gate_decision": "unclear_pass",
  "publication_type": "unknown",
  "short_rationale": "No abstract is provided for the candidate; the title 'Fundamentals of Business Process Management' is indicative of a textbook or reference work rather than a clearly identifiable primary empirical study. Without abstract content to confirm empirical methods or results, the publication form remains unclear.",
  "evidence_fields_used": [
    "title",
    "abstract"
  ],
  "title_abstract_quotes": []
}
```

## Run Counts

- input_total: `499`
- parsed successes: `499`
- parsed failures: `0`
- parsed missing: `0`
