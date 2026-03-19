## Global Identity And Hygiene Policy

- `paper_id` is the systematic-review id, not the candidate record key.
- Candidate identity is defined only by `candidate_key` and `candidate_title`.
- Use only candidate-level inputs as evidence: title, abstract, allowed metadata, prior-stage output, current QA output, synthesis output, and full text when the current stage allows it.
- Treat `review.title`, `review.topic`, `source_markdown`, `source_basis`, criteria review topic text, and reviewer-facing bundle metadata as workflow context only. They are not candidate evidence.
- Never quote, normalize, or reason from review-level phrases unless the same phrase is directly present in the candidate-level evidence.
- Copy the output identity contract exactly. Do not invent, rename, or silently alter identity fields.
- If the current input does not support a claim, leave it unresolved; do not backfill it from bundle metadata.
