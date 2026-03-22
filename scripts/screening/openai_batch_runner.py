#!/usr/bin/env python3
"""OpenAI 官方 Batch API 協調層。"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel


def _to_jsonable(payload: Any) -> Any:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(mode="json")
    return payload


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_to_jsonable(payload), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _parse_jsonl_text(text: str | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not text:
        return rows
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        payload = json.loads(stripped)
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _strip_json_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return stripped


def _stringify_metadata(metadata: dict[str, Any] | None) -> dict[str, str]:
    if not metadata:
        return {}
    return {str(key): str(value) for key, value in metadata.items()}


def _extract_message_content(body: dict[str, Any]) -> str:
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("Batch response body 缺少 choices")
    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise ValueError("Batch response body 缺少 message")
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks: list[str] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            text_value = item.get("text")
            if isinstance(text_value, str):
                chunks.append(text_value)
        if chunks:
            return "".join(chunks)
    raise ValueError("無法從 batch response body 擷取 assistant content")


def _normalize_schema_node(node: Any) -> Any:
    if isinstance(node, dict):
        normalized = {}
        for key, value in node.items():
            if key == "default":
                continue
            normalized[key] = _normalize_schema_node(value)
        properties = normalized.get("properties")
        if normalized.get("type") == "object" and isinstance(properties, dict):
            normalized["required"] = list(properties.keys())
            normalized["additionalProperties"] = False
        return normalized
    if isinstance(node, list):
        return [_normalize_schema_node(item) for item in node]
    return node


def build_json_schema_response_format(
    response_model: type[BaseModel],
    *,
    schema_name: str | None = None,
) -> dict[str, Any]:
    schema = _normalize_schema_node(response_model.model_json_schema())
    return {
        "type": "json_schema",
        "json_schema": {
            "name": schema_name or response_model.__name__,
            "strict": True,
            "schema": schema,
        },
    }


@dataclass(frozen=True)
class BatchRequestSpec:
    custom_id: str
    model: str
    body: dict[str, Any]
    response_model: type[BaseModel]
    validator: Callable[[BaseModel], None] | None = None
    context: dict[str, Any] = field(default_factory=dict)


class OpenAIBatchRunner:
    def __init__(self, client: Any, *, poll_interval_sec: float = 30.0) -> None:
        self.client = client
        self.poll_interval_sec = poll_interval_sec

    def serialize_requests(self, specs: list[BatchRequestSpec], *, endpoint: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for spec in specs:
            rows.append(
                {
                    "custom_id": spec.custom_id,
                    "method": "POST",
                    "url": endpoint,
                    "body": spec.body,
                }
            )
        return rows

    def submit_requests(
        self,
        *,
        specs: list[BatchRequestSpec],
        endpoint: str,
        artifact_dir: Path,
        metadata: dict[str, Any] | None = None,
        completion_window: str = "24h",
    ) -> dict[str, Any]:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        input_rows = self.serialize_requests(specs, endpoint=endpoint)
        input_path = artifact_dir / "input.jsonl"
        _write_jsonl(input_path, input_rows)

        with input_path.open("rb") as handle:
            upload = self.client.files.create(file=handle, purpose="batch")
        upload_payload = _to_jsonable(upload)
        _write_json(artifact_dir / "upload_file.json", upload_payload)

        batch = self.client.batches.create(
            input_file_id=upload_payload["id"],
            endpoint=endpoint,
            completion_window=completion_window,
            metadata=_stringify_metadata(metadata),
        )
        batch_payload = _to_jsonable(batch)
        _write_json(artifact_dir / "batch_create.json", batch_payload)
        _write_json(artifact_dir / "batch_latest.json", batch_payload)
        return {
            "input_path": str(input_path),
            "upload_file": upload_payload,
            "batch_create": batch_payload,
        }

    def retrieve_batch(self, batch_id: str, *, artifact_dir: Path | None = None) -> dict[str, Any]:
        payload = _to_jsonable(self.client.batches.retrieve(batch_id))
        if artifact_dir is not None:
            _write_json(artifact_dir / "batch_latest.json", payload)
        return payload

    def wait_until_terminal(
        self,
        batch_id: str,
        *,
        artifact_dir: Path,
        max_wait_minutes: float | None = None,
    ) -> dict[str, Any]:
        started = time.monotonic()
        while True:
            payload = self.retrieve_batch(batch_id, artifact_dir=artifact_dir)
            status = str(payload.get("status") or "")
            if status in {"completed", "failed", "expired", "cancelled"}:
                return payload
            if max_wait_minutes is not None and (time.monotonic() - started) > max_wait_minutes * 60:
                raise TimeoutError(f"等待 batch 超時：{batch_id}")
            time.sleep(self.poll_interval_sec)

    def download_file_text(self, file_id: str | None) -> str | None:
        if not file_id:
            return None
        response = self.client.files.content(file_id)
        text_attr = getattr(response, "text", None)
        if isinstance(text_attr, str):
            return text_attr
        if callable(text_attr):
            text_value = text_attr()
            if isinstance(text_value, str):
                return text_value
        read_attr = getattr(response, "read", None)
        if callable(read_attr):
            data = read_attr()
            if isinstance(data, bytes):
                return data.decode("utf-8")
            if isinstance(data, str):
                return data
        content_attr = getattr(response, "content", None)
        if isinstance(content_attr, bytes):
            return content_attr.decode("utf-8")
        if isinstance(content_attr, str):
            return content_attr
        return None

    def collect_results(
        self,
        *,
        specs: list[BatchRequestSpec],
        batch_payload: dict[str, Any],
        artifact_dir: Path,
    ) -> dict[str, Any]:
        output_text = self.download_file_text(batch_payload.get("output_file_id"))
        error_text = self.download_file_text(batch_payload.get("error_file_id"))
        if output_text is not None:
            (artifact_dir / "output.jsonl").write_text(output_text, encoding="utf-8")
        if error_text is not None:
            (artifact_dir / "error.jsonl").write_text(error_text, encoding="utf-8")

        output_rows = _parse_jsonl_text(output_text)
        error_rows = _parse_jsonl_text(error_text)
        output_by_id = {str(row.get("custom_id")): row for row in output_rows if row.get("custom_id")}
        error_by_id = {str(row.get("custom_id")): row for row in error_rows if row.get("custom_id")}
        spec_by_id = {spec.custom_id: spec for spec in specs}

        successes: list[dict[str, Any]] = []
        failures: list[dict[str, Any]] = []
        missing: list[dict[str, Any]] = []

        for custom_id, spec in spec_by_id.items():
            if custom_id in error_by_id:
                failures.append(
                    {
                        "custom_id": custom_id,
                        "status": "error_file",
                        "context": spec.context,
                        "error": error_by_id[custom_id],
                    }
                )
                continue

            output_row = output_by_id.get(custom_id)
            if output_row is None:
                missing.append(
                    {
                        "custom_id": custom_id,
                        "status": "missing",
                        "context": spec.context,
                    }
                )
                continue

            try:
                response = output_row.get("response")
                if not isinstance(response, dict):
                    raise ValueError("output row 缺少 response")
                status_code = int(response.get("status_code") or 0)
                body = response.get("body")
                if status_code != 200 or not isinstance(body, dict):
                    raise ValueError(f"status_code={status_code}")
                assistant_text = _extract_message_content(body)
                payload = json.loads(_strip_json_fence(assistant_text))
                parsed = spec.response_model.model_validate(payload)
                if spec.validator is not None:
                    spec.validator(parsed)
                successes.append(
                    {
                        "custom_id": custom_id,
                        "status": "ok",
                        "context": spec.context,
                        "assistant_text": assistant_text,
                        "parsed": parsed.model_dump(mode="json"),
                    }
                )
            except Exception as exc:  # noqa: BLE001
                failures.append(
                    {
                        "custom_id": custom_id,
                        "status": "parse_or_validation_failed",
                        "context": spec.context,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                        "raw_output": output_row,
                    }
                )

        payload = {
            "batch_id": batch_payload.get("id"),
            "batch_status": batch_payload.get("status"),
            "successes": successes,
            "failures": failures,
            "missing": missing,
            "output_row_count": len(output_rows),
            "error_row_count": len(error_rows),
        }
        _write_json(artifact_dir / "parsed_results.json", payload)
        return payload
