# OpenAI Batch API 實作說明與最小改動方案

日期: 2026-03-21  
狀態: 設計說明，尚未實作

本文件說明如何在 `NLP_PRISMA_Reviews` 中導入 OpenAI 官方 Batch API，並聚焦於「最小 blast radius」的實作路徑。

## 1. 先講結論

- 目前這個 repo 沒有實作 OpenAI 官方 Batch API。
- 原始 `AUTOSR-SDSE` repo 也沒有實作 OpenAI 官方 Batch API。
- 兩邊現有的 `chat_batch()` / `read_pdf_batch()` 是本地 wrapper 的逐筆迴圈，不是 `client.batches.create(...)`。
- 兩邊現有的 `chat_async()` 與 experiment scripts 裡的 `AsyncOpenAI + asyncio.Semaphore + gather()` 是本地並發，不是 OpenAI Batch job。
- 最小改動的第一步，不應該先動 shared runtime 或 vendored `llm.py` 的語意，而應先在離線 experiment scripts 上做。
- 最適合先落地的目標是:
  - `fulltext_direct_experiments/fulltext_direct_experiment_v1_all4_2026-03-19/tools/run_experiment.py`
  - 然後才是 `qa_first_experiments/*/tools/run_experiment.py`

## 2. 目前 codebase 的真實狀態

### 2.1 這個 repo 與原始 AUTOSR-SDSE 都沒有官方 Batch API

我已比對目前 repo 與原始 `AUTOSR-SDSE` 的下列檔案，內容是 byte-identical:

- `scripts/screening/vendor/src/utils/llm.py`
- `scripts/screening/vendor/src/utils/openai_web_search.py`
- `scripts/screening/vendor/src/utils/structured_web_search_pipeline.py`
- `AUTOSR-SDSE/src/utils/llm.py`
- `AUTOSR-SDSE/src/utils/openai_web_search.py`
- `AUTOSR-SDSE/src/utils/structured_web_search_pipeline.py`

也就是說，這個 repo 目前沿用的是同一套 OpenAI 呼叫抽象。

### 2.2 目前 repo 裡名為 `batch` 的東西，其實是本地 loop

在 `scripts/screening/vendor/src/utils/llm.py`:

- `chat_batch()` 會逐筆跑 `_chat_request(...)`
- `read_pdf_batch()` 會逐檔跑 `_pdf_request(...)`
- 真正送出的 API 仍然是:
  - `self._client.responses.create(...)`
  - `self._async_client.responses.create(...)`
  - `self._client.files.create(..., purpose="assistants")`

也就是:

1. 沒有 `client.batches.create(...)`
2. 沒有 `files.create(..., purpose="batch")`
3. 沒有 `input_file_id`
4. 沒有 `completion_window`
5. 沒有 `output_file_id` / `error_file_id`

### 2.3 `batch_discount = 0.5` 不是官方 Batch API 實作

`scripts/screening/vendor/src/utils/llm.py` 目前有:

- `batch_discount: float = 0.5`
- `mode="batch"`

這代表目前 shared provider 只是把「本地多筆呼叫」在 usage/cost 記帳上標成 batch 模式，並沒有真的建立 OpenAI Batch job。

這個差異很重要，否則之後很容易誤判成「repo 已經支援 Batch API」。

### 2.4 新 experiment scripts 目前也是本地 async，不是 Batch API

目前幾個新腳本都直接用 `AsyncOpenAI`:

- `qa_first_experiments/.../tools/run_experiment.py`
- `fulltext_direct_experiments/.../tools/run_experiment.py`

它們的核心模式是:

- `self.client.beta.chat.completions.parse(...)`
- `asyncio.Semaphore(concurrency)`
- `asyncio.gather(...)`

這些都屬於同步 API 的批量並發，不是官方 Batch job。

## 3. OpenAI 官方 Batch API 目前要求什麼

