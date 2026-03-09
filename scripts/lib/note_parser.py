#!/usr/bin/env python3
"""Heuristic note parsing for PRISMA BibTeX reconstruction."""

from __future__ import annotations

import re
from typing import Dict, List, Optional


def _normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _strip_metadata_brackets(note: str) -> str:
    note = re.sub(r"\[(?:doi|medline|accessed|pmid|pmcid)\s*:[^\]]+\]", "", note, flags=re.IGNORECASE)
    # Remove generic bracket notes often from PDF extraction.
    note = re.sub(r"\[[^\]]+\]", "", note)
    return _normalize_space(note)


def _clean_title_segment(segment: str) -> str:
    segment = segment.strip()
    segment = re.sub(r"\(\s*", "(", segment)
    segment = re.sub(r"\s*\)", ")", segment)
    segment = re.sub(r"^[\-–—,:;]+|[\-–—,:;]+$", "", segment)
    return segment.strip()


def _is_short_org_token(seg: str) -> bool:
    compact = re.sub(r"[\W_]+", "", seg)
    if len(compact) < 2 or len(compact) > 25:
        return False
    if not compact.isalpha() and not compact.isupper():
        return False
    return compact.isupper()


def _looks_like_author(seg: str) -> bool:
    text = seg.replace("\\&", " ").replace("&", " ").strip()
    low = seg.lower()
    if not seg or len(seg) < 6:
        if re.fullmatch(r"^[a-zÀ-ÖØ-öø-ÿ]\.??$", low.strip()):
            return True
        if re.search(r"^[a-zÀ-ÖØ-öø-ÿ]+,\s*[a-z](?:\.\s*)?$", low):
            return True
        if re.search(r"^[a-zÀ-ÖØ-öø-ÿ]+\s+[a-z]\.??\s*$", low):
            return True
        return False
    if re.search(r"\(\s*\d{4}", seg):
        return False

    has_et_al = "et al" in low
    comma_count = text.count(",")
    and_count = " and " in low or " & " in low
    if has_et_al and comma_count >= 1:
        return True
    if and_count and comma_count >= 1:
        return True
    if comma_count >= 2 and any(ch.isupper() for ch in seg[:10]):
        return True
    if re.search(r"[A-Za-zÀ-ÖØ-öø-ÿ]+\s*,\s*[A-Z](?:\.[A-Za-z]?)?\s*$", text, flags=re.IGNORECASE):
        return True
    if re.search(r"^\w+,\s*[A-Z]{1,4}\.?$", text):
        return True
    return False


def _looks_like_org_segment(seg: str) -> bool:
    text = seg.strip().strip(" .;,")
    if not text or len(text) > 65:
        return False
    if not re.search(r"[A-Za-zÀ-ÖØ-öø-ÿ]", text):
        return False
    if "," in text or " and " in text.lower() or "\\&" in text or "&" in text:
        return False
    if "." in text and re.search(r"\bdoi\b", text, flags=re.IGNORECASE):
        return False
    if _is_short_org_token(text):
        return True
    if re.search(r"\.[a-z]{2,3}\b", text.lower()):
        return True
    if re.search(
        r"\b(center|centre|association|institute|office|agency|commission|organization|organisation|group|department|authority|society|university|ministry|hospital|center|service|centre)\b",
        text.lower(),
    ):
        return True

    tokens = [t for t in re.split(r"[\s-]+", text) if t]
    if not tokens or len(tokens) > 5:
        return False

    word_types: List[str] = []
    for token in tokens:
        if not token.isalpha():
            return False
        if token.isupper() and len(token) >= 2:
            word_types.append("acronym")
        elif re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿ]{1,3}", token):
            word_types.append("acronym")
        elif token[0].isupper() and token[1:].islower():
            word_types.append("title")
        else:
            return False

    if not word_types:
        return False
    return all(t in {"acronym", "title"} for t in word_types) and len(tokens) <= 4


def _likely_author_segment(seg: str) -> bool:
    if _looks_like_author(seg) and len(seg) <= 55:
        return True
    return False


