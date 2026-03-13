"""Runtime prompt loader for screening reviewers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_RUNTIME_PROMPTS_PATH = (
    Path(__file__).resolve().parents[3] / "runtime_prompts" / "runtime_prompts.json"
)


@dataclass(frozen=True)
class RuntimePrompt:
    backstory: str
    additional_context: Optional[str] = None


@lru_cache(maxsize=4)
def _load_prompt_payload(path_text: str) -> Dict[str, Any]:
    path = Path(path_text)
    if not path.exists():
        raise FileNotFoundError(f"找不到 runtime prompt 檔案：{path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"runtime prompt 檔案格式錯誤（需為 object）：{path}")
    return payload


def _resolve_path(prompts_path: Optional[Path]) -> Path:
    return prompts_path.resolve() if prompts_path else DEFAULT_RUNTIME_PROMPTS_PATH.resolve()


def _to_prompt(node: Any, *, label: str) -> RuntimePrompt:
    if not isinstance(node, dict):
        raise ValueError(f"runtime prompt `{label}` 格式錯誤（需為 object）。")
    backstory = str(node.get("backstory") or "").strip()
    if not backstory:
        raise ValueError(f"runtime prompt `{label}` 缺少 backstory。")
    additional_context_raw = node.get("additional_context")
    additional_context = None
    if additional_context_raw is not None:
        text = str(additional_context_raw).strip()
        additional_context = text if text else None
    return RuntimePrompt(backstory=backstory, additional_context=additional_context)


def load_stage1_junior_prompt(
    reviewer_name: str,
    *,
    prompts_path: Optional[Path] = None,
) -> RuntimePrompt:
    path = _resolve_path(prompts_path)
    payload = _load_prompt_payload(str(path))
    root = payload.get("stage1_junior")
    if not isinstance(root, dict):
        raise ValueError("runtime prompt 檔案缺少 `stage1_junior`。")

    name = (reviewer_name or "").strip()
    role_map = {
        "JuniorNano": "junior_nano",
        "JuniorMini": "junior_mini",
    }
    role_key = role_map.get(name)
    if role_key is None:
        raise ValueError(f"未知的 Stage1 junior reviewer：{reviewer_name}")
    return _to_prompt(root.get(role_key), label=f"stage1_junior.{role_key}")


def load_stage1_senior_prompt(
    prompt_id: str,
    *,
    prompts_path: Optional[Path] = None,
) -> RuntimePrompt:
    path = _resolve_path(prompts_path)
    payload = _load_prompt_payload(str(path))
    normalized = (prompt_id or "").strip()
    allowed = {"stage1_senior_no_marker", "stage1_senior_prompt_tuned"}
    if normalized not in allowed:
        raise ValueError(f"不支援的 Stage1 senior prompt_id：{prompt_id}")
    return _to_prompt(payload.get(normalized), label=normalized)


def load_stage2_fulltext_prompt(
    reviewer_name: str,
    *,
    prompts_path: Optional[Path] = None,
) -> RuntimePrompt:
    path = _resolve_path(prompts_path)
    payload = _load_prompt_payload(str(path))
    root = payload.get("stage2_fulltext")
    if not isinstance(root, dict):
        raise ValueError("runtime prompt 檔案缺少 `stage2_fulltext`。")

    name = (reviewer_name or "").strip()
    role_map = {
        "JuniorNano": "junior_nano",
        "JuniorMini": "junior_mini",
        "SeniorLead": "senior",
    }
    role_key = role_map.get(name)
    if role_key is None:
        raise ValueError(f"未知的 Stage2 reviewer：{reviewer_name}")
    return _to_prompt(root.get(role_key), label=f"stage2_fulltext.{role_key}")
