from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple


@dataclass(frozen=True)
class TextBlock:
    x0: float
    y0: float
    x1: float
    y1: float
    text: str

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def center_x(self) -> float:
        return (self.x0 + self.x1) / 2.0

    @property
    def center_y(self) -> float:
        return (self.y0 + self.y1) / 2.0


def normalize_extracted_text(text: str) -> str:
    lines = text.replace("\r\n", "\n").split("\n")
    normalized: List[str] = []
    last_blank = False

    for raw_line in lines:
        line = raw_line.rstrip()
        if not line:
            if not last_blank:
                normalized.append("")
            last_blank = True
            continue
        normalized.append(line)
        last_blank = False

    return "\n".join(normalized).strip()


def _normalize_block_text(text: str) -> str:
    cleaned_lines = [line.strip() for line in text.replace("\x00", " ").splitlines() if line.strip()]
    return "\n".join(cleaned_lines).strip()


def _load_text_blocks(page: "fitz.Page") -> List[TextBlock]:
    blocks: List[TextBlock] = []
    for raw in page.get_text("blocks"):
        x0, y0, x1, y1, text, *_rest = raw
        cleaned = _normalize_block_text(text or "")
        if not cleaned:
            continue
        blocks.append(TextBlock(float(x0), float(y0), float(x1), float(y1), cleaned))
    return sorted(blocks, key=lambda block: (block.y0, block.x0, block.y1, block.x1))


def _is_full_width_block(block: TextBlock, *, page_width: float) -> bool:
    page_mid = page_width / 2.0
    if block.x0 < page_mid < block.x1:
        return True
    if block.width >= page_width * 0.60:
        return True
    if abs(block.center_x - page_mid) <= page_width * 0.08 and block.width >= page_width * 0.50:
        return True
    return False


def _render_blocks(blocks: List[TextBlock]) -> str:
    return "\n\n".join(block.text for block in blocks if block.text).strip()


def _render_segment(blocks: List[TextBlock], *, page_width: float) -> str:
    if not blocks:
        return ""

    page_mid = page_width / 2.0
    left_blocks = [block for block in blocks if block.center_x < page_mid]
    right_blocks = [block for block in blocks if block.center_x >= page_mid]

    if left_blocks and right_blocks:
        left_max_x1 = max(block.x1 for block in left_blocks)
        right_min_x0 = min(block.x0 for block in right_blocks)
        gutter_width = right_min_x0 - left_max_x1
        if gutter_width >= page_width * 0.03:
            left_text = _render_blocks(sorted(left_blocks, key=lambda block: (block.y0, block.x0)))
            right_text = _render_blocks(sorted(right_blocks, key=lambda block: (block.y0, block.x0)))
            return "\n\n".join(part for part in (left_text, right_text) if part).strip()

    return _render_blocks(sorted(blocks, key=lambda block: (block.y0, block.x0)))


def _extract_page_text_column_aware(page: "fitz.Page") -> str:
    blocks = _load_text_blocks(page)
    if not blocks:
        return normalize_extracted_text((page.get_text("text") or "").replace("\x00", " "))

    page_width = float(page.rect.width)
    full_width_blocks = [block for block in blocks if _is_full_width_block(block, page_width=page_width)]
    column_blocks = [block for block in blocks if not _is_full_width_block(block, page_width=page_width)]

    if not full_width_blocks:
        return _render_segment(column_blocks, page_width=page_width)

    ordered_parts: List[str] = []
    segment_start = float("-inf")

    for full_block in sorted(full_width_blocks, key=lambda block: (block.y0, block.x0)):
        segment_blocks = [
            block
            for block in column_blocks
            if segment_start <= block.center_y < full_block.y0
        ]
        segment_text = _render_segment(segment_blocks, page_width=page_width)
        if segment_text:
            ordered_parts.append(segment_text)
        ordered_parts.append(full_block.text)
        segment_start = max(segment_start, full_block.y1)

    trailing_blocks = [block for block in column_blocks if block.center_y >= segment_start]
    trailing_text = _render_segment(trailing_blocks, page_width=page_width)
    if trailing_text:
        ordered_parts.append(trailing_text)

    return "\n\n".join(part for part in ordered_parts if part).strip()


def extract_texts_from_pdf(pdf_path: Path) -> Tuple[str, str, str]:
    try:
        import fitz  # PyMuPDF
    except Exception as exc:
        return "", "", f"fitz_import_error:{exc.__class__.__name__}"

    try:
        doc = fitz.open(pdf_path)
    except Exception as exc:
        return "", "", f"pdf_open_error:{exc.__class__.__name__}"

    try:
        page_texts = [_extract_page_text_column_aware(page) for page in doc]
    except Exception as exc:
        doc.close()
        return "", "", f"pdf_extract_error:{exc.__class__.__name__}"

    doc.close()
    full_text = normalize_extracted_text("\n\n".join(text for text in page_texts if text))
    page1_text = normalize_extracted_text(page_texts[0] if page_texts else "")
    return full_text, page1_text, "ok:fitz_blocks_column_aware"