def _looks_like_title_segment(seg: str) -> bool:
    if _is_junk_segment(seg):
        return False
    if _likely_author_segment(seg) or _looks_like_journal_segment(seg):
        return False
    return len(seg.strip()) >= 8


def _looks_like_author_block(text: str) -> bool:
    txt = text.strip()
    if not txt:
        return False
    low = txt.lower()
    if "http" in low or "doi:" in low or "url" in low or "arxiv" in low or "preprint" in low:
        return False
    if _is_short_org_token(txt):
        return False
    if re.search(r"\bet\s*al\b", low):
        return True
    if " and " in low or "\\&" in low or "&" in low:
        return True
    if "," in txt:
        return True
    if re.search(r"\b[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ'-]+\s+[A-Z]{1,4}(?:\.[A-Za-z]{0,3})*", txt):
        return True
    if re.search(r"\b[A-Za-zÀ-ÖØ-öø-ÿ'-]+\s*,\s*[A-Z]\.?", txt):
        return True
    return False


def _extract_leading_author_block(note: str) -> tuple[str, str]:
    m = re.match(r"^\s*(.+?)\.\s+(.*)$", note)
    if not m:
        return "", note
    lead = _clean_title_segment(m.group(1))
    rest = m.group(2).strip()
    if not _looks_like_author_block(lead):
        return "", note
    return lead, rest


def _looks_like_journal_segment(seg: str) -> bool:
    low = seg.lower()
    if not seg:
        return False
    if re.fullmatch(r"\s*\(?\s*(?:19|20)\d{2}\s*\)?\.?\s*", low):
        return False
    if re.search(r"\bpp?\b", low):
        return False
    if any(tok in low for tok in [" press ", " arxiv ", " nature ", " proc ", " symposium ", " meeting "]):
        return True

    words = seg.split()
    if len(words) <= 3 and seg[0].isupper() and len(seg) >= 4:
        return False if _looks_like_author(seg) else True

    if len(words) <= 5 and re.search(r"\b\d{1,4}\b", seg):
        return True
    if re.search(r"\b\d{1,4}\s*[,)]", seg):
        if len(words) <= 8:
            return True
        return False
    return False


def _is_junk_segment(segment: str) -> bool:
    if not segment:
        return True
    low = segment.lower().strip(" .;")
    if not low:
        return True
    if len(low) < 4:
        return True
    if re.fullmatch(r"\d{4}", low):
        return True
    if re.search(r"\bhttps?://", low) or "http" in low:
        return True
    if low.startswith("doi:") or low.startswith("pmid") or low.startswith("accessed"):
        return True
    if re.fullmatch(r"\d{4}[a-z]?(?:\)|,)?", low):
        return True
    if low.startswith("pp") or low.startswith("p.") or low.startswith("pages"):
        return True
    if re.search(r"\(presented at\b", low):
        return True
    if low.startswith("in:"):
        return True
    if re.fullmatch(r"\s*[\d\-–]+\s*", low):
        return True
    return False


def _strip_urls(text: str) -> str:
    text = re.sub(r"(?i)\bhttps?://\S+", "", text)
    text = re.sub(r"(?i)\bwww\.[A-Za-z0-9./?=_-]+\b", "", text)
    return text


def _looks_like_author_fragment(seg: str) -> bool:
    s = seg.lower().strip(" .;,:")
    if not s:
        return False
    if s in {"et al", "et al."}:
        return True
    if re.fullmatch(r"[a-z]\.?.?", s):
        return True
    if re.fullmatch(r"[a-z]\.[a-z]\.?", s):
        return True
    if len(s) <= 2:
        return True
    if re.fullmatch(r"[a-zÀ-ÖØ-öø-ÿ]+,?\s*[a-z]?\.", s):
        return True
    return False


def _strip_ampersand_author_prefix(segment: str) -> str:
    text = segment.strip()
    m = re.match(r"^\\?\&\s*[^,]+,\s*[A-Za-zÀ-ÖØ-öø-ÿ]\.?,?\s*(?P<rest>.*)$", text, flags=re.IGNORECASE)
    if m:
        if not m.group("rest").strip():
            return ""
        return m.group("rest").strip()
    return text


