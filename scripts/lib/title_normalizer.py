#!/usr/bin/env python3
"""Title normalization helper used by both clean and oracle flows."""

from __future__ import annotations

import re

try:
    from title_normalization import normalize_title  # type: ignore
except Exception:  # pragma: no cover
    import unicodedata

    _TEX_SPECIAL_REPLACEMENTS = {
        r"\&": " and ",
        r"\%": " percent ",
        r"\_": " ",
        r"\#": " ",
        r"\$": " ",
        r"\{": "",
        r"\}": "",
        "~": " ",
        "@": " at ",
        "&": " and ",
    }

    _FALLBACK_TEX_CMD_RE = re.compile(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?")

    def _strip_outer_wrappers(text: str) -> str:
        text = text.strip()
        changed = True
        while changed:
            changed = False
            if len(text) >= 2 and text[0] == "{" and text[-1] == "}":
                text = text[1:-1].strip()
                changed = True
            elif len(text) >= 2 and text[0] == '"' and text[-1] == '"':
                text = text[1:-1].strip()
                changed = True
        return text

    def normalize_title(text: str) -> str:
        if text is None:
            return ""

        cleaned = _strip_outer_wrappers(text)
        for needle, replacement in _TEX_SPECIAL_REPLACEMENTS.items():
            cleaned = cleaned.replace(needle, replacement)

        cleaned = _FALLBACK_TEX_CMD_RE.sub(" ", cleaned)
        cleaned = cleaned.replace("$", " ")
        cleaned = cleaned.replace("{", "").replace("}", "")

        cleaned = unicodedata.normalize("NFKD", cleaned)
        cleaned = cleaned.encode("ascii", "ignore").decode("ascii")
        cleaned = cleaned.lower()
        cleaned = re.sub(r"[^a-z0-9]+", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned
