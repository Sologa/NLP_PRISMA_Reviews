# Retry Audit

| Phase | Run ID | Batch status | Request count | Success | Failure | Missing | Batch ID | Top errors |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| `stage1_review` | `20260409_probe_2409_gpt54_xhigh_stage1` | `completed` | 69 | 60 | 9 | 0 | `batch_69d78208094881908f6af2c80e1b74f7` | The server had an error while processing your request. Sorry about that! (9) |
| `stage1_review` | `20260410_retry1_gpt54_xhigh_stage1_2409` | `completed` | 9 | 9 | 0 | 0 | `batch_69d9099bb210819094083426220fb9d3` | - |
| `stage2_review` | `20260410_retry1_gpt54_xhigh_stage2_2409` | `completed` | 26 | 11 | 15 | 0 | `batch_69d931ac533c8190833155b9e49cbb30` | You have insufficient permissions for this operation. Missing scopes: model.request. Check that you have the correct role in your organization (Reader, Writer, Owner) and project (Member, Owner), and if you're using a restricted API key, that it has the necessary scopes. (15) |
| `stage2_review` | `20260411_retry2_gpt54_xhigh_stage2_2409` | `completed` | 15 | 15 | 0 | 0 | `batch_69da15ca7b4c8190bd8e398d7ccc58af` | - |
