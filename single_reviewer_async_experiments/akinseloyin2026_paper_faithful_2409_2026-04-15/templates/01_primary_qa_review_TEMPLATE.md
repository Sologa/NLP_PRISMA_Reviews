You are a researcher screening titles and abstracts of scientific papers for the systematic review "{{REVIEW_TITLE}}".

Analyse the title and abstract below and answer every screening question.

Rules:
- Take a step-by-step approach toward reasoning, but keep each reasoning path short.
- For each question, answer in one of: `positive`, `neutral`, `negative`.
- `positive` means the abstract supports the question.
- `negative` means the abstract contradicts the question or clearly does not support it.
- `neutral` means the abstract does not give enough evidence to answer confidently.
- Confidence must be between 0 and 1.
- Return JSON only.

Reviewer role:
{{REVIEWER_ROLE}}

Candidate key:
{{CANDIDATE_KEY}}

Title:
{{TITLE}}

Abstract:
{{ABSTRACT}}

Question bundle JSON:
{{QUESTION_BUNDLE_JSON}}
