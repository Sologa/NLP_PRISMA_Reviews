# Leakage Control Protocol

This protocol must be frozen before any benchmark run.

## Allowed During Method Design

- Current-state architecture files.
- Stage-specific source-faithful criteria.
- Public literature and benchmark descriptions.
- Aggregate current metrics.
- Development split records and outputs.

## Forbidden For Held-Out Evaluation

- Using held-out FP/FN identities to construct Boundary Atlas entries.
- Inspecting held-out gold labels during prompt, graph, or atlas tuning.
- Editing graph nodes after seeing held-out errors.
- Converting held-out failure cases into new operational criteria.
- Reporting post-hoc repaired held-out results as primary results.

## Boundary Atlas Restrictions

Each atlas entry must record:

- source review;
- source candidate key when applicable;
- allowed split scope;
- forbidden evaluation keys;
- provenance text;
- whether it is positive, hard negative, or contrast pair.

An atlas entry is invalid if it is derived from a held-out case and then used
to evaluate that same held-out case.

## Gold Label Handling

Gold labels are for evaluation only. If source-faithful criteria and gold labels
appear in tension, mark the case as `criteria_gold_tension` and report it as a
separate slice.

Do not silently optimize to gold when it conflicts with source criteria.

## Invalidating Conditions

Invalidate a run when:

- the held-out split was inspected during method tuning;
- Boundary Atlas includes held-out final errors;
- generated outputs were written outside `research_bcpcs_2026-04-18/`;
- active production criteria or prompts were modified;
- final human-assisted F1 is reported as automated F1.

