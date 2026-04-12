#!/usr/bin/env python3
"""薄包裝 prompt renderer。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


PLACEHOLDER_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")


def _load_context(path: Path) -> Dict[str, Any]:
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8")
    if suffix == ".json":
        payload = json.loads(text)
    elif suffix in {".yaml", ".yml"}:
        if yaml is None:
            raise ImportError("載入 YAML context 需要 PyYAML。")
        payload = yaml.safe_load(text)
    else:
        raise ValueError(f"不支援的 context 檔案型別：{path}")
    if not isinstance(payload, dict):
        raise ValueError("Context 必須解成 dict。")
    return payload


def _stringify(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, indent=2)
    if value is None:
        return "null"
    return str(value)


def _render(template_text: str, context: Dict[str, Any], *, strict: bool) -> str:
    missing: list[str] = []

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in context:
            missing.append(key)
            return match.group(0)
        return _stringify(context[key])

    rendered = PLACEHOLDER_RE.sub(replace, template_text)
    if strict and missing:
        raise KeyError("缺少 placeholders: " + ", ".join(sorted(set(missing))))
    return rendered


def main() -> int:
    parser = argparse.ArgumentParser(description="使用 JSON/YAML context render prompt template。")
    parser.add_argument("--template", required=True, type=Path)
    parser.add_argument("--context", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--no-strict", action="store_true")
    args = parser.parse_args()

    rendered = _render(
        args.template.read_text(encoding="utf-8"),
        _load_context(args.context),
        strict=not args.no_strict,
    )
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