以下內容已對照 OpenAI 官方文件，日期為 2026-03-21。

### 3.1 標準流程

官方 Batch API 的標準流程是:

1. 先準備 `.jsonl` 輸入檔
2. 每一行是一筆 request
3. 每一筆 request 都必須有唯一 `custom_id`
4. 先上傳該檔案，`purpose="batch"`
5. 再用 `client.batches.create(...)` 建立 batch job
6. 用 `batches.retrieve(...)` 或 `batches.list(...)` 查狀態
7. 完成後用 `output_file_id` 下載成功結果
8. 如有失敗，用 `error_file_id` 下載錯誤結果

### 3.2 目前官方文件的重要限制

- 支援的 endpoint 包含:
  - `/v1/responses`
  - `/v1/chat/completions`
  - `/v1/embeddings`
  - `/v1/completions`
  - `/v1/moderations`
  - `/v1/images/generations`
  - `/v1/images/edits`
  - `/v1/videos`
- 單一 input file 只能包含單一 model 的 requests。
- `completion_window` 目前只能設成 `24h`。
- Batch API 的輸出順序不保證與輸入順序一致，必須用 `custom_id` 對回去。
- 每個 batch 最多 `50,000` requests。
- 每個 batch input file 最大 `200 MB`。
- 每小時最多建立 `2,000` 個 batches。
- Batch API 有獨立 rate-limit pool，不會消耗一般同步 API 的同一池額度。
- 官方文件明確寫明: 相比同步 API，Batch API 有 `50%` 成本折扣。
- output file 會在 batch 完成後 `30` 天自動刪除。
- batch 若超過 24 小時仍未完成，會進入 `expired`；已完成部分仍可下載，且完成部分仍會計費。

### 3.3 目前官方狀態下，這個 repo 使用的模型與路徑是可行的

依 2026-03-21 官方 model 頁面，像 `gpt-4.1-mini` 與 `gpt-5-nano` 都有:

- Batch endpoint
- Chat Completions endpoint
- Structured outputs 支援

這代表目前 experiment scripts 採用的模型族群，原則上可以走 Batch API。

## 4. 設計原則: 不要把 Batch API 當成 `LLMRunner.call()` 的透明替代品

這是最重要的實作判斷。

### 4.1 為什麼不能直接把單次 call 偷換成 Batch

目前的程式結構大多是:

1. render prompt
2. 立刻送 API
3. 立刻拿回 parsed 結果
4. 依照結果決定下一步 prompt 或是否需要 senior

但官方 Batch API 是:

1. 先蒐集一整批 request
2. 一次提交
3. 等待 batch 完成
4. 下載結果
5. 再做後續決策

也就是說，Batch API 是「phase-level job orchestration」，不是「single-call transport swap」。

### 4.2 推論: `beta.chat.completions.parse(...)` 不應直接沿用到 Batch 路徑

這一點是根據目前 SDK 使用方式與 Batch guide 推得的實作結論:

- `beta.chat.completions.parse(...)` 是 SDK 的便利封裝，適合即時 request-response。
- Batch API 要求你先把 request body 序列化進 `.jsonl`。
- 因此在 Batch 路徑中，應改為:
  - 手動建立 request body
  - 手動帶入 `response_format`
  - 下載結果後再用現有的 Pydantic model 做本地驗證

換句話說:

- prompt rendering 可以沿用
- Pydantic schema 可以沿用
- validator 可以沿用
- 但 `parse(...)` 這個即時 helper 不應該是 Batch implementation 的核心

## 5. 這個 repo 的最小改動方案

### 5.1 第一原則: 先新增 helper，不先改 shared provider 語意

第一步建議新增一個 repo-local helper，而不是直接改:

- `scripts/screening/vendor/src/utils/llm.py`

原因:

