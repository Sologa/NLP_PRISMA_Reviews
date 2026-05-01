# BCPCS XHigh vs `gpt-5.4-mini` XHigh Single-Stage Baseline

## Scope

- baseline: cutoff-pass rows direct to current Stage 2 prompt, `gpt-5.4-mini`, `xhigh`, Batch API
- BCPCS: global-check / claim-packets full-corpus split-batch rerun, `gpt-5.4-mini`, `xhigh`, Batch API
- original 127 slice source: `127` rows from current full127 inventory

## Validity

- BCPCS quality-comparison valid: `False`
- BCPCS reviewed rows: `707`
- BCPCS parsed successes / failures / missing: `79` / `628` / `0`
- BCPCS `finish_reason=length` + empty content rows: `628`
- Interpretation: if most BCPCS rows exhausted completion budget on reasoning and returned empty content, the reported F1 is an execution-failure artifact, not a clean model-quality comparison.

## Overall Full Corpus

| system | F1 | precision | recall | TP/FP/TN/FN | total cost |
| --- | ---: | ---: | ---: | --- | ---: |
| baseline single-stage xhigh | 0.9168 | 0.9700 | 0.8692 | 485/15/181/73 | $7.407065 |
| BCPCS xhigh | 0.2355 | 0.9494 | 0.1344 | 75/4/192/483 | $7.808285 |

## Per Paper

| paper | baseline F1 | BCPCS F1 | delta | baseline P/R | BCPCS P/R | baseline TP/FP/TN/FN | BCPCS TP/FP/TN/FN | baseline cost | BCPCS cost | baseline run |
| --- | ---: | ---: | ---: | --- | --- | --- | --- | ---: | ---: | --- |
| `2307.05527` | 0.8959 | 0.0000 | -0.8959 | 0.9726 / 0.8304 | 0.0000 / 0.0000 | 142/4/47/29 | 0/0/51/171 | $2.809071 | $2.415868 | `20260423_gpt54mini_xhigh_singlestage_2307_2601` |
| `2409.13738` | 0.9130 | 0.0000 | -0.9130 | 0.8400 / 1.0000 | 0.0000 / 0.0000 | 21/4/59/0 | 0/0/63/21 | $0.566953 | $0.736583 | `20260423_gpt54mini_xhigh_singlestage_2409_2511` |
| `2511.13936` | 0.8814 | 0.1176 | -0.7637 | 0.8966 / 0.8667 | 0.5000 / 0.0667 | 26/3/55/4 | 2/2/56/28 | $0.723219 | $0.831776 | `20260423_gpt54mini_xhigh_singlestage_2409_2511` |
| `2601.19926` | 0.9308 | 0.3552 | -0.5756 | 0.9867 / 0.8810 | 0.9733 / 0.2173 | 296/4/20/40 | 73/2/22/263 | $3.307822 | $3.824058 | `20260423_gpt54mini_xhigh_singlestage_2307_2601` |

## Original 127 Slice

- total: `127`
- primary / secondary: `22` / `105`
- per paper: `{"2307.05527": 41, "2409.13738": 5, "2511.13936": 5, "2601.19926": 76}`

| system | F1 | precision | recall | TP/FP/TN/FN |
| --- | ---: | ---: | ---: | --- |
| baseline single-stage xhigh on original 127 | 0.5810 | 0.8000 | 0.4561 | 52/13/0/62 |
| BCPCS xhigh full-corpus slice on original 127 | 0.0833 | 0.8333 | 0.0439 | 5/1/12/109 |
| BCPCS dedicated full127 reference run | 0.8700 | 0.8818 | 0.8584 | 97/13/0/16 |

### Original 127 Per Paper

| paper | baseline single-stage xhigh F1 | BCPCS xhigh all4-slice F1 | BCPCS dedicated full127 F1 | baseline TP/FP/TN/FN | BCPCS all4-slice TP/FP/TN/FN | BCPCS full127 TP/FP/TN/FN |
| --- | ---: | ---: | ---: | --- | --- | --- |
| `2307.05527` | 0.5091 | 0.0000 | 0.9487 | 14/4/0/23 | 0/0/4/37 | 37/4/0/0 |
| `2409.13738` | 0.3333 | 0.0000 | 0.3333 | 1/4/0/0 | 0/0/4/1 | 1/4/0/0 |
| `2511.13936` | 0.3333 | 0.0000 | 0.8889 | 1/1/0/3 | 0/0/1/4 | 4/1/0/0 |
| `2601.19926` | 0.6429 | 0.1282 | 0.8397 | 36/4/0/36 | 5/1/3/67 | 55/4/0/17 |

## Notes

- `BCPCS xhigh full-corpus slice on original 127` is the original 127 inventory intersected with the new all4 full-corpus BCPCS xhigh outputs.
- `BCPCS dedicated full127 reference run` stays as the direct guardrail reference for the current full127 architecture line, so the two BCPCS rows answer different questions.
- The baseline row on the original 127 answers how many of those historical error cases are still missed by the new single-stage xhigh baseline.
