# Publication Date Parse Audit Comparison

- Generated at: `2026-03-26T11:32:34.791145+00:00`
- Output dir: `screening/results/publication_date_parse_audit_2026-03-26`
- Before summary: `screening/results/publication_date_parse_audit_2026-03-26/baseline_current_parser/summary.json`
- After summary: `screening/results/publication_date_parse_audit_2026-03-26/after_parser_fix/summary.json`
- Before parser sha256: `e36847d00992085a76bf7342f1d8a0ef9d1ba96c93f52ba3e536ca4f60b6df27`
- After parser sha256: `2cd8cf54dd22126a4441bb966a5d90eaeef880c1131ba09754ce249b68c027ea`

## Global Delta

- Total parsed: `2397` -> `2471`
- Total unparseable: `74` -> `0`
- `%Y-%m`-shaped unparseable count: `74` -> `0`
- `2601.19926` raw `2020-12`: `4` -> `0`
- `2601.19926` `2020-12` resolved: `True`

## Per-Paper Changes

| Paper | Input | Parsed before | Parsed after | Delta | Unparseable before | Unparseable after | Delta |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `2303.13365` | input_file_missing | 0 | 0 | 0 | 0 | 0 | 0 |
| `2306.12834` | ok | 251 | 263 | 12 | 12 | 0 | -12 |
| `2307.05527` | ok | 221 | 222 | 1 | 1 | 0 | -1 |
| `2310.07264` | ok | 107 | 107 | 0 | 0 | 0 | 0 |
| `2312.05172` | ok | 146 | 149 | 3 | 3 | 0 | -3 |
| `2401.09244` | ok | 204 | 207 | 3 | 3 | 0 | -3 |
| `2405.15604` | ok | 231 | 244 | 13 | 13 | 0 | -13 |
| `2407.17844` | input_file_missing | 0 | 0 | 0 | 0 | 0 | 0 |
| `2409.13738` | ok | 79 | 84 | 5 | 5 | 0 | -5 |
| `2503.04799` | ok | 123 | 131 | 8 | 8 | 0 | -8 |
| `2507.07741` | ok | 178 | 188 | 10 | 10 | 0 | -10 |
| `2507.18910` | ok | 149 | 151 | 2 | 2 | 0 | -2 |
| `2509.11446` | ok | 161 | 164 | 3 | 3 | 0 | -3 |
| `2510.01145` | ok | 110 | 113 | 3 | 3 | 0 | -3 |
| `2511.13936` | ok | 83 | 88 | 5 | 5 | 0 | -5 |
| `2601.19926` | ok | 354 | 360 | 6 | 6 | 0 | -6 |

## Resolved Raw Strings

