# Method Specification: Boundary-Calibrated Proof-Carrying Screening

## Objective

BCPCS converts systematic-review screening from free-form LLM classification
into proof-carrying eligibility verification. The method reads source-faithful
stage criteria, creates typed eligibility claims, retrieves support and
refutation evidence, records a ledger, and derives final decisions through an
auditable graph with selective routing.

## Inputs

- Stage-specific criteria JSON from `criteria_stage1/` and `criteria_stage2/`.
- Metadata records from `refs/<paper_id>/metadata/title_abstracts_metadata.jsonl`.
- Gold labels only for evaluation, never for graph construction on held-out
  reviews.
- Full text from `refs/<paper_id>/mds/*.md` for Stage 2 when available.
- Cutoff policy from `cutoff_jsons/<paper_id>.json`.

## Processing Stages

### 1. Criteria Compilation

Each stage criterion is compiled into one or more atomic claims. Claims must
record:

- source criterion IDs,
- original criterion source path,
- stage,
- claim type,
- required status,
- decision operator,
- stage observability.

The compiler may split criteria for atomicity, but may not add stricter
requirements than the source paper supports.

### 2. Support And Refutation Retrieval

For every claim, the system generates two evidence needs:

- support evidence: spans that would satisfy the claim;
- refute evidence: spans that would trigger a contradiction or exclusion.

Stage 1 retrieval can use title, abstract, and metadata only. Stage 2 retrieval
can use full text when resolvable.

### 3. Evidence Ledger Creation

For each candidate and claim, the verifier writes:

- `support`, `refute`, or `unknown`,
- quote and location,
- source path or field,
- confidence,
- missingness reason when unknown,
- span validation status.

The verifier does not write the final include/exclude verdict.

### 4. Boundary Calibration

The Boundary Atlas contains leakage-controlled archetypes:

- positive archetypes,
- hard-negative archetypes,
- contrast pairs.

It calibrates near-miss boundaries such as:

- process extraction versus conceptual/UML/user-story extraction;
- preference learning versus preference-only evaluation;
- generative audio versus generic audio processing;
- syntax-specific transformer analysis versus generic language-model benchmark.

Atlas entries are workflow support, not formal criteria.

### 5. Decision Graph

The decision graph maps claim states to verdicts:

- required support missing at Stage 2 can force exclusion or routing;
- refute evidence can force exclusion;
- Stage 1 unknown can defer;
- unresolved Stage 2 evidence must route or mark a specific failure class.

The graph produces:

- auto verdict,
- route decision,
- decisive claims,
- unresolved claims,
- evidence provenance.

### 6. Selective Routing

If the graph cannot satisfy the risk policy, the candidate is routed to
SeniorLead or human adjudication. Routed cases are counted separately.

## Outputs

- Eligibility graph JSON.
- Evidence ledger JSONL.
- Boundary atlas JSON.
- Auto-decision JSONL.
- Selective-decision JSONL.
- Metrics report.
- Evidence validation report.

## Design Invariants

- Cutoff is applied before review.
- Formal criteria remain source-faithful.
- Stage 1 criteria remain a title/abstract projection.
- No third hidden criteria layer is introduced.
- SeniorLead remains in routed workflows.
- Evidence, not prose confidence, carries the decision.