1. 那份 code 是 vendored AUTOSR-SDSE，同步上游時比較容易衝突。
2. 現有 `chat_batch()` 已經有既有語意，直接改成官方 Batch job 會讓名稱與實際行為突變。
3. shared runtime 還有 `read_pdfs()` / file-upload path，這不是 Batch API 最小落地點。

### 建議新增位置

優先建議新增:

- `scripts/screening/openai_batch_runner.py`

而不是先動 vendor。

這樣可以把 blast radius 限縮在本 repo 自己的 orchestration code。

### 5.2 helper 應負責的事情

建議 `scripts/screening/openai_batch_runner.py` 負責:

- 接收一組 logical requests
- 產生 `.jsonl`
- 上傳 `purpose="batch"`
- 建立 `client.batches.create(...)`
- 輪詢狀態
- 下載 `output_file_id` / `error_file_id`
- 以 `custom_id` 對回原始 request
- 解析 assistant output
- 用既有 Pydantic model 做本地驗證
- 產生 artifact 供重跑與審計

### 建議的資料結構

```python
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class BatchRequestSpec:
    custom_id: str
    model: str
    endpoint: str
    body: dict[str, Any]
    response_model: type[Any]
    validator: Callable[[Any], None] | None
    context: dict[str, Any]
```

### 建議的 artifact 輸出

建議每個 batch job 都落盤，避免之後無法追蹤:

```text
<result_dir>/batch_jobs/<phase>/<model>/
  input.jsonl
  batch_create.json
  batch_latest.json
  output.jsonl
  error.jsonl
  parsed_results.json
  manifest.json
```

這樣做的好處:

- 能 resume
- 能審核 request 與 result 是否對齊
- 能回頭分析失敗樣式
- 能對照成本與 completed/failed counts

## 6. 第一個應該改哪個 script

### 6.1 首選: `fulltext_direct_experiment_v1_all4_2026-03-19`

最適合先做 PoC 的腳本是:

- `fulltext_direct_experiments/fulltext_direct_experiment_v1_all4_2026-03-19/tools/run_experiment.py`

原因:

1. 它是離線批跑，不要求即時回應。
2. 它沒有先碰 PDF upload 的特殊路徑。
3. 它的依賴圖相對簡單:
   - 兩個 junior
   - 視情況再送 senior
4. 它的 output schema 比 QA-first 簡單。
5. 它最接近「Phase A -> Phase B」的標準 batch 工作流。

### 6.2 這個腳本的最小改動方式

不要嘗試讓 `_review_record()` 內部仍然逐筆 await API，只把 transport 偷換成 batch。  
那樣會卡在 control flow 上。

最小可行的重構是:

1. 保留目前 async 路徑不動
2. 新增 `--api-mode {async,batch}`，預設仍是 `async`
3. 新增一組 phase-level 函式

建議新增的函式形狀:

- `_build_junior_batch_specs(...)`
- `_run_junior_batch_phase(...)`
- `_build_senior_batch_specs(...)`
- `_run_senior_batch_phase(...)`
- `_merge_batch_outputs_into_rows(...)`

### 6.3 這個腳本在 batch 模式下的流程

建議流程:

1. 先載入所有 records 與 fulltext resolution
2. 對所有 eligible records 建立 `JuniorNano` batch specs
3. 對所有 eligible records 建立 `JuniorMini` batch specs
4. 分 model 各提交一個 batch
5. 下載結果並用現有 `JuniorReviewOutput` + validator 做本地驗證
6. 依 junior 分數決定哪些 records 需要 senior
7. 只對這些 ambiguous records 建立 senior batch specs
8. 提交 senior batch
9. 合併 junior/senior 結果，沿用既有 `_derive_final_verdict(...)`
10. 照原本格式輸出 review results 與 F1 report

### 6.4 哪些現有邏輯可以原封不動

以下邏輯基本上都可以保留:

- prompt templates
- `render_prompt`
- `JuniorReviewOutput` / `SeniorReviewOutput`
- `_validate_junior_output(...)`
- `_validate_senior_output(...)`
- `_derive_final_verdict(...)`
- metrics evaluation
- result JSON 結構

