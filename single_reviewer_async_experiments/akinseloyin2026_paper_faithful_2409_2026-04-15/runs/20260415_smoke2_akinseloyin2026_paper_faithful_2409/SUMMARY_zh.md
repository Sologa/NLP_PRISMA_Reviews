# 2409 Paper-Faithful A 摘要

- `paper_id`: `2409.13738`
- `current_authority_k`: `35`
- `single_reviewer_k`: `36`
- `total_cost`: `$0.0670`

## Key Findings

- current-authority threshold 下 F1 最高的是 `adj_judge`，F1=`0.4000`，FN=`0`。
- single-reviewer threshold 下 F1 最高的是 `adj_judge`，F1=`0.4000`。
- ranking MAP 最高的是 `adj_judge`，MAP=`1.0000`，WSS@95=`0.7000`。

## Decision Note

目前最穩的是 `adj_judge`，但它還沒有明確贏過 single-reviewer stage1 baseline。 先不要擴到 stage2，除非你要追的是排序品質而不是 stage1 F1。

## Cost

- `gpt-4.1-mini`: calls=8, input_tokens=18292, output_tokens=3705, cost=$0.0132
- `gpt-5-mini`: calls=12, input_tokens=32550, output_tokens=17696, cost=$0.0435
- `gpt-5.4-nano`: calls=8, input_tokens=18276, output_tokens=5284, cost=$0.0103
