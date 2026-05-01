# BCPCS `gpt-5.4-mini xhigh` Execution Failure Note

## Summary

- Scope: current BCPCS `global-check / claim-packets` full-corpus rerun on all 4 SRs
- Model / effort: `gpt-5.4-mini`, `xhigh`
- Batch mode: yes
- Result: **not a valid quality comparison**

The observed low F1 is dominated by execution failure, not by normal include/exclude behavior.

## What Failed

From [bcpcs_xhigh_vs_gpt54mini_xhigh_single_stage_2026-04-23.md](/Users/xjp/Desktop/NLP_PRISMA_Reviews/research_bcpcs_2026-04-18/reports/bcpcs_xhigh_vs_gpt54mini_xhigh_single_stage_2026-04-23.md):

- BCPCS reviewed rows: `707`
- Parsed successes / failures / missing: `79 / 628 / 0`
- `finish_reason=length` + empty content rows: `628`

Per paper:

| paper | reviewed | parsed successes | parsed failures | `length` + empty content |
| --- | ---: | ---: | ---: | ---: |
| `2307.05527` | 208 | 0 | 208 | 208 |
| `2409.13738` | 65 | 0 | 65 | 65 |
| `2511.13936` | 75 | 4 | 71 | 71 |
| `2601.19926` | 359 | 75 | 284 | 284 |

These failures appear in the raw Batch outputs as:

- `finish_reason = "length"`
- `message.content = ""`
- `completion_tokens_details.reasoning_tokens = max_completion_tokens`

So the parser is failing with `JSONDecodeError` because there is no JSON content to parse at all.

## Smoke Checks

I manually retried failed `2601` rows outside the full batch to test whether a larger completion budget would fix the issue.

Tested rows:

- `stage2_recall_repair_batch__2601.19926__rogers_primer_2020`
- `stage2_recall_repair_batch__2601.19926__zhou_linguistic_2025`

### Smoke A: same BCPCS body, only raise `max_completion_tokens`

- setting: current BCPCS prompt/body, `xhigh`, `max_completion_tokens = 12288`
- result: still `finish_reason=length`, still empty `message.content`
- usage: `reasoning_tokens = 12288`

### Smoke B: trimmed prompt, keep `xhigh`

- setting: `evidence_packet_chars = 3000`, `max_quotes = 4`, `xhigh`, `max_completion_tokens = 12288`
- result: still `finish_reason=length`, still empty `message.content`
- usage: `reasoning_tokens = 12288`

## Conclusion

Under the current BCPCS prompt/task shape, `gpt-5.4-mini xhigh` is **operationally incompatible**:

- the model consumes the entire completion budget as reasoning
- many rows never emit the required JSON object
- the resulting F1 is therefore an execution artifact, not a trustworthy model-quality score

## Implication

If a future thread wants a valid BCPCS `xhigh` comparison, it cannot just rerun the current configuration.

It needs at least one of:

- a different reasoning effort
- a materially different prompt/task shape
- a different response contract / generation path

Until then, the current BCPCS `xhigh` all4 result should be treated as **invalid for quality comparison**.