def _looks_like_journal_snippet(text: str) -> bool:
    t = _normalize_space(text or "")
    if not t:
        return False
    if re.search(r"\b\d{1,4}\s*,\s*[A-Za-z]?\d+[\-–—]\d+\s*\(\d{4}", t):
        return True
    if re.search(r"^[A-Za-z]{2,8}\s+\d{1,4}\s*,\s*\d+[\-–—]\d+", t):
        return True
    if re.search(r"\(\s*(?:19|20)\d{2}\s*\)?\s*$", t):
        return True
    return False


def _safe_year_from_text(text: str) -> Optional[str]:
    if not text:
        return None
    years = re.findall(r"(?:19|20)\d{2}", text)
    if not years:
        return None
    return years[-1]


def extract_doi_from_text(note: str, fields: Dict[str, str]) -> Optional[str]:
    if "doi" in fields and fields["doi"]:
        return fields["doi"].strip().strip("{}").strip()

    candidates: List[str] = []

    for m in re.finditer(r"\bdoi:\s*(10\.[0-9][^\s\]\),;}]*)", note, flags=re.IGNORECASE):
        candidates.append(m.group(1).strip(".,;()[]{} "))

    for m in re.finditer(r"https?://(?:dx\.)?doi\.org/([0-9][^\s\]\),;}]*)", note, flags=re.IGNORECASE):
        candidates.append(m.group(1).strip(".,;()[]{} "))

    if not candidates:
        for m in re.finditer(r"\b(10\.[0-9]{4,9}/[^\s\]\),;}]*)", note):
            candidates.append(m.group(1).strip(".,;()[]{} "))

    dedup: List[str] = []
    seen = set()
    for c in candidates:
        if not c:
            continue
        n = c.strip().rstrip(".")
        if n.lower().startswith("http"):
            continue
        if n not in seen:
            dedup.append(n)
            seen.add(n)

    if dedup:
        return dedup[0]

    if "url" in fields and fields["url"] and "10." in fields["url"]:
        m = re.search(r"(10\.[0-9][^/\s]+/[^\s]+)", fields["url"])
        if m:
            return m.group(1).strip(". ,;()[]{} ")

    return None