- `1984-04`: before `1`, after `0`, affected papers before `2503.04799`
- `1991-10`: before `1`, after `0`, affected papers before `2503.04799`
- `1994-04`: before `1`, after `0`, affected papers before `2405.15604`
- `1997-03`: before `1`, after `0`, affected papers before `2405.15604`
- `2006-03`: before `1`, after `0`, affected papers before `2409.13738`
- `2007-02`: before `1`, after `0`, affected papers before `2312.05172`
- `2010-04`: before `1`, after `0`, affected papers before `2503.04799`
- `2010-09`: before `1`, after `0`, affected papers before `2312.05172`
- `2011-05`: before `1`, after `0`, affected papers before `2409.13738`
- `2013-06`: before `1`, after `0`, affected papers before `2312.05172`
- `2015-04`: before `2`, after `0`, affected papers before `2503.04799, 2510.01145`
- `2015-06`: before `1`, after `0`, affected papers before `2405.15604`
- `2016-12`: before `2`, after `0`, affected papers before `2306.12834, 2601.19926`
- `2017-01`: before `1`, after `0`, affected papers before `2405.15604`
- `2017-06`: before `1`, after `0`, affected papers before `2306.12834`
- `2017-08`: before `2`, after `0`, affected papers before `2306.12834, 2405.15604`
- `2017-10`: before `3`, after `0`, affected papers before `2401.09244, 2507.07741, 2511.13936`
- `2017-12`: before `1`, after `0`, affected papers before `2306.12834`
- `2018-04`: before `1`, after `0`, affected papers before `2507.07741`
- `2018-05`: before `1`, after `0`, affected papers before `2405.15604`
- `2018-07`: before `1`, after `0`, affected papers before `2405.15604`
- `2018-09`: before `1`, after `0`, affected papers before `2511.13936`
- `2018-10`: before `3`, after `0`, affected papers before `2306.12834, 2509.11446, 2601.19926`
- `2018-11`: before `1`, after `0`, affected papers before `2306.12834`
- `2018-12`: before `3`, after `0`, affected papers before `2306.12834, 2507.07741, 2511.13936`
- `2019-01`: before `1`, after `0`, affected papers before `2306.12834`
- `2019-05`: before `3`, after `0`, affected papers before `2507.07741`
- `2019-08`: before `1`, after `0`, affected papers before `2405.15604`
- `2019-11`: before `2`, after `0`, affected papers before `2405.15604, 2503.04799`
- `2019-12`: before `2`, after `0`, affected papers before `2401.09244, 2507.07741`
- `2020-01`: before `1`, after `0`, affected papers before `2307.05527`
- `2020-02`: before `2`, after `0`, affected papers before `2306.12834, 2507.07741`
- `2020-05`: before `1`, after `0`, affected papers before `2507.07741`
- `2020-06`: before `1`, after `0`, affected papers before `2405.15604`
- `2020-07`: before `1`, after `0`, affected papers before `2306.12834`
- `2020-10`: before `1`, after `0`, affected papers before `2306.12834`
- `2020-12`: before `6`, after `0`, affected papers before `2401.09244, 2405.15604, 2601.19926`
- `2021-01`: before `1`, after `0`, affected papers before `2306.12834`
- `2021-08`: before `1`, after `0`, affected papers before `2405.15604`
- `2022-07`: before `1`, after `0`, affected papers before `2405.15604`
- `2022-10`: before `1`, after `0`, affected papers before `2507.07741`
- `2022-11`: before `1`, after `0`, affected papers before `2503.04799`
- `2023-04`: before `1`, after `0`, affected papers before `2409.13738`
- `2023-05`: before `1`, after `0`, affected papers before `2409.13738`
- `2023-07`: before `1`, after `0`, affected papers before `2409.13738`
- `2023-08`: before `1`, after `0`, affected papers before `2503.04799`
- `2023-10`: before `1`, after `0`, affected papers before `2511.13936`
- `2023-11`: before `1`, after `0`, affected papers before `2509.11446`
- `2024-03`: before `1`, after `0`, affected papers before `2503.04799`
- `2024-04`: before `2`, after `0`, affected papers before `2507.18910, 2509.11446`
- `2024-05`: before `1`, after `0`, affected papers before `2507.18910`
- `2024-06`: before `1`, after `0`, affected papers before `2510.01145`
- `2025-03`: before `1`, after `0`, affected papers before `2511.13936`
- `2025-05`: before `1`, after `0`, affected papers before `2510.01145`

## Remaining Unparseable Raw Strings

- `(none)`

## `%Y-%m` Findings

- Papers with `%Y-%m`-shaped failures before: `2405.15604, 2306.12834, 2507.07741, 2503.04799, 2601.19926, 2409.13738, 2511.13936, 2312.05172, 2401.09244, 2509.11446, 2510.01145, 2507.18910, 2307.05527`
- Papers with `%Y-%m`-shaped failures after: `(none)`
- Papers improved: `2306.12834, 2307.05527, 2312.05172, 2401.09244, 2405.15604, 2409.13738, 2503.04799, 2507.07741, 2507.18910, 2509.11446, 2510.01145, 2511.13936, 2601.19926`
- Papers unchanged: `2310.07264`
- Papers still unparseable after fix: `(none)`
- Papers missing input files: `2303.13365, 2407.17844`
