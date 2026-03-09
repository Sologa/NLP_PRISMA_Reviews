#!/usr/bin/env python3
"""BibTeX parsing helpers shared by clean + oracle builders."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class BibEntry:
    entry_type: str
    key: str | None
    fields: Dict[str, str]
    raw_fields: Dict[str, str]


class BibTexError(RuntimeError):
    pass


def _is_escaped(text: str, idx: int) -> bool:
    """Return True when text[idx] is escaped by an odd number of backslashes."""
    backslashes = 0
    j = idx - 1
    while j >= 0 and text[j] == "\\":
        backslashes += 1
        j -= 1
    return (backslashes % 2) == 1


def _find_matching(text: str, open_idx: int, open_char: str, close_char: str) -> int:
    level = 0
    for idx in range(open_idx, len(text)):
        ch = text[idx]
        if ch == open_char:
            level += 1
        elif ch == close_char:
            level -= 1
            if level == 0:
                return idx
    raise BibTexError("unbalanced entry delimiter")


def _split_key_and_body(body: str) -> Tuple[str, str]:
    depth = 0
    in_quote = False
    escape = False
    for idx, ch in enumerate(body):
        if in_quote:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_quote = False
        else:
            if ch == '"' and not _is_escaped(body, idx):
                in_quote = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                if depth > 0:
                    depth -= 1
            elif ch == "," and depth == 0:
                return body[:idx].strip(), body[idx + 1 :].strip()

    raise BibTexError("missing entry key or field body")


def _parse_value_expression(body: str, start: int) -> Tuple[str, int]:
    depth = 0
    in_quote = False
    escape = False
    idx = start
    while idx < len(body):
        ch = body[idx]
        if in_quote:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_quote = False
        else:
            if ch == '"' and not _is_escaped(body, idx):
                in_quote = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                if depth > 0:
                    depth -= 1
            elif ch == "," and depth == 0:
                break
        idx += 1
    return body[start:idx].strip(), idx


def _split_concat_parts(expr: str) -> List[str]:
    parts: List[str] = []
    buf: List[str] = []
    depth = 0
    in_quote = False
    escape = False
    for idx, ch in enumerate(expr):
        if in_quote:
            buf.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_quote = False
            continue

        if ch == '"' and not _is_escaped(expr, idx):
            in_quote = True
            buf.append(ch)
            continue
        if ch == "{":
            depth += 1
            buf.append(ch)
            continue
        if ch == "}" and depth > 0:
            depth -= 1
            buf.append(ch)
            continue
        if ch == "#" and depth == 0:
            part = "".join(buf).strip()
            if part:
                parts.append(part)
            buf = []
            continue
        buf.append(ch)

    part = "".join(buf).strip()
    if part:
        parts.append(part)
    return parts


def _eval_expr(expr: str, string_macros: Dict[str, str]) -> str:
    parts = _split_concat_parts(expr)
    if not parts:
        return ""

    values: List[str] = []
    for part in parts:
        piece = part.strip()
        if not piece:
            continue
        if piece.startswith("{") and piece.endswith("}"):
            values.append(piece[1:-1])
        elif piece.startswith('"') and piece.endswith('"'):
            values.append(piece[1:-1])
        else:
            values.append(string_macros.get(piece.lower(), piece))
    return "".join(values).strip()


def _parse_fields(body: str, string_macros: Dict[str, str]) -> Tuple[Dict[str, str], Dict[str, str]]:
    fields: Dict[str, str] = {}
    raw_fields: Dict[str, str] = {}
    idx = 0

    while idx < len(body):
        while idx < len(body) and body[idx] in "\n\r\t ,":
            idx += 1
        if idx >= len(body):
            break

        start = idx
        while idx < len(body) and (body[idx].isalnum() or body[idx] in "_-:"):
            idx += 1
        name = body[start:idx].strip().lower()
        if not name:
            break

        while idx < len(body) and body[idx].isspace():
            idx += 1
        if idx >= len(body) or body[idx] != "=":
            while idx < len(body) and body[idx] != ",":
                idx += 1
            if idx < len(body):
                idx += 1
            continue

        idx += 1
        while idx < len(body) and body[idx].isspace():
            idx += 1

        expr, idx = _parse_value_expression(body, idx)
        raw_fields[name] = expr
        fields[name] = _eval_expr(expr, string_macros) if expr else ""

        if idx < len(body) and body[idx] == ",":
            idx += 1

    return fields, raw_fields


def parse_bibtex(text: str) -> List[BibEntry]:
    entries: List[BibEntry] = []
    string_macros: Dict[str, str] = {}
    idx = 0

    while idx < len(text):
        at_pos = text.find("@", idx)
        if at_pos == -1:
            break
        idx = at_pos + 1
        while idx < len(text) and text[idx].isspace():
            idx += 1

        start = idx
        while idx < len(text) and text[idx].isalpha():
            idx += 1
        entry_type = text[start:idx].strip().lower()
        if not entry_type:
            continue

        while idx < len(text) and text[idx].isspace():
            idx += 1
        if idx >= len(text) or text[idx] not in "({":
            continue

        open_char = text[idx]
        close_char = ")" if open_char == "(" else "}"
        open_idx = idx
        close_idx = _find_matching(text, open_idx, open_char, close_char)
        body = text[open_idx + 1 : close_idx]
        idx = close_idx + 1

        if entry_type in {"comment", "preamble"}:
            continue

        if entry_type == "string":
            fields, _ = _parse_fields(body, string_macros)
            for key, value in fields.items():
                if key:
                    string_macros[key.lower()] = value
            continue

        try:
            key, field_body = _split_key_and_body(body)
        except BibTexError:
            continue

        fields, raw_fields = _parse_fields(field_body, string_macros)
        entries.append(BibEntry(entry_type=entry_type, key=key, fields=fields, raw_fields=raw_fields))

    return entries
