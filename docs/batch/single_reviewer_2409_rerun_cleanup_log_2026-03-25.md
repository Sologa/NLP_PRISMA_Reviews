# 2409 Single Reviewer Rerun Cleanup Log

- 記錄時間：`2026-03-25T17:03:05`
- 原因：對於已有第二遍的模型，只保留第二遍，刪除第一遍本地結果目錄。
- 備註：第一遍已經 push 過，因此只在本地清理，並在此記錄。

| 刪除的第一遍 run_id | 保留的第二遍 run_id | 模型 | 第二遍狀態 | 第二遍 F1 |
| --- | --- | --- | --- | ---: |
| `20260324_2409_rerun_gpt5mini_low` | `20260324_2409_rerun2_gpt5mini_low` | `gpt-5-mini` | `completed` | `0.8571` |
| `20260324_2409_rerun_gpt5nano_low` | `20260324_2409_rerun2_gpt5nano_low` | `gpt-5-nano` | `completed` | `0.8400` |
| `20260324_2409_rerun_gpt54_low` | `20260324_2409_rerun2_gpt54_low` | `gpt-5.4` | `completed` | `0.9130` |