也就是說，真正要改的是「調度層」，不是「判斷邏輯層」。

## 7. QA-first scripts 的最小改動方案

### 7.1 QA-first 可以做，但不應該當第一刀

QA-first 系列腳本更複雜，因為它不是單純:

- juniors -> optional senior

而是多個 phase 串起來，例如:

- QA
- synthesis
- criteria evaluation
- senior adjudication

而且有些 phase 之間真的有資料依賴。

### 7.2 QA-first 的正確 batch 化方式

QA-first 不應該以 record 為單位 batch，而應該以「phase + model」為單位 batch。

也就是像這樣切:

1. `JuniorNano QA` 全部 records 一個 batch
2. `JuniorMini QA` 全部 records 一個 batch
3. `Synthesis` 一個或多個 batch
4. `Criteria evaluation` 一個或多個 batch
5. `Senior` 只針對需要 senior 的 records 再送 batch

### 7.3 QA-first 的最小重構原則

不要把每個 `LLMRunner.call()` 都改成「可能 queue、可能 flush、可能等待 batch」。  
這樣會把控制流弄得很難維護。

建議做法是:

- 保留 `LLMRunner.call()` 給 `async` 模式
- 另外新增 phase runner，專門負責:
  - build specs
  - submit batch
  - collect outputs
  - local parse/validate

## 8. shared provider 應該怎麼改，才不會踩雷

### 8.1 不建議第一步直接改 `chat_batch()`

不建議直接把:

- `scripts/screening/vendor/src/utils/llm.py::chat_batch()`

改成官方 Batch API，原因是:

1. 現在這個名字已經表示「本地逐筆 batch wrapper」。
2. 改完後行為會從「立即返回 List[LLMResult]」變成「提交離線 job 再等待」，語意不相容。
3. shared provider 目前還服務其他路徑，不應一開始就做 breaking semantic change。

### 8.2 如果將來要加到 shared provider，應該用新名字

將來若真的要在 shared provider 層支援官方 Batch API，建議加新的明確方法，例如:

- `submit_batch_job(...)`
- `collect_batch_job(...)`
- `chat_batch_job(...)`

而不是覆蓋既有 `chat_batch()`。

## 9. 與 `topic_pipeline.py` / `read_pdfs()` 有關的判斷

目前 `scripts/screening/vendor/src/pipelines/topic_pipeline.py` 的 `read_pdfs()` 路徑，是把多個 PDF 上傳後一次送進 `responses.create(...)`。

這條路徑暫時不建議納入第一波 Batch API 改造，原因:

1. 它的主要問題不是大量同質文字 request，而是 file-input orchestration。
2. 它不是目前最主要的 API 成本熱點。
3. 它不是最小改動路徑。

第一波 PoC 應該先只處理「純文字 prompt + structured output」的批跑工作。

## 10. 一個實際可落地的 helper 骨架

下面是建議的最小骨架，不是完整實作。

```python
from __future__ import annotations

import json
import time
from pathlib import Path
from openai import OpenAI


class OpenAIBatchRunner:
    def __init__(self, client: OpenAI, poll_interval_sec: float = 30.0) -> None:
        self.client = client
        self.poll_interval_sec = poll_interval_sec

    def write_input_jsonl(self, path: Path, requests: list[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            for row in requests:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def submit(self, *, input_jsonl: Path, endpoint: str, metadata: dict | None = None) -> dict:
        uploaded = self.client.files.create(file=input_jsonl.open("rb"), purpose="batch")
        batch = self.client.batches.create(
            input_file_id=uploaded.id,
            endpoint=endpoint,
            completion_window="24h",
            metadata=metadata or {},
        )
        return batch.model_dump()

    def wait_until_terminal(self, batch_id: str) -> dict:
        while True:
            batch = self.client.batches.retrieve(batch_id)
            payload = batch.model_dump()
            status = payload["status"]
            if status in {"completed", "failed", "expired", "cancelled"}:
                return payload
            time.sleep(self.poll_interval_sec)

    def download_file_text(self, file_id: str | None) -> str | None:
        if not file_id:
            return None
        return self.client.files.content(file_id).text
```