def _extract_title_from_note(note: str, strict_title: bool = False) -> tuple[str, str]:
    if not note:
        return ("", "missing_note")

    note = _normalize_space(note)
    note = note.replace("\n", " ")
    note = _strip_metadata_brackets(note)
    note = _strip_urls(note)
    note = re.sub(r"^\s*[A-Za-zÀ-ÖØ-öø-ÿ]\.\s*(?:\\&\s*|&\s*)?", "", note)

    if not note:
        return ("", "empty_after_cleanup")

    note_no_in = re.split(r"\b[Ii]n:\s+", note, maxsplit=1)[0].strip()
    note_no_in = re.sub(r"\bURL:\s*https?://\S+", "", note_no_in, flags=re.IGNORECASE)
    note_no_in = re.sub(r"\bPreprint\s+at\s+https?://\S+", "", note_no_in, flags=re.IGNORECASE)
    note_no_in = re.sub(r"\bPreprint\s+\S+", "", note_no_in, flags=re.IGNORECASE)
    note_no_in = _strip_urls(note_no_in)
    note_no_in = _normalize_space(note_no_in)

    segments = [_normalize_space(seg).strip(" .") for seg in re.split(r"\.\s+", note_no_in) if _normalize_space(seg)]
    if not segments:
        if strict_title:
            return ("", "missing_segments")
        return ("", "missing_segments")

    etal = re.search(r"\bet\s*al\.?", note_no_in, flags=re.IGNORECASE)
    if etal and etal.end() < len(note_no_in):
        after = note_no_in[etal.end() :].lstrip(" .,:;")
        after_segments = [_normalize_space(s) for s in re.split(r"\.\s+", after) if _normalize_space(s)]
        for seg in after_segments:
            seg = _clean_title_segment(_strip_ampersand_author_prefix(seg))
            if _is_junk_segment(seg) or _looks_like_author_fragment(seg) or _looks_like_journal_segment(seg):
                continue
            if len(seg) >= 8:
                seg = re.sub(r"\(?\b(?:19|20)\d{2}\)?$", "", seg).strip()
                if seg:
                    return (seg, "from_after_authors")

    candidate = ""
    reason = "fallback_prefix"

    if len(segments) >= 2 and _is_short_org_token(segments[0]) and _looks_like_title_segment(segments[1]):
        candidate = _clean_title_segment(segments[1])
        if candidate:
            return (candidate[:180], "from_org_lead")

    if _is_short_org_token(segments[0]) and len(segments) > 2 and segments[1].lower() in {"presented", "presented at"}:
        if _looks_like_title_segment(segments[2]):
            candidate = _clean_title_segment(segments[2])
            if candidate:
                return (candidate[:180], "from_org_lead")

    lead_author, remainder = _extract_leading_author_block(note_no_in)
    if lead_author and remainder:
        lead_title, lead_reason = _extract_title_from_note(remainder, strict_title=False)
        if lead_title and lead_reason not in {"strict_missing", "missing_segments"}:
            return (lead_title, "from_after_authors")

    start = 0
    if segments and _likely_author_segment(segments[0]):
        while start < len(segments) and _likely_author_segment(segments[start]):
            start += 1
        while start < len(segments) and _looks_like_author_fragment(segments[start]):
            start += 1
        if start > 0 and start < len(segments) and _looks_like_author_fragment(segments[start - 1]):
            start = max(start, 1)

    if len(segments) >= 2:
        for idx in range(start, len(segments)):
            seg = _clean_title_segment(_strip_ampersand_author_prefix(segments[idx]))
            if _is_junk_segment(seg) or _likely_author_segment(seg) or _looks_like_journal_segment(seg):
                continue
            if _looks_like_author_fragment(seg):
                continue
            if len(seg) < 8 and re.fullmatch(r"[A-Za-z]{1,6}", seg):
                continue
            candidate = seg
            reason = "from_after_authors"
            break

    if not candidate and len(segments) >= 1:
        first = _clean_title_segment(segments[0])
        if not _is_junk_segment(first) and not _likely_author_segment(first):
            if _looks_like_author_fragment(first):
                reason = "from_first_segment_fragment"
            else:
                candidate = _clean_title_segment(_strip_ampersand_author_prefix(first))
                candidate = re.sub(r"\(?\b(?:19|20)\d{2}\)?$", "", candidate).strip()
                if candidate:
                    reason = "from_first_segment"
                    return (candidate[:180], reason)

        if not candidate:
            for seg in segments[1:]:
                seg = _clean_title_segment(seg)
                if not seg:
                    continue
                if _is_junk_segment(seg):
                    continue
                seg = _strip_ampersand_author_prefix(seg)
                seg = re.sub(r"\(?\b(?:19|20)\d{2}\)?$", "", seg).strip()
                if _looks_like_author_fragment(seg) or _likely_author_segment(seg) or _looks_like_journal_segment(seg):
                    continue
                candidate = seg
                reason = "from_later_weak"
                break

            if not candidate:
                non_empty = [_clean_title_segment(seg) for seg in segments if _clean_title_segment(seg)]
                if non_empty:
                    candidate = non_empty[0][:180]
                    reason = "fallback_first_clean_segment"

    if not candidate and strict_title:
        return ("", "strict_missing")

    if not candidate:
        return ("", reason)

    candidate = re.sub(r"\s{2,}", " ", candidate).strip()
    if not candidate:
        return ("", reason)

    return (candidate, reason)


