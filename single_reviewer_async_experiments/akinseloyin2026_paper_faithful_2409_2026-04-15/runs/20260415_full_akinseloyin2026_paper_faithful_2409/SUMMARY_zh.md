# 2409 Paper-Faithful A 摘要

- `paper_id`: `2409.13738`
- `current_authority_k`: `35`
- `single_reviewer_k`: `36`
- `total_cost`: `$1.2112`

## Key Findings

- current-authority threshold 下 F1 最高的是 `mad_raw`，F1=`0.7500`，FN=`0`。
- single-reviewer threshold 下 F1 最高的是 `adj_judge`，F1=`0.7368`。
- ranking MAP 最高的是 `mad_raw`，MAP=`0.4458`，WSS@95=`0.4717`。

## Decision Note

目前最穩的是 `mad_raw`，但它還沒有明確贏過 single-reviewer stage1 baseline。 先不要擴到 stage2，除非你要追的是排序品質而不是 stage1 F1。

## Cost

- `gpt-4.1-mini`: calls=138, input_tokens=325492, output_tokens=64441, cost=$0.2333
- `gpt-5-mini`: calls=207, input_tokens=602183, output_tokens=322323, cost=$0.7952
- `gpt-5.4-nano`: calls=138, input_tokens=325216, output_tokens=94102, cost=$0.1827