## 11. structured output 在 Batch 模式下的建議做法

這個 repo 目前 heavily 依賴:

- Pydantic model
- `beta.chat.completions.parse(...)`
- 本地 validator

Batch 模式下建議改成:

1. request body 仍送 Chat Completions
2. 在 `body` 中帶入 structured output 所需的 `response_format`
3. 下載結果後，取出 assistant content
4. `json.loads(...)`
5. `response_model.model_validate(...)`
6. 再跑現有 validator

### 建議的 request line 形狀

```json
{
  "custom_id": "paper-2409__juniornano__record-0001",
  "method": "POST",
  "url": "/v1/chat/completions",
  "body": {
    "model": "gpt-5-nano",
    "messages": [
      {"role": "user", "content": "<rendered prompt>"}
    ],
    "response_format": {
      "type": "json_schema",
      "json_schema": {
        "name": "JuniorReviewOutput",
        "strict": true,
        "schema": {}
      }
    }
  }
}
```

注意:

- 上面 `response_format` 的實際欄位形狀，實作時應再核對當下官方 Structured Outputs 文件。
- 但整體方向是正確的: Batch 模式下要自己序列化 request body，而不是依賴 SDK 的 `parse(...)` helper 幫你做即時解析。

## 12. 實作時建議加入的 CLI 參數

建議在第一個 PoC 腳本加入:

```text
--api-mode async|batch
--batch-poll-interval 30
--batch-artifact-dir <path>
--resume-batch
--batch-max-wait-minutes 1440
```

其中:

- `--api-mode async` 保持目前預設行為
- `--api-mode batch` 才啟用官方 Batch API
- `--resume-batch` 允許重跑時直接接續既有 batch artifact

## 13. 實作順序建議

### 第 1 步

只做一個 PoC:

- `fulltext_direct_experiment_v1_all4_2026-03-19/tools/run_experiment.py`

目標:

- juniors 改為 batch
- senior 改為 batch
- 結果 JSON 結構不變
- metrics output 不變

### 第 2 步

確認以下都正常:

- F1 不變或可接受
- validator failure rate 不異常
- batch error file 可解析
- 成本與速度有實際改善

### 第 3 步

再把同樣模式移植到:

- `qa_first_experiments/*/tools/run_experiment.py`

### 第 4 步

只有當 phase-based batch orchestration 已經穩定後，才考慮是否把能力上提到 shared provider。

## 14. 這份設計的核心判斷

一句話總結:

> 在這個 repo 裡，OpenAI Batch API 最小改動的正確切入點，不是改 single-call wrapper，而是新增一個 repo-local batch orchestration helper，先套在離線 experiment scripts 的 phase boundary 上。

如果一開始直接動:

- shared provider
- vendored AUTOSR-SDSE runtime
- `read_pdfs()` / file-input path

那都不是最小改動，風險也更高。

## 15. 官方文件來源

以下是本文件對照的官方來源:

- OpenAI Batch API guide  
  `https://developers.openai.com/api/docs/guides/batch`
- OpenAI Batch API reference  
  `https://developers.openai.com/api/reference/resources/batches`
- OpenAI Files API reference  
  `https://developers.openai.com/api/reference/resources/files/methods/create`
- OpenAI Cost optimization guide  
  `https://developers.openai.com/api/docs/guides/cost-optimization`
- GPT-4.1 mini model page  
  `https://developers.openai.com/api/docs/models/gpt-4.1-mini`
- GPT-5 nano model page  
  `https://developers.openai.com/api/docs/models/gpt-5-nano`
