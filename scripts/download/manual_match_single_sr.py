#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import unicodedata
import urllib.parse
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import requests

try:
    import fitz  # PyMuPDF
except Exception as exc:  # pragma: no cover
    raise SystemExit(f"PyMuPDF (fitz) is required: {exc}")


UA = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
MIN_PDF_BYTES = 5000
REQUEST_TIMEOUT = 25
DOI_RE = re.compile(r"^10\.[^\s/]+/.+$", re.IGNORECASE)
ARXIV_RE = re.compile(r"(?:arxiv\.org/(?:abs|pdf)/)?(\d{4}\.\d{4,5}(?:v\d+)?)(?:\.pdf)?", re.IGNORECASE)


def read_jsonl_by_key(path: Path) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    if not path.exists():
        return out
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            k = str(row.get("key") or "").strip()
            if k:
                out[k] = row
    return out


def norm(s: str) -> str:
    return (s or "").strip()


def clean_field(s: str) -> str:
    s = norm(s)
    s = s.strip("{}\"' ")
    s = re.sub(r"\s+", " ", s)
    return s


def normalize_text(s: str) -> str:
    s = clean_field(s)
    s = unicodedata.normalize("NFKC", s).lower()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def title_main(title: str) -> str:
    t = clean_field(title)
    for sep in [":", " - ", " – ", " — "]:
        if sep in t:
            left = t.split(sep, 1)[0].strip()
            if len(left) >= 12:
                return left
    return t


def extract_title_from_first_page(doc: fitz.Document) -> str:
    if len(doc) == 0:
        return ""
    page = doc[0]
    text_dict = page.get_text("dict")
    candidates: List[Tuple[float, float, str]] = []
    for block in text_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            line_text = "".join(span.get("text", "") for span in spans).strip()
            if not line_text:
                continue
            if len(line_text) < 8:
                continue
            low = normalize_text(line_text)
            if low in {"abstract", "keywords", "index terms"}:
                continue
            max_size = max((float(span.get("size", 0.0)) for span in spans), default=0.0)
            y0 = float(line.get("bbox", [0, 0, 0, 0])[1])
            candidates.append((max_size, -y0, line_text))
    if candidates:
        candidates.sort(reverse=True)
        return clean_field(candidates[0][2])

    lines = [clean_field(x) for x in page.get_text("text").splitlines() if clean_field(x)]
    for ln in lines:
        if len(ln) >= 8:
            return ln
    return ""


def extract_first_page_text(doc: fitz.Document) -> str:
    if len(doc) == 0:
        return ""
    return clean_field(doc[0].get_text("text") or "")


def looks_like_pdf(content: bytes, content_type: str, final_url: str) -> bool:
    ct = (content_type or "").lower()
    u = (final_url or "").lower()
    return content.startswith(b"%PDF-") or "application/pdf" in ct or u.endswith(".pdf") or "/pdf" in u


def normalize_doi(val: str) -> str:
    d = clean_field(val)
    dl = d.lower()
    if dl.startswith("https://doi.org/"):
        d = d.split("doi.org/", 1)[1]
    elif dl.startswith("http://doi.org/"):
        d = d.split("doi.org/", 1)[1]
    elif dl.startswith("doi:"):
        d = d[4:]
    d = d.strip("/ ")
    return d


def maybe_doi(val: str) -> Optional[str]:
    d = normalize_doi(val)
    if d and DOI_RE.match(d):
        return d
    return None


def maybe_arxiv_id(val: str) -> Optional[str]:
    v = clean_field(val)
    if not v:
        return None
    m = ARXIV_RE.search(v)
    if m:
        return m.group(1)
    if re.fullmatch(r"\d{4}\.\d{4,5}(?:v\d+)?", v):
        return v
    return None


def uniq_keep_order(items: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for x in items:
        x = clean_field(x)
        if not x or x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def expand_url_variants(url: str) -> List[str]:
    u = clean_field(url)
    if not u:
        return []
    out = [u]

    # arXiv abs -> pdf
    m_arx = re.search(r"arxiv\.org/abs/(\d{4}\.\d{4,5}(?:v\d+)?)", u, re.IGNORECASE)
    if m_arx:
        out.append(f"https://arxiv.org/pdf/{m_arx.group(1)}.pdf")

    # ACL Anthology landing page -> direct PDF
    if "aclanthology.org/" in u and not u.lower().endswith(".pdf"):
        tail = u.rstrip("/").rsplit("/", 1)[-1]
        if re.fullmatch(r"[A-Za-z0-9\-.]+", tail):
            out.append(f"https://aclanthology.org/{tail}.pdf")
    if "aclweb.org/anthology/" in u:
        tail = u.rstrip("/").rsplit("/", 1)[-1]
        tail = tail[:-4] if tail.lower().endswith(".pdf") else tail
        if re.fullmatch(r"[A-Za-z0-9\-.]+", tail):
            out.append(f"https://aclanthology.org/{tail}.pdf")

    # AAAI OJS article landing -> download endpoint
    m_aaai = re.search(r"ojs\.aaai\.org/index\.php/AAAI/article/view/(\d+)", u, re.IGNORECASE)
    if m_aaai:
        out.append(f"https://ojs.aaai.org/index.php/AAAI/article/view/{m_aaai.group(1)}/pdf")
        out.append(f"https://ojs.aaai.org/index.php/AAAI/article/view/{m_aaai.group(1)}/download")

    # SAGE DOI landing -> direct PDF
    if "journals.sagepub.com/doi/" in u and "/pdf" not in u:
        out.append(u.rstrip("/") + "/pdf")

    # IEEE Xplore document page -> stamp PDF
    m_ieee = re.search(r"ieeexplore\.ieee\.org/document/(\d+)", u, re.IGNORECASE)
    if m_ieee:
        out.append(f"https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber={m_ieee.group(1)}")

    # DOI patterns with deterministic direct PDFs
    md = re.search(r"https?://(?:dx\.)?doi\.org/(10\.[^\\s]+)", u, re.IGNORECASE)
    if md:
        d = normalize_doi(md.group(1))
        d_low = d.lower()
        if d_low.startswith("10.18653/v1/"):
            anth_id = d.split("/", 2)[-1].upper()
            if re.fullmatch(r"[A-Z0-9.-]+", anth_id):
                out.append(f"https://aclanthology.org/{anth_id}.pdf")
        if d_low.startswith("10.1609/aaai.v"):
            m_aaai_doi = re.search(r"\\.(\\d+)$", d)
            if m_aaai_doi:
                aid = m_aaai_doi.group(1)
                out.append(f"https://ojs.aaai.org/index.php/AAAI/article/view/{aid}/pdf")
                out.append(f"https://ojs.aaai.org/index.php/AAAI/article/view/{aid}/download")

    return uniq_keep_order(out)


def collect_oracle_hints(orow: dict) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    doi = None
    arxiv_id = None
    url = None
    if not orow:
        return doi, arxiv_id, url

    if orow.get("arxiv"):
        arxiv_id = maybe_arxiv_id(str(orow.get("arxiv")))

    raw = orow.get("raw") or {}
    local = raw.get("local") if isinstance(raw, dict) else None
    if isinstance(local, dict):
        doi = maybe_doi(str(local.get("doi") or "")) or doi
        arxiv_id = maybe_arxiv_id(str(local.get("eprint") or "")) or arxiv_id
        url = clean_field(str(local.get("url") or "")) or url
        if local.get("archiveprefix") and clean_field(str(local.get("archiveprefix"))).lower() == "arxiv":
            arxiv_id = maybe_arxiv_id(str(local.get("eprint") or "")) or arxiv_id

    return doi, arxiv_id, url


def source_id_to_urls(source_id: str, source: str) -> List[str]:
    sid = clean_field(source_id)
    if not sid:
        return []

    out: List[str] = []
    if sid.startswith("http://") or sid.startswith("https://"):
        out.append(sid)
    d = maybe_doi(sid)
    if d:
        out.extend([
            f"https://doi.org/{d}",
            f"https://dx.doi.org/{d}",
        ])
        if d.startswith("10.1145/"):
            out.append(f"https://dl.acm.org/doi/pdf/{d}?download=true")
        if d.startswith("10.1007/"):
            out.append(f"https://link.springer.com/content/pdf/{d}.pdf")
            out.append(f"https://link.springer.com/chapter/{d}")
    if source == "openalex" and sid.startswith("https://openalex.org/"):
        wid = sid.rsplit("/", 1)[-1]
        if wid:
            out.append(f"https://api.openalex.org/works/{wid}")
    return uniq_keep_order(out)


def doi_special_candidates(doi: str) -> List[str]:
    d = clean_field(doi)
    if not d:
        return []
    out: List[str] = []
    if d.startswith("10.5220/"):
        tail = d.split("/", 1)[1]
        digits = "".join(ch for ch in tail if ch.isdigit())
        pnum = digits.lstrip("0")[:6] if digits else ""
        if pnum:
            out.append(f"https://www.scitepress.org/Papers/2024/{pnum}/{pnum}.pdf")
            out.append(f"https://www.scitepress.org/PublishedPapers/2024/{pnum}/{pnum}.pdf")
    if d.startswith("10.20944/preprints"):
        m = re.search(r"10\.20944/preprints(?P<id>\d+\.\d+)\.v\d+", d, flags=re.IGNORECASE)
        if m:
            out.append(f"https://www.preprints.org/manuscript/{m.group('id')}/v1/download")
    if d.startswith("10.1007/"):
        out.append(f"https://link.springer.com/article/{d}")
        out.append(f"https://link.springer.com/chapter/{d}")
    if d.startswith("10.1145/"):
        out.append(f"https://dl.acm.org/doi/{d}")
    return uniq_keep_order(out)


def fetch_zenodo_candidates(session: requests.Session, source_id: str) -> List[str]:
    sid = clean_field(source_id)
    if not sid:
        return []
    m = re.search(r"\b(\d{6,})\b", sid)
    if not m:
        return []
    rec_id = m.group(1)
    out: List[str] = []
    api_url = f"https://zenodo.org/api/records/{rec_id}"
    try:
        r = session.get(api_url, headers=UA, timeout=12)
        if r.status_code != 200:
            return []
        j = r.json()
    except Exception:
        return []

    files = j.get("files") or []
    for f in files:
        if not isinstance(f, dict):
            continue
        links = f.get("links") or {}
        for k in ["self", "download"]:
            u = clean_field(str(links.get(k) or ""))
            if u:
                out.append(u)
        key = clean_field(str(f.get("key") or ""))
        if key and key.lower().endswith(".pdf"):
            out.append(f"https://zenodo.org/records/{rec_id}/files/{key}?download=1")
    return uniq_keep_order(out)


def fetch_title_search_candidates(session: requests.Session, title: str) -> List[str]:
    t = clean_field(title)
    if len(t) < 8:
        return []

    out: List[str] = []

    # OpenAlex title search
    try:
        r = session.get(
            "https://api.openalex.org/works",
            params={"search": t, "per-page": 5},
            headers=UA,
            timeout=12,
        )
        if r.status_code == 200:
            j = r.json()
            for w in j.get("results") or []:
                if not isinstance(w, dict):
                    continue
                oa = w.get("open_access") or {}
                if oa.get("oa_url"):
                    out.append(str(oa.get("oa_url")))
                primary = w.get("primary_location") or {}
                for k in ["pdf_url", "landing_page_url"]:
                    if primary.get(k):
                        out.append(str(primary.get(k)))
                for loc in w.get("locations") or []:
                    if not isinstance(loc, dict):
                        continue
                    for k in ["pdf_url", "landing_page_url"]:
                        if loc.get(k):
                            out.append(str(loc.get(k)))
    except Exception:
        pass

    # Semantic Scholar title search
    try:
        r = session.get(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            params={"query": t, "limit": 5, "fields": "title,url,openAccessPdf,externalIds"},
            headers=UA,
            timeout=12,
        )
        if r.status_code == 200:
            j = r.json()
            for p in j.get("data") or []:
                if not isinstance(p, dict):
                    continue
                oap = p.get("openAccessPdf") or {}
                if oap.get("url"):
                    out.append(str(oap.get("url")))
                if p.get("url"):
                    out.append(str(p.get("url")))
                ext = p.get("externalIds") or {}
                d = maybe_doi(str(ext.get("DOI") or ""))
                if d:
                    out.append(f"https://doi.org/{d}")
    except Exception:
        pass

    return uniq_keep_order(out)


def fetch_duckduckgo_candidates(session: requests.Session, query: str, max_results: int = 12) -> List[str]:
    q = clean_field(query)
    if len(q) < 6:
        return []

    out: List[str] = []
    try:
        enc_q = urllib.parse.quote_plus(q)
        r = session.get(
            f"https://duckduckgo.com/html/?q={enc_q}",
            headers=UA,
            timeout=14,
        )
        if r.status_code != 200:
            return []
        txt = r.text or ""
        for m in re.finditer(r"uddg=([^&\"'<>\\s]+)", txt):
            try:
                u = urllib.parse.unquote(m.group(1))
            except Exception:
                continue
            u = clean_field(u)
            if u.startswith("http://") or u.startswith("https://"):
                out.append(u)
    except Exception:
        return []

    return uniq_keep_order(out)[:max_results]


def fetch_source_id_api_candidates(session: requests.Session, source: str, source_id: str, doi: Optional[str]) -> List[str]:
    sid = clean_field(source_id)
    out: List[str] = []

    if source == "openalex":
        targets = []
        if sid.startswith("W"):
            targets.append(f"https://api.openalex.org/works/{sid}")
        if sid.startswith("https://openalex.org/"):
            targets.append(sid.replace("https://openalex.org/", "https://api.openalex.org/works/"))
        if doi:
            targets.append(f"https://api.openalex.org/works/https://doi.org/{doi}")
        for t in targets:
            try:
                r = session.get(t, headers=UA, timeout=12)
                if r.status_code != 200:
                    continue
                j = r.json()
                oa = j.get("open_access") or {}
                if oa.get("oa_url"):
                    out.append(str(oa.get("oa_url")))
                primary = j.get("primary_location") or {}
                for k in ["pdf_url", "landing_page_url"]:
                    if primary.get(k):
                        out.append(str(primary.get(k)))
                for loc in j.get("locations") or []:
                    if not isinstance(loc, dict):
                        continue
                    for k in ["pdf_url", "landing_page_url"]:
                        if loc.get(k):
                            out.append(str(loc.get(k)))
            except Exception:
                continue

    if source in {"semantic_scholar", "crossref", "pubmed", "github", "zenodo", "manual"}:
        targets = []
        if sid and not sid.startswith("http"):
            targets.append(sid)
        if doi:
            targets.append(f"DOI:{doi}")
        for pid in targets:
            try:
                r = session.get(
                    f"https://api.semanticscholar.org/graph/v1/paper/{pid}",
                    params={"fields": "url,openAccessPdf,externalIds,title"},
                    headers=UA,
                    timeout=12,
                )
                if r.status_code != 200:
                    continue
                j = r.json()
                oap = j.get("openAccessPdf") or {}
                if oap.get("url"):
                    out.append(str(oap.get("url")))
                if j.get("url"):
                    out.append(str(j.get("url")))
                ext = j.get("externalIds") or {}
                d = maybe_doi(str(ext.get("DOI") or ""))
                if d:
                    out.append(f"https://doi.org/{d}")
            except Exception:
                continue

    return uniq_keep_order(out)


def judge_match(metadata_title: str, metadata_abstract: str, first_page_title: str, first_page_text: str) -> Tuple[str, str]:
    meta_title_n = normalize_text(metadata_title)
    meta_main_n = normalize_text(title_main(metadata_title))
    fp_title_n = normalize_text(first_page_title)
    fp_text_n = normalize_text(first_page_text)

    # Primary title consistency rules (no fuzzy/score-based logic)
    if meta_title_n and meta_title_n in fp_text_n:
        title_ok = True
        title_note = "full_title_found_in_first_page"
    elif meta_main_n and len(meta_main_n) >= 12 and meta_main_n in fp_text_n:
        title_ok = True
        title_note = "main_title_found_in_first_page"
    elif meta_title_n and fp_title_n and (meta_title_n in fp_title_n or fp_title_n in meta_title_n):
        title_ok = True
        title_note = "title_header_consistent"
    elif meta_main_n and fp_title_n and (meta_main_n in fp_title_n or fp_title_n in meta_main_n):
        title_ok = True
        title_note = "main_title_header_consistent"
    else:
        title_ok = False
        title_note = "title_not_consistent_with_metadata"

    if not title_ok:
        return "mismatch", title_note

    # Topic sanity gate when abstract exists: if first-page text is too poor, keep uncertain
    if clean_field(metadata_abstract):
        if len(fp_text_n) < 60:
            return "uncertain", "first_page_text_too_short_for_topic_check"

    return "match", title_note


def fetch_candidate_pdf(session: requests.Session, candidate_url: str) -> Tuple[Optional[bytes], str, str]:
    """Return (pdf_bytes, final_url, reason). reason='ok' when bytes present."""
    u = clean_field(candidate_url)
    if not u:
        return None, u, "empty_candidate"

    if u.startswith("local:"):
        p = Path(u[len("local:") :])
        if not p.exists() or not p.is_file():
            return None, u, "local_file_missing"
        b = p.read_bytes()
        if len(b) < MIN_PDF_BYTES:
            return None, u, "local_file_too_small"
        if not b.startswith(b"%PDF-"):
            return None, u, "local_file_not_pdf"
        return b, u, "ok"

    try:
        r = session.get(u, headers=UA, timeout=REQUEST_TIMEOUT, allow_redirects=True)
    except requests.exceptions.Timeout:
        return None, u, "timeout"
    except Exception as exc:
        return None, u, f"request_error:{exc.__class__.__name__}"

    final_url = clean_field(r.url or u)
    status = int(r.status_code)
    if status >= 400:
        return None, final_url, f"http_{status}"

    content = r.content or b""
    ct = clean_field(r.headers.get("Content-Type", ""))
    if not looks_like_pdf(content, ct, final_url):
        # Try deterministic direct-PDF alternates from resolved landing URLs.
        for alt in expand_url_variants(final_url):
            if alt == final_url:
                continue
            try:
                rr = session.get(alt, headers=UA, timeout=REQUEST_TIMEOUT, allow_redirects=True)
            except Exception:
                continue
            if int(rr.status_code) >= 400:
                continue
            bb = rr.content or b""
            if len(bb) < MIN_PDF_BYTES:
                continue
            ct2 = clean_field(rr.headers.get("Content-Type", ""))
            fu2 = clean_field(rr.url or alt)
            if not looks_like_pdf(bb, ct2, fu2):
                continue
            if not bb.startswith(b"%PDF-"):
                try:
                    _ = fitz.open(stream=bb, filetype="pdf")
                except Exception:
                    continue
            return bb, fu2, "ok"
        return None, final_url, "not_pdf_content"

    if len(content) < MIN_PDF_BYTES:
        return None, final_url, "pdf_too_small"

    if not content.startswith(b"%PDF-"):
        # Some servers return octet-stream; still verify via fitz.
        try:
            _ = fitz.open(stream=content, filetype="pdf")
        except Exception:
            return None, final_url, "invalid_pdf_bytes"

    return content, final_url, "ok"


def build_candidates(
    paper_id: str,
    key: str,
    metadata_row: dict,
    source_row: dict,
    oracle_row: dict,
    out_pdf_path: Path,
    session: requests.Session,
    force_web_search: bool = False,
) -> List[str]:
    cands: List[str] = []

    # Always try the canonical local PDF first, if present.
    # This prevents unnecessary web lookups when a correct file is already available.
    if out_pdf_path.exists() and out_pdf_path.is_file():
        cands.append(f"local:{out_pdf_path.as_posix()}")

    meta_source = clean_field(str(metadata_row.get("source") or source_row.get("source") or ""))
    source_id = clean_field(str(metadata_row.get("source_id") or source_row.get("source_id") or ""))
    meta_title = clean_field(str(metadata_row.get("title") or source_row.get("title") or ""))

    doi_m = maybe_doi(str(metadata_row.get("doi") or ""))
    arxiv_m = maybe_arxiv_id(str(metadata_row.get("arxiv") or ""))
    url_m = clean_field(str(metadata_row.get("url") or ""))

    doi_o, arxiv_o, url_o = collect_oracle_hints(oracle_row)

    doi = doi_m or doi_o or maybe_doi(source_id)
    arxiv_id = arxiv_m or arxiv_o or maybe_arxiv_id(source_id)

    if arxiv_id:
        cands.append(f"https://arxiv.org/pdf/{arxiv_id}.pdf")
        cands.append(f"https://arxiv.org/abs/{arxiv_id}")

    if doi:
        cands.append(f"https://doi.org/{doi}")
        if doi.startswith("10.1145/"):
            cands.append(f"https://dl.acm.org/doi/pdf/{doi}?download=true")
        if doi.startswith("10.1007/"):
            cands.append(f"https://link.springer.com/content/pdf/{doi}.pdf")
            cands.append(f"https://link.springer.com/chapter/{doi}")
        cands.extend(doi_special_candidates(doi))

    if url_m:
        cands.append(url_m)
    if url_o:
        cands.append(url_o)

    cands.extend(source_id_to_urls(source_id, meta_source))
    cands.extend(fetch_source_id_api_candidates(session, meta_source, source_id, doi))
    if meta_source == "zenodo":
        cands.extend(fetch_zenodo_candidates(session, source_id))

    # Restrict title-based search to low-signal cases to avoid unrelated PDF hijacking.
    if (not doi) and (not source_id or source_id.startswith("local:")) and (not arxiv_id) and len(cands) <= 2:
        cands.extend(fetch_title_search_candidates(session, meta_title))

    if force_web_search:
        search_queries: List[str] = []
        if meta_title:
            search_queries.append(f"{meta_title} pdf")
            search_queries.append(meta_title)
        if doi:
            search_queries.append(f"{doi} pdf")
        if key:
            search_queries.append(f"{key} pdf")

        for q in uniq_keep_order(search_queries):
            cands.extend(fetch_duckduckgo_candidates(session, q))

    expanded: List[str] = []
    for c in uniq_keep_order(cands):
        expanded.extend(expand_url_variants(c))
    return uniq_keep_order(expanded)


def ensure_saved_pdf(content: bytes, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)


def process_one_key(
    paper_id: str,
    key: str,
    metadata: Dict[str, dict],
    sources: Dict[str, dict],
    oracle: Dict[str, dict],
    output_root: Path,
    session: requests.Session,
    force_web_search: bool = False,
) -> Dict[str, str]:
    mrow = metadata.get(key)
    srow = sources.get(key, {})
    orow = oracle.get(key, {})
    source = clean_field(str((mrow or {}).get("source") or srow.get("source") or "unknown"))

    out_pdf = output_root / paper_id / f"{key}.pdf"

    if not mrow:
        return {
            "paper_id": paper_id,
            "key": key,
            "source": source or "unknown",
            "chosen_url": "",
            "result": "failed",
            "bytes": "0",
            "first_page_title": "",
            "note": "metadata_missing_for_key",
        }

    metadata_title = clean_field(str(mrow.get("title") or ""))
    metadata_abstract = clean_field(str(mrow.get("abstract") or ""))

    candidates = build_candidates(
        paper_id=paper_id,
        key=key,
        metadata_row=mrow,
        source_row=srow,
        oracle_row=orow,
        out_pdf_path=out_pdf,
        session=session,
        force_web_search=force_web_search,
    )

    uncertain_row: Optional[Dict[str, str]] = None
    mismatch_last_reason = "no_candidate"
    mismatch_last_url = ""

    for cand in candidates:
        pdf_bytes, final_url, fetch_reason = fetch_candidate_pdf(session, cand)
        if pdf_bytes is None:
            mismatch_last_reason = fetch_reason
            mismatch_last_url = final_url or cand
            continue

        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            first_title = extract_title_from_first_page(doc)
            first_text = extract_first_page_text(doc)
            doc.close()
        except Exception as exc:
            mismatch_last_reason = f"pdf_read_error:{exc.__class__.__name__}"
            mismatch_last_url = final_url or cand
            continue

        verdict, verdict_note = judge_match(
            metadata_title=metadata_title,
            metadata_abstract=metadata_abstract,
            first_page_title=first_title,
            first_page_text=first_text,
        )

        row = {
            "paper_id": paper_id,
            "key": key,
            "source": source,
            "chosen_url": final_url or cand,
            "result": verdict,
            "bytes": str(len(pdf_bytes)),
            "first_page_title": clean_field(first_title),
            "note": verdict_note,
        }

        if verdict == "match":
            ensure_saved_pdf(pdf_bytes, out_pdf)
            return row

        if verdict == "uncertain" and uncertain_row is None:
            uncertain_row = row

        mismatch_last_reason = verdict_note
        mismatch_last_url = final_url or cand

    if uncertain_row is not None:
        return uncertain_row

    return {
        "paper_id": paper_id,
        "key": key,
        "source": source,
        "chosen_url": mismatch_last_url,
        "result": "failed",
        "bytes": "0",
        "first_page_title": "",
        "note": mismatch_last_reason,
    }


def write_csv(path: Path, rows: List[Dict[str, str]], fields: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def main() -> int:
    ap = argparse.ArgumentParser(description="Manual single-SR PDF matching with first-page verification.")
    ap.add_argument("--paper-id", required=True)
    ap.add_argument("--keys-file", required=True, type=Path)
    ap.add_argument("--refs-root", default="refs", type=Path)
    ap.add_argument("--oracle-root", default="bib/per_SR_cleaned", type=Path)
    ap.add_argument("--output-root", default="ref_pdfs", type=Path)
    ap.add_argument("--issues-root", default="issues/manual_pdf_match", type=Path)
    ap.add_argument("--force-web-search", action="store_true")
    args = ap.parse_args()

    paper_id = args.paper_id
    keys = [x.strip() for x in args.keys_file.read_text(encoding="utf-8").splitlines() if x.strip()]

    meta_path = args.refs_root / paper_id / "metadata" / "title_abstracts_metadata.jsonl"
    src_path = args.refs_root / paper_id / "metadata" / "title_abstracts_sources.jsonl"
    oracle_path = args.oracle_root / paper_id / "reference_oracle.jsonl"

    metadata = read_jsonl_by_key(meta_path)
    sources = read_jsonl_by_key(src_path)
    oracle = read_jsonl_by_key(oracle_path)

    session = requests.Session()
    session.headers.update(UA)

    rows: List[Dict[str, str]] = []

    for idx, key in enumerate(keys, start=1):
        row = process_one_key(
            paper_id=paper_id,
            key=key,
            metadata=metadata,
            sources=sources,
            oracle=oracle,
            output_root=args.output_root,
            session=session,
            force_web_search=args.force_web_search,
        )
        rows.append(row)

        line = (
            f"[{row['paper_id']}] {row['key']} | {row['source']} | {row['chosen_url']} | "
            f"{row['result']} | {row['bytes']} | {row['first_page_title']} | {row['note']}"
        )
        print(line, flush=True)

        if idx % 10 == 0:
            print(f"PROGRESS {idx}/{len(keys)}", flush=True)

    fields = ["paper_id", "key", "source", "chosen_url", "result", "bytes", "first_page_title", "note"]
    rows_csv = args.issues_root / f"{paper_id}_rows.csv"
    unresolved_csv = args.issues_root / f"{paper_id}_unresolved.csv"
    summary_md = args.issues_root / f"{paper_id}_summary.md"

    write_csv(rows_csv, rows, fields)

    unresolved = [r for r in rows if r.get("result") in {"failed", "uncertain"}]
    write_csv(unresolved_csv, unresolved, fields)

    match_count = sum(1 for r in rows if r.get("result") == "match")
    failed_count = sum(1 for r in rows if r.get("result") == "failed")
    uncertain_count = sum(1 for r in rows if r.get("result") == "uncertain")

    reason_counter = Counter(r.get("note", "") for r in rows if r.get("result") in {"failed", "uncertain"})
    top3 = reason_counter.most_common(3)

    unresolved_keys = [r.get("key", "") for r in unresolved]

    with summary_md.open("w", encoding="utf-8") as f:
        f.write(f"# Manual PDF Match Summary: {paper_id}\n\n")
        f.write(f"- total_keys: {len(keys)}\n")
        f.write(f"- match: {match_count}\n")
        f.write(f"- failed: {failed_count}\n")
        f.write(f"- uncertain: {uncertain_count}\n\n")
        f.write("## Failed/Uncertain Reason Top3\n")
        if top3:
            for reason, count in top3:
                f.write(f"- {reason}: {count}\n")
        else:
            f.write("- none\n")
        f.write("\n## Unresolved Keys\n")
        if unresolved_keys:
            for k in unresolved_keys:
                f.write(f"- {k}\n")
        else:
            f.write("- none\n")

    print("=== FINAL SUMMARY ===")
    print(f"match={match_count} failed={failed_count} uncertain={uncertain_count}")
    print(f"rows_csv={rows_csv.as_posix()}")
    print(f"unresolved_csv={unresolved_csv.as_posix()}")
    print(f"summary_md={summary_md.as_posix()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
