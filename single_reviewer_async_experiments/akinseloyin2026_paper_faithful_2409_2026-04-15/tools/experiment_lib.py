from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from vendor.src.utils.llm import DEFAULT_PRICING, ModelPriceRegistry, ModelPricing, OpenAIProvider


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        payload = json.loads(stripped)
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def safe_text(value: Any) -> str:
    return str(value or "").strip()


def render_template(template_text: str, context: dict[str, Any]) -> str:
    rendered = template_text
    for key, value in context.items():
        placeholder = "{{" + key + "}}"
        replacement = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)
        rendered = rendered.replace(placeholder, replacement)
    return rendered


def parse_json_response_text(text: str) -> dict[str, Any]:
    stripped = safe_text(text)
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    payload = json.loads(stripped)
    if not isinstance(payload, dict):
        raise ValueError("expected JSON object response")
    return payload


def relative_path(path: Path, repo_root: Path) -> str:
    return str(path.resolve().relative_to(repo_root.resolve()))


def build_openai_provider() -> OpenAIProvider:
    price_table = DEFAULT_PRICING.table
    openai_table = price_table.setdefault("openai", {})
    openai_table["gpt-5.4-nano"] = ModelPricing(input_cost_per_1m=0.20, output_cost_per_1m=1.25)
    pricing = ModelPriceRegistry(price_table=price_table)
    return OpenAIProvider(pricing=pricing)
