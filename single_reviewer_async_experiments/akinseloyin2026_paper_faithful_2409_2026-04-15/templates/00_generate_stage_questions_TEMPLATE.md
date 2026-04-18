You are a researcher screening titles and abstracts of scientific papers.

Generate exactly 5 unique yes/no screening questions for the systematic review topic below.

Rules:
- Cover the full Stage 1 observable eligibility, not just one inclusion bullet.
- Keep conjunction statements together when the criterion requires them together.
- Do not create duplicate or unnecessary questions.
- Every question must be answerable from title and abstract only.
- Questions must be useful for ranking candidate papers for abstract screening.
- Return JSON only.

Review title:
{{REVIEW_TITLE}}

Paper id:
{{PAPER_ID}}

Stage id:
{{STAGE_ID}}

Stage criteria JSON:
{{STAGE_CRITERIA_JSON}}
