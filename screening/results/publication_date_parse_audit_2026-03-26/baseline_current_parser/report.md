# Publication Date Parse Audit

- Generated at: `2026-03-26T09:58:50.886085+00:00`
- Output dir: `screening/results/publication_date_parse_audit_2026-03-26/baseline_current_parser`
- Parser target: `scripts.screening.cutoff_time_filter._parse_candidate_date`
- Parser file: `scripts/screening/cutoff_time_filter.py`
- Parser sha256: `e36847d00992085a76bf7342f1d8a0ef9d1ba96c93f52ba3e536ca4f60b6df27`

## Global Summary

- Papers requested: `16`
- Papers with input files: `14`
- Papers missing input files: `2`
- Total input rows: `2491`
- Total unique keys: `2471`
- Total duplicate keys: `20`
- Total duplicate rows skipped: `20`
- Parsed count: `2397`
- Unparseable count: `74`
- Missing/empty count: `0`
- Parse success rate: `0.9701`

## Per-Paper Table

| Paper | Input | Rows | Unique | Dup keys | Dup rows | Parsed | Unparseable | Missing | Success rate |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2303.13365` | input_file_missing | 0 | 0 | 0 | 0 | 0 | 0 | 0 | None |
| `2306.12834` | ok | 263 | 263 | 0 | 0 | 251 | 12 | 0 | 0.9544 |
| `2307.05527` | ok | 222 | 222 | 0 | 0 | 221 | 1 | 0 | 0.9955 |
| `2310.07264` | ok | 107 | 107 | 0 | 0 | 107 | 0 | 0 | 1.0 |
| `2312.05172` | ok | 149 | 149 | 0 | 0 | 146 | 3 | 0 | 0.9799 |
| `2401.09244` | ok | 207 | 207 | 0 | 0 | 204 | 3 | 0 | 0.9855 |
| `2405.15604` | ok | 244 | 244 | 0 | 0 | 231 | 13 | 0 | 0.9467 |
| `2407.17844` | input_file_missing | 0 | 0 | 0 | 0 | 0 | 0 | 0 | None |
| `2409.13738` | ok | 84 | 84 | 0 | 0 | 79 | 5 | 0 | 0.9405 |
| `2503.04799` | ok | 131 | 131 | 0 | 0 | 123 | 8 | 0 | 0.9389 |
| `2507.07741` | ok | 189 | 188 | 1 | 1 | 178 | 10 | 0 | 0.9468 |
| `2507.18910` | ok | 159 | 151 | 8 | 8 | 149 | 2 | 0 | 0.9868 |
| `2509.11446` | ok | 164 | 164 | 0 | 0 | 161 | 3 | 0 | 0.9817 |
| `2510.01145` | ok | 123 | 113 | 10 | 10 | 110 | 3 | 0 | 0.9735 |
| `2511.13936` | ok | 89 | 88 | 1 | 1 | 83 | 5 | 0 | 0.9432 |
| `2601.19926` | ok | 360 | 360 | 0 | 0 | 354 | 6 | 0 | 0.9833 |

## Missing Input Files

- `2303.13365`
- `2407.17844`

## Top Unparseable Raw Strings

- `2020-12`: count `6`, papers `2401.09244, 2405.15604, 2601.19926`, example keys `Romim2020HateSD, KumarAVT20a, rogers_primer_2020, Warstadt:etal:2020, ettinger_what_2020, kuncoro-etal-2020-syntactic`
- `2017-10`: count `3`, papers `2401.09244, 2507.07741, 2511.13936`, example keys `lample2018word, Zhu_2017_ICCV, sutton2017popularity`
- `2018-10`: count `3`, papers `2306.12834, 2509.11446, 2601.19926`, example keys `al2018survey, devlin2019bertpretrainingdeepbidirectional, Devlin:etal:2019`
- `2018-12`: count `3`, papers `2306.12834, 2507.07741, 2511.13936`, example keys `guan2018generation, emond2018transliteration, kilgour2018fr`
- `2019-05`: count `3`, papers `2507.07741`, example keys `shan_end2end, 8682824, li_bytes_2019`
- `2015-04`: count `2`, papers `2503.04799, 2510.01145`, example keys `7178964, Panayotov2015`
- `2016-12`: count `2`, papers `2306.12834, 2601.19926`, example keys `kundeti2016clinical, Linzen:etal:2016`
- `2017-08`: count `2`, papers `2306.12834, 2405.15604`, example keys `paez2017gray, WangHF17a`
- `2019-11`: count `2`, papers `2405.15604, 2503.04799`, example keys `LiuXTL19, Griffin-Lim`
- `2019-12`: count `2`, papers `2401.09244, 2507.07741`, example keys `charitidis2020towards, yue_end--end_2019`
- `2020-02`: count `2`, papers `2306.12834, 2507.07741`, example keys `vaci2020natural, dhawan_investigating_2020`
- `2024-04`: count `2`, papers `2507.18910, 2509.11446`, example keys `AbdulKhaliq2024, 10440574`
- `1984-04`: count `1`, papers `2503.04799`, example keys `articleStft`
- `1991-10`: count `1`, papers `2503.04799`, example keys `anderson1991hcrc`
- `1994-04`: count `1`, papers `2405.15604`, example keys `GoldbergDK94`
- `1997-03`: count `1`, papers `2405.15604`, example keys `ReiterD97`
- `2006-03`: count `1`, papers `2409.13738`, example keys `Fereday2006`
- `2007-02`: count `1`, papers `2312.05172`, example keys `wu2007`
- `2010-04`: count `1`, papers `2503.04799`, example keys `5453745`
- `2010-09`: count `1`, papers `2312.05172`, example keys `clarkelapata2010discourse`

## Most Affected Papers

- `2405.15604`: unparseable `13`, success rate `0.9467`
- `2306.12834`: unparseable `12`, success rate `0.9544`
- `2507.07741`: unparseable `10`, success rate `0.9468`
- `2503.04799`: unparseable `8`, success rate `0.9389`
- `2601.19926`: unparseable `6`, success rate `0.9833`
- `2409.13738`: unparseable `5`, success rate `0.9405`
- `2511.13936`: unparseable `5`, success rate `0.9432`
- `2510.01145`: unparseable `3`, success rate `0.9735`
- `2312.05172`: unparseable `3`, success rate `0.9799`
- `2509.11446`: unparseable `3`, success rate `0.9817`
- `2401.09244`: unparseable `3`, success rate `0.9855`
- `2507.18910`: unparseable `2`, success rate `0.9868`
- `2307.05527`: unparseable `1`, success rate `0.9955`

## 2303.13365

- Input status: `input_file_missing`
- Metadata path: `refs/2303.13365/metadata/title_abstracts_metadata.jsonl`
- Detail JSON: `screening/results/publication_date_parse_audit_2026-03-26/baseline_current_parser/papers/2303.13365.json`

## 2306.12834

- Input status: `ok`
- Metadata path: `refs/2306.12834/metadata/title_abstracts_metadata.jsonl`
- Detail JSON: `screening/results/publication_date_parse_audit_2026-03-26/baseline_current_parser/papers/2306.12834.json`
- Duplicate keys: `0`
- Duplicate rows skipped: `0`
- Duplicate keys with conflicting `published_date`: `(none)`
- Unparseable raw strings:
  - `2016-12`: count `1`, example keys `kundeti2016clinical`
  - `2017-06`: count `1`, example keys `jonnalagadda2017text`
  - `2017-08`: count `1`, example keys `paez2017gray`
  - `2017-12`: count `1`, example keys `weng2017medical`
  - `2018-10`: count `1`, example keys `al2018survey`
  - `2018-11`: count `1`, example keys `santos2018cross`
  - `2018-12`: count `1`, example keys `guan2018generation`
  - `2019-01`: count `1`, example keys `esteva2019guide`
  - `2020-02`: count `1`, example keys `vaci2020natural`
  - `2020-07`: count `1`, example keys `bhat2020automated`
  - `2020-10`: count `1`, example keys `weissler2020use`
  - `2021-01`: count `1`, example keys `Ulrich2021The`

## 2307.05527

- Input status: `ok`
- Metadata path: `refs/2307.05527/metadata/title_abstracts_metadata.jsonl`
- Detail JSON: `screening/results/publication_date_parse_audit_2026-03-26/baseline_current_parser/papers/2307.05527.json`
- Duplicate keys: `0`
- Duplicate rows skipped: `0`
- Duplicate keys with conflicting `published_date`: `(none)`
- Unparseable raw strings:
  - `2020-01`: count `1`, example keys `kelley2021exciting`

## 2310.07264

- Input status: `ok`
- Metadata path: `refs/2310.07264/metadata/title_abstracts_metadata.jsonl`
- Detail JSON: `screening/results/publication_date_parse_audit_2026-03-26/baseline_current_parser/papers/2310.07264.json`
- Duplicate keys: `0`
- Duplicate rows skipped: `0`
- Duplicate keys with conflicting `published_date`: `(none)`
- Unparseable raw strings: `(none)`

## 2312.05172

- Input status: `ok`
- Metadata path: `refs/2312.05172/metadata/title_abstracts_metadata.jsonl`
- Detail JSON: `screening/results/publication_date_parse_audit_2026-03-26/baseline_current_parser/papers/2312.05172.json`
- Duplicate keys: `0`
- Duplicate rows skipped: `0`
- Duplicate keys with conflicting `published_date`: `(none)`
- Unparseable raw strings:
  - `2007-02`: count `1`, example keys `wu2007`
  - `2010-09`: count `1`, example keys `clarkelapata2010discourse`
  - `2013-06`: count `1`, example keys `cohn2013`

## 2401.09244

- Input status: `ok`
- Metadata path: `refs/2401.09244/metadata/title_abstracts_metadata.jsonl`
- Detail JSON: `screening/results/publication_date_parse_audit_2026-03-26/baseline_current_parser/papers/2401.09244.json`
- Duplicate keys: `0`
- Duplicate rows skipped: `0`
- Duplicate keys with conflicting `published_date`: `(none)`
- Unparseable raw strings:
  - `2017-10`: count `1`, example keys `lample2018word`
  - `2019-12`: count `1`, example keys `charitidis2020towards`
  - `2020-12`: count `1`, example keys `Romim2020HateSD`

## 2405.15604

- Input status: `ok`
- Metadata path: `refs/2405.15604/metadata/title_abstracts_metadata.jsonl`
- Detail JSON: `screening/results/publication_date_parse_audit_2026-03-26/baseline_current_parser/papers/2405.15604.json`
- Duplicate keys: `0`
- Duplicate rows skipped: `0`
- Duplicate keys with conflicting `published_date`: `(none)`
- Unparseable raw strings:
  - `1994-04`: count `1`, example keys `GoldbergDK94`
  - `1997-03`: count `1`, example keys `ReiterD97`
  - `2015-06`: count `1`, example keys `VedantamZP15a`
  - `2017-01`: count `1`, example keys `MoratanchC17`
  - `2017-08`: count `1`, example keys `WangHF17a`
  - `2018-05`: count `1`, example keys `GaoLSQ18`
  - `2018-07`: count `1`, example keys `WangYTZ18`
  - `2019-08`: count `1`, example keys `GaoBCL19`
  - `2019-11`: count `1`, example keys `LiuXTL19`
  - `2020-06`: count `1`, example keys `SchusterSSB20a`
  - `2020-12`: count `1`, example keys `KumarAVT20a`
  - `2021-08`: count `1`, example keys `LiTZW21`
  - `2022-07`: count `1`, example keys `Peng22`

## 2407.17844

- Input status: `input_file_missing`
- Metadata path: `refs/2407.17844/metadata/title_abstracts_metadata.jsonl`
- Detail JSON: `screening/results/publication_date_parse_audit_2026-03-26/baseline_current_parser/papers/2407.17844.json`

## 2409.13738

- Input status: `ok`
- Metadata path: `refs/2409.13738/metadata/title_abstracts_metadata.jsonl`
- Detail JSON: `screening/results/publication_date_parse_audit_2026-03-26/baseline_current_parser/papers/2409.13738.json`
- Duplicate keys: `0`
- Duplicate rows skipped: `0`
- Duplicate keys with conflicting `published_date`: `(none)`
- Unparseable raw strings:
  - `2006-03`: count `1`, example keys `Fereday2006`
  - `2011-05`: count `1`, example keys `weidlich2011`
  - `2023-04`: count `1`, example keys `vidgof2023large`
  - `2023-05`: count `1`, example keys `li2023_skcoder`
  - `2023-07`: count `1`, example keys `berti2023abstractions`

## 2503.04799

- Input status: `ok`
- Metadata path: `refs/2503.04799/metadata/title_abstracts_metadata.jsonl`
- Detail JSON: `screening/results/publication_date_parse_audit_2026-03-26/baseline_current_parser/papers/2503.04799.json`
- Duplicate keys: `0`
- Duplicate rows skipped: `0`
- Duplicate keys with conflicting `published_date`: `(none)`
- Unparseable raw strings:
  - `1984-04`: count `1`, example keys `articleStft`
  - `1991-10`: count `1`, example keys `anderson1991hcrc`
  - `2010-04`: count `1`, example keys `5453745`
  - `2015-04`: count `1`, example keys `7178964`
  - `2019-11`: count `1`, example keys `Griffin-Lim`
  - `2022-11`: count `1`, example keys `DBLP:conf/ococosda/AryaAMP22`
  - `2023-08`: count `1`, example keys `10229412`
  - `2024-03`: count `1`, example keys `Boulal2024`

## 2507.07741

- Input status: `ok`
- Metadata path: `refs/2507.07741/metadata/title_abstracts_metadata.jsonl`
- Detail JSON: `screening/results/publication_date_parse_audit_2026-03-26/baseline_current_parser/papers/2507.07741.json`
- Duplicate keys: `1`
- Duplicate rows skipped: `1`
- Duplicate keys with conflicting `published_date`: `(none)`
- Unparseable raw strings:
  - `2019-05`: count `3`, example keys `shan_end2end, 8682824, li_bytes_2019`
  - `2017-10`: count `1`, example keys `Zhu_2017_ICCV`
  - `2018-04`: count `1`, example keys `seki_end--end_2018`
  - `2018-12`: count `1`, example keys `emond2018transliteration`
  - `2019-12`: count `1`, example keys `yue_end--end_2019`
  - `2020-02`: count `1`, example keys `dhawan_investigating_2020`
  - `2020-05`: count `1`, example keys `9054138`
  - `2022-10`: count `1`, example keys `mohamed2022self`

## 2507.18910

- Input status: `ok`
- Metadata path: `refs/2507.18910/metadata/title_abstracts_metadata.jsonl`
- Detail JSON: `screening/results/publication_date_parse_audit_2026-03-26/baseline_current_parser/papers/2507.18910.json`
- Duplicate keys: `8`
- Duplicate rows skipped: `8`
- Duplicate keys with conflicting `published_date`: `(none)`
- Unparseable raw strings:
  - `2024-04`: count `1`, example keys `AbdulKhaliq2024`
  - `2024-05`: count `1`, example keys `Ding2024RAGsurvey`

## 2509.11446

- Input status: `ok`
- Metadata path: `refs/2509.11446/metadata/title_abstracts_metadata.jsonl`
- Detail JSON: `screening/results/publication_date_parse_audit_2026-03-26/baseline_current_parser/papers/2509.11446.json`
- Duplicate keys: `0`
- Duplicate rows skipped: `0`
- Duplicate keys with conflicting `published_date`: `(none)`
- Unparseable raw strings:
  - `2018-10`: count `1`, example keys `devlin2019bertpretrainingdeepbidirectional`
  - `2023-11`: count `1`, example keys `Wei2023-ig`
  - `2024-04`: count `1`, example keys `10440574`

## 2510.01145

- Input status: `ok`
- Metadata path: `refs/2510.01145/metadata/title_abstracts_metadata.jsonl`
- Detail JSON: `screening/results/publication_date_parse_audit_2026-03-26/baseline_current_parser/papers/2510.01145.json`
- Duplicate keys: `10`
- Duplicate rows skipped: `10`
- Duplicate keys with conflicting `published_date`: `(none)`
- Unparseable raw strings:
  - `2015-04`: count `1`, example keys `Panayotov2015`
  - `2024-06`: count `1`, example keys `afonja2024performant`
  - `2025-05`: count `1`, example keys `emezue2025naijavoices`

## 2511.13936

- Input status: `ok`
- Metadata path: `refs/2511.13936/metadata/title_abstracts_metadata.jsonl`
- Detail JSON: `screening/results/publication_date_parse_audit_2026-03-26/baseline_current_parser/papers/2511.13936.json`
- Duplicate keys: `1`
- Duplicate rows skipped: `1`
- Duplicate keys with conflicting `published_date`: `(none)`
- Unparseable raw strings:
  - `2017-10`: count `1`, example keys `sutton2017popularity`
  - `2018-09`: count `1`, example keys `reiter2018structured`
  - `2018-12`: count `1`, example keys `kilgour2018fr`
  - `2023-10`: count `1`, example keys `zhou2023beyond`
  - `2025-03`: count `1`, example keys `xu2025qwen2`

## 2601.19926

- Input status: `ok`
- Metadata path: `refs/2601.19926/metadata/title_abstracts_metadata.jsonl`
- Detail JSON: `screening/results/publication_date_parse_audit_2026-03-26/baseline_current_parser/papers/2601.19926.json`
- Duplicate keys: `0`
- Duplicate rows skipped: `0`
- Duplicate keys with conflicting `published_date`: `(none)`
- Unparseable raw strings:
  - `2020-12`: count `4`, example keys `rogers_primer_2020, Warstadt:etal:2020, ettinger_what_2020, kuncoro-etal-2020-syntactic`
  - `2016-12`: count `1`, example keys `Linzen:etal:2016`
  - `2018-10`: count `1`, example keys `Devlin:etal:2019`
