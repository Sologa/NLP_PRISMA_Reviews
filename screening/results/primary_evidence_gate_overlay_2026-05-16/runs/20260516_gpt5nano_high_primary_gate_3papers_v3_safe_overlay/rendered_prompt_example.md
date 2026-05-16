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
    "primary research article",
    "original research contribution"
  ],
  "matched_allow_markers": [],
  "policy": "Secondary/survey/review/non-primary source forms are excluded before review."
}
```

## Stage 1 Criteria

```json
{
  "topic": "NLP4PBM: A Systematic Review on Process Extraction using Natural Language Processing with Rule-based, Machine and Deep Learning Methods",
  "topic_definition": "Stage 1 observable projection of the original paper's eligibility. Use title+abstract evidence to judge whether the study specifically covers NLP for process extraction from natural-language text. Full-text-only checks (paper type, language/fulltext availability, primary-research status, method concreteness, empirical validation) are deferred to Stage 2.",
  "summary": "Stage 1 title/abstract projection of source-faithful Stage 2 criteria; no added topic-specific hardening beyond observable restatement.",
  "summary_topics": [
    {
      "id": "S1",
      "description": "NLP4PBM: A Systematic Review on Process Extraction using Natural Language Processing with Rule-based, Machine and Deep Learning Methods"
    }
  ],
  "inclusion_criteria": {
    "required": [
      {
        "criterion": "Title/abstract explicitly indicates that the paper specifically covers the use of NLP for process extraction from natural language text.",
        "source": "https://arxiv.org/html/2409.13738v1",
        "topic_ids": [
          "S1"
        ]
      },
      {
        "criterion": "Observable task signal links natural-language text to process-model or process-representation extraction/construction objectives.",
        "source": "https://arxiv.org/html/2409.13738v1",
        "topic_ids": [
          "S1"
        ]
      },
      {
        "criterion": "When the core fit is plausible but title/abstract evidence is incomplete, keep maybe and defer final confirmation to Stage 2 instead of adding new hard exclusions.",
        "source": "https://arxiv.org/html/2409.13738v1",
        "topic_ids": [
          "S1"
        ]
      }
    ]
  },
  "exclusion_criteria": [
    {
      "criterion": "Title/abstract clearly indicates the study is not specifically covering NLP for process extraction from natural language text.",
      "source": "https://arxiv.org/html/2409.13738v1",
      "topic_ids": [
        "S1"
      ]
    },
    {
      "criterion": "Observable non-target examples from EC.3: NLP for process redesign, matching, or process prediction.",
      "source": "https://arxiv.org/html/2409.13738v1",
      "topic_ids": [
        "S1"
      ]
    },
    {
      "criterion": "Observable non-target examples from EC.3: sentiment analysis, works targeting individual labels instead of natural text, or studies on generating natural text from processes.",
      "source": "https://arxiv.org/html/2409.13738v1",
      "topic_ids": [
        "S1"
      ]
    },
    {
      "criterion": "Survey/review papers are excluded when title/abstract clearly indicates secondary research.",
      "source": "https://arxiv.org/html/2409.13738v1",
      "topic_ids": [
        "S1"
      ]
    }
  ],
  "sources": [
    "https://arxiv.org/html/2409.13738v1"
  ]
}
```
