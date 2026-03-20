#!/usr/bin/env python3
"""Thin prompt renderer for external template files."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict

try:
    import yaml
except ImportError:  # pragma: no cover - optional dependency in .venv runtime
    yaml = None


PLACEHOLDER_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")


def _load_context(path: Path) -> Dict[str, Any]:
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8")
    if suffix == ".json":
        payload = json.loads(text)
    elif suffix in {".yaml", ".yml"}:
        if yaml is None:
            raise ImportError("PyYAML is required to load YAML context files.")
        payload = yaml.safe_load(text)
    else:
        raise ValueError(f"Unsupported context file type: {path}")
    if not isinstance(payload, dict):
        raise ValueError("Context must decode to an object/dict.")
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
    missing = []

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in context:
            missing.append(key)
            return match.group(0)
        return _stringify(context[key])

    rendered = PLACEHOLDER_RE.sub(replace, template_text)
    if strict and missing:
        unique = ", ".join(sorted(set(missing)))
        raise KeyError(f"Missing placeholders: {unique}")
    return rendered


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a prompt template with a JSON/YAML context.")
    parser.add_argument("--template", required=True, type=Path, help="Path to the template file.")
    parser.add_argument("--context", required=True, type=Path, help="Path to the JSON/YAML context file.")
    parser.add_argument("--output", type=Path, default=None, help="Optional output file path.")
    parser.add_argument("--no-strict", action="store_true", help="Allow unresolved placeholders.")
    args = parser.parse_args()

    template_path = args.template.resolve()
    context_path = args.context.resolve()
    template_text = template_path.read_text(encoding="utf-8")
    context = _load_context(context_path)
    rendered = _render(template_text, context, strict=not args.no_strict)

    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
