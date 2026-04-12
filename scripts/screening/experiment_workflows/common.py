from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL at {path}:{index}: {exc}") from exc
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def safe_text(value: Any) -> str:
    return str(value or "").strip()


def json_text(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def relative_path(path: Path | None, repo_root: Path) -> str | None:
    if path is None:
        return None
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def now_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")


def decision_from_score(score: int) -> str:
    if score >= 4:
        return "include"
    if score <= 2:
        return "exclude"
    return "maybe"


def stage_verdict(stage: str, score: int) -> str:
    return f"{decision_from_score(score)} ({stage}:{score})"


def custom_id(phase: str, paper_id: str, key: str) -> str:
    return f"{phase}__{paper_id}__{key}"


__all__ = [
    "custom_id",
    "decision_from_score",
    "json_text",
    "now_run_id",
    "read_json",
    "read_jsonl",
    "relative_path",
    "safe_text",
    "stage_verdict",
    "write_json",
    "write_jsonl",
]
