# 結構化輸出修正策略

- 若 JSON 結構錯誤，優先修正結構，不要改變核心判斷。
- 若 `decision_recommendation` 與 `stage_score` 不一致，必須先修正為一致。
- 若欄位缺漏，補齊必要欄位，不要新增 schema 外欄位。
- 若某項判斷缺乏證據，應改放入 `uncertain_points`，而不是假設證據存在。