def parse_note_to_fields(note: str, prefer_fields: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    prefer_fields = prefer_fields or {}
    raw = note or ""
    clean_note = _strip_metadata_brackets(_normalize_space(raw))
    cleaned = re.sub(r"\bURL:\s*https?://\S+", "", clean_note, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bPreprint\s+at\s+https?://\S+", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bPreprint\s+", "", cleaned, flags=re.IGNORECASE)
    cleaned = _strip_urls(cleaned)
    cleaned = cleaned.replace("\u00ad", "")

    segments = [_normalize_space(s) for s in re.split(r"\.\s+", cleaned) if _normalize_space(s)]
    fields: Dict[str, str] = {
        "author_raw": "",
        "title": "",
        "journal": "",
        "volume": "",
        "number": "",
        "pages": "",
        "year": "",
        "publisher": "",
        "note_cleaned": clean_note,
    }

    leading_author, leading_rest = _extract_leading_author_block(cleaned)
    if leading_author:
        author_raw = leading_author
        lead_segments = [_normalize_space(s) for s in re.split(r"\.\s+", leading_rest) if _normalize_space(s)]
        for seg in lead_segments:
            if _looks_like_author_fragment(seg):
                author_raw += " " + seg
                continue
            if re.search(r"\bet\s+al\.?$", seg.lower()):
                author_raw += " et al"
                break
            break
        title, reason = _extract_title_from_note(leading_rest, strict_title=False) if leading_rest else ("", "from_author_prefix")
        if not title:
            title, reason = _extract_title_from_note(cleaned, strict_title=False)
    else:
        title, reason = _extract_title_from_note(cleaned, strict_title=False)
        author_raw = ""
        for seg in segments[:4]:
            if _likely_author_segment(seg):
                author_raw = seg
                break

    fields["title"] = title
    fields["_title_reason"] = reason

    title_cleaned = _clean_title_segment(title)
    needs_repair = bool(title_cleaned and (len(title_cleaned) <= 2 or _looks_like_journal_snippet(title_cleaned)))
    if not needs_repair and title_cleaned and len(title_cleaned.split()) <= 1 and len(title_cleaned) > 2 and "'" not in title_cleaned:
        needs_repair = False

    if needs_repair:
        for seg in segments:
            seg = _clean_title_segment(seg)
            if not seg or seg == title_cleaned:
                continue
            if len(seg) <= 3:
                continue
            if _is_junk_segment(seg) or _looks_like_journal_snippet(seg):
                continue
            if _looks_like_author_fragment(seg) or _likely_author_segment(seg) or _looks_like_journal_segment(seg):
                continue
            title = seg
            reason = "from_title_repair"
            break
        fields["title"] = title
        fields["_title_reason"] = reason

    if not author_raw and segments:
        prefix: List[str] = []
        for seg in segments:
            if _likely_author_segment(seg) or _looks_like_author_fragment(seg):
                prefix.append(seg)
            else:
                break
        if prefix:
            author_raw = " ".join(prefix)

    if not author_raw and segments:
        for seg in segments[:3]:
            if _looks_like_org_segment(seg):
                author_raw = seg.rstrip(" .")
                break

    fields["author_raw"] = author_raw

    body_for_meta = cleaned
    if title:
        body_for_meta = body_for_meta.replace(title, "")

    journal_guess = ""
    volume = ""
    number = ""
    pages = ""
    year = _safe_year_from_text(body_for_meta) or prefer_fields.get("year", "")

    year_positions = list(re.finditer(r"(19|20\d{2})", body_for_meta))
    candidate_text = body_for_meta
    if year_positions:
        last_year = year_positions[-1]
        candidate_text = body_for_meta[: last_year.start()].strip()
        if not year:
            year = last_year.group(0)

    for seg in segments:
        if not seg or seg == title:
            continue
        if not journal_guess and _looks_like_journal_segment(seg):
            journal_guess = re.sub(r"\b(Epub|Preprint|online|posted)\b.*", "", seg, flags=re.IGNORECASE).strip(" .,")

        m = re.search(
            r"(?P<journal>.+?)\s+(?P<vol>\d{1,4}[a-zA-Z]?)\s*(?:\((?P<num>\d{1,4})\))?\s*,?\s*(?P<pages>\d+[\-–—]\d+|e?\d+)?$",
            seg,
        )
        if m and not journal_guess:
            journal_guess = m.group("journal").strip(" ,")
            volume = m.group("vol") or volume
            number = m.group("num") or number
            pages = m.group("pages") or pages

    if not pages:
        m = re.search(r"\b(\d+)\s*[,;:]\s*([A-Za-z]?\d+[\-–—]\d+|e?\d+)\b", candidate_text)
        if not m:
            m = re.search(r"\b(\d+)\s*;\s*([A-Za-z]?\d+[\-–—]\d+|e?\d+)\b", candidate_text)
        if m:
            volume = m.group(1)
            pages = m.group(2)

    if not journal_guess and candidate_text:
        journal_guess = re.sub(r"\s*\d+[\-–—\w\.,\s]*$", "", candidate_text).strip(" ,.;")

    fields["journal"] = re.sub(r"\s{2,}", " ", journal_guess).strip(", ;.")
    fields["volume"] = volume.strip()
    fields["number"] = number.strip()
    fields["pages"] = pages.strip()
    fields["year"] = (fields["year"].strip() if fields["year"] else "") or (year or "")

    if "organization" in prefer_fields:
        fields["publisher"] = prefer_fields.get("organization", "").strip()

    return fields


def _normalize_author_name(token: str) -> str:
    token = token.strip(" ")
    if not token:
        return token
    if token.lower() in {"et al", "et al."}:
        return "et al"
    token = re.sub(r"\s*[,;]$", "", token)

    if "," in token:
        parts = [t.strip() for t in token.split(",", 1)]
        if len(parts) == 2 and parts[0] and parts[1]:
            return f"{parts[0]}, {parts[1]}".strip()

    m = re.match(
        r"^([A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ'-]+)\s+((?:[A-Za-z]{1,4}(?:\.[A-Za-z]?)?)(?:\s+[A-Za-z]{1,4}(?:\.[A-Za-z]?)?)*)$",
        token,
        flags=re.IGNORECASE,
    )
    if m:
        return f"{m.group(1)}, {m.group(2)}".strip()
    return token


def _split_author_tokens(author_text: str) -> List[str]:
    text = author_text.strip()
    if not text:
        return []
    has_et_al = False
    if re.search(r"\bet\s+al\.?", text.lower()):
        has_et_al = True
        text = re.split(r"\bet\s+al\.?", text, flags=re.IGNORECASE)[0].strip().rstrip(",; ")

    text = text.replace("\\&", " and ").replace("&", " and ")
    raw_tokens: List[str] = []
    for token in re.split(r"\s+and\s+", text):
        token = token.strip()
        if not token:
            continue
        if "," in token and re.search(r"\s*,\s*[A-Za-zÀ-ÖØ-öø-ÿ]", token):
            pieces = [p.strip() for p in token.split(",") if p.strip()]
            if len(pieces) == 2:
                raw_tokens.append(f"{pieces[0]}, {pieces[1]}")
            else:
                raw_tokens.extend([p.strip() for p in token.split(",") if p.strip()])
            continue
        raw_tokens.append(token)

    if has_et_al:
        raw_tokens.append("et al")

    merged: List[str] = []
    i = 0
    while i < len(raw_tokens):
        tok = raw_tokens[i]
        if "," in tok and re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿ]+\s*,\s*[A-Z]{1,5}(?:\.?\s*)?$", tok):
            merged.append(tok)
            i += 1
            continue
        if i + 1 < len(raw_tokens) and re.match(r"^[A-Za-zÀ-ÖØ-öø-ÿ]+$", tok) and re.match(r"^[A-Za-zÀ-ÖØ-öø-ÿ'-]+$", raw_tokens[i + 1]):
            merged.append(f"{tok}, {raw_tokens[i+1]}")
            i += 2
            continue
        merged.append(tok)
        i += 1
    return merged


def normalize_author_block(author_raw: str) -> str:
    if not author_raw:
        return ""
    names = _split_author_tokens(author_raw)
    normalized: List[str] = []
    for name in names:
        nm = _normalize_author_name(name)
        if nm:
            normalized.append(nm)
    if not normalized:
        return ""
    return " and ".join(normalized)


def extract_title_from_note(note: str, strict_title: bool = False) -> tuple[str, str]:
    return _extract_title_from_note(note, strict_title=strict_title)
