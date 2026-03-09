#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import html
import json
import os
import re
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import requests

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

MIN_VALID_PDF_BYTES = 8000
REQ_TIMEOUT = int(os.getenv("MANUAL_RETRY_REQ_TIMEOUT", "25"))
UA = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}

FORCED_URLS = {
    "CottonCS24": ["https://osf.io/preprints/edarxiv/mrz8h/download"],
    "McKeown82": ["https://aclanthology.org/P82-1028.pdf"],
    "Okoli15": ["https://chitu.okoli.org/media/pro/research/pubs/Okoli2015CAIS.pdf"],
    "teshite2023afan": [
        "https://onlinelibrary.wiley.com/doi/pdf/10.1155/2023/9959015",
        "https://research.rug.nl/files/129315450/1_s2_0_S2405844023016912_main.pdf",
    ],
    "n_atox_evaluating_nodate": [
        "https://d197for5662m48.cloudfront.net/documents/publicationstatus/22580887/preprint_pdf/90f4211d7b2f504c2ddb6c13e3e0d4c5.pdf",
    ],
    "de2008stanford": ["https://nlp.stanford.edu/software/dependencies_manual.pdf"],
    "ramanantsoa2023voxmg": ["https://openreview.net/pdf?id=zbAPDsBkGGb"],
    "Miao2024NephrologyRAG": ["https://www.mdpi.com/1648-9144/60/3/445/pdf"],
    "Harrington_Its_2022": [
        "https://static1.squarespace.com/static/5928b37020099e2f4bf8b485/t/6214189a1ae204287520a989/1645484186968/its%2Bkind%2Bof%2Blike%2Bcode-switching.pdf",
    ],
    "winograd1972automatic": [
        "https://www.preprints.org/manuscript/202303.0122/v1/download",
        "https://pdfs.semanticscholar.org/7f10/5bd370bf937058fc494b6b3fb1e73459ce10.pdf",
    ],
    "riefer2016mining": ["https://www.tom-thaler.de/publications/RieferThalerTernis2016_Text2ModelMining.pdf"],
    "graves2005framewise": [
        "https://www.cs.toronto.edu/~graves/nn_2005.pdf",
        "https://www.cs.toronto.edu/~graves/ijcnn_2005.pdf",
    ],
}


def norm(s: str) -> str:
    return (s or "").strip()


def normalize_doi(doi: str) -> str:
    d = norm(doi).strip("{}\"")
    dl = d.lower()
    if dl.startswith("https://doi.org/"):
        d = d.split("doi.org/", 1)[1]
    elif dl.startswith("http://doi.org/"):
        d = d.split("doi.org/", 1)[1]
    elif dl.startswith("doi:"):
        d = d[4:]
    return d.strip()


def clean_title_query(title: str) -> str:
    t = norm(title).replace("{", "").replace("}", "")
    t = re.sub(r"\s+", " ", t)
    if len(t) > 240:
        t = t[:240]
    return t


def token_set(s: str) -> set[str]:
    s = re.sub(r"[^a-z0-9]+", " ", (s or "").lower())
    return {w for w in s.split() if len(w) >= 4}


def title_match(expected: str, text: str) -> bool:
    if not expected or not text:
        return True
    a = token_set(expected)
    if len(a) < 3:
        return True
    b = token_set(text)
    overlap = len(a & b)
    return overlap >= 2


def classify_non_pdf(content: bytes, text_hint: str) -> str:
    t = (text_hint or "").lower()
    if any(k in t for k in ["sign in", "log in", "institutional access", "purchase", "subscribe", "access through your institution"]):
        return "need_login"
    return "non_pdf"


def is_probable_pdf(content: bytes, content_type: str, final_url: str) -> bool:
    ct = (content_type or "").lower()
    url = (final_url or "").lower()
    return content.startswith(b"%PDF-") or "application/pdf" in ct or url.endswith(".pdf")


def fetch_openalex_candidates(session: requests.Session, source_id: str = "", doi: str = "") -> List[str]:
    out: List[str] = []
    targets = []
    if source_id and source_id.startswith("W"):
        targets.append(f"https://api.openalex.org/works/{source_id}")
    if doi:
        targets.append(f"https://api.openalex.org/works/https://doi.org/{doi}")
    for t in targets:
        try:
            r = session.get(t, headers=UA, timeout=12)
            if r.status_code != 200:
                continue
            j = r.json()
        except Exception:
            continue
        oa = j.get("open_access") or {}
        if oa.get("oa_url"):
            out.append(norm(oa.get("oa_url")))
        primary = j.get("primary_location") or {}
        for k in ["pdf_url", "landing_page_url"]:
            if primary.get(k):
                out.append(norm(primary.get(k)))
        for loc in j.get("locations") or []:
            if isinstance(loc, dict):
                for k in ["pdf_url", "landing_page_url"]:
                    if loc.get(k):
                        out.append(norm(loc.get(k)))
    return out


def fetch_s2_candidates(session: requests.Session, source_id: str = "", doi: str = "") -> List[str]:
    out: List[str] = []
    ids = []
    if source_id and source_id != "":
        ids.append(source_id)
    if doi:
        ids.append(f"DOI:{doi}")
    for pid in ids:
        url = f"https://api.semanticscholar.org/graph/v1/paper/{pid}?fields=url,openAccessPdf,externalIds,title"
        try:
            r = session.get(url, headers=UA, timeout=12)
            if r.status_code != 200:
                continue
            j = r.json()
        except Exception:
            continue
        oap = j.get("openAccessPdf") or {}
        if oap.get("url"):
            out.append(norm(oap.get("url")))
        if j.get("url"):
            out.append(norm(j.get("url")))
    return out


def fetch_openalex_title_candidates(session: requests.Session, title: str) -> List[str]:
    out: List[str] = []
    q = clean_title_query(title)
    if len(q) < 12:
        return out
    try:
        r = session.get(
            "https://api.openalex.org/works",
            params={"search": q, "per-page": "5"},
            headers=UA,
            timeout=12,
        )
        if r.status_code != 200:
            return out
        j = r.json()
    except Exception:
        return out
    for w in j.get("results") or []:
        if not isinstance(w, dict):
            continue
        disp = norm(w.get("display_name"))
        if disp and not title_match(q, disp):
            continue
        oa = w.get("open_access") or {}
        if oa.get("oa_url"):
            out.append(norm(oa.get("oa_url")))
        primary = w.get("primary_location") or {}
        for k in ["pdf_url", "landing_page_url"]:
            if primary.get(k):
                out.append(norm(primary.get(k)))
        for loc in w.get("locations") or []:
            if isinstance(loc, dict):
                for k in ["pdf_url", "landing_page_url"]:
                    if loc.get(k):
                        out.append(norm(loc.get(k)))
    return out


def fetch_s2_title_candidates(session: requests.Session, title: str) -> List[str]:
    out: List[str] = []
    q = clean_title_query(title)
    if len(q) < 12:
        return out
    try:
        r = session.get(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            params={"query": q, "limit": "5", "fields": "title,url,openAccessPdf,externalIds"},
            headers=UA,
            timeout=12,
        )
        if r.status_code != 200:
            return out
        j = r.json()
    except Exception:
        return out
    for p in j.get("data") or []:
        if not isinstance(p, dict):
            continue
        pt = norm(p.get("title"))
        if pt and not title_match(q, pt):
            continue
        oap = p.get("openAccessPdf") or {}
        if oap.get("url"):
            out.append(norm(oap.get("url")))
        if p.get("url"):
            out.append(norm(p.get("url")))
        ext = p.get("externalIds") or {}
        doi = normalize_doi(norm(ext.get("DOI")))
        if doi:
            out.append(f"https://doi.org/{doi}")
    return out


def uniq_keep_order(urls: List[str]) -> List[str]:
    seen = set()
    out = []
    for u in urls:
        v = norm(html.unescape(u))
        if not v or v in seen:
            continue
        seen.add(v)
        out.append(v)
    return out


def prioritize_candidates(urls: List[str], max_candidates: int = 12) -> List[str]:
    direct_pdf: List[str] = []
    publisher_pdf: List[str] = []
    generic: List[str] = []
    weak: List[str] = []
    for u in urls:
        ul = u.lower()
        if (
            ul.endswith(".pdf")
            or "/pdf" in ul
            or "download" in ul
            or "blobtype=pdf" in ul
            or "type=printable" in ul
        ):
            direct_pdf.append(u)
            continue
        if any(host in ul for host in ["doi.org/", "arxiv.org/abs/", "arxiv.org/pdf/", "aclanthology.org/", "openreview.net/"]):
            publisher_pdf.append(u)
            continue
        if any(host in ul for host in ["semanticscholar.org/paper/", "pubmed.ncbi.nlm.nih.gov/"]):
            weak.append(u)
            continue
        generic.append(u)
    ranked = direct_pdf + publisher_pdf + generic + weak
    return ranked[:max_candidates]


def load_manual_candidates(root: Path) -> Dict[Tuple[str, str], Dict[str, str]]:
    data: Dict[Tuple[str, str], Dict[str, str]] = {}
    for p in sorted(root.glob("*.manual_candidates.csv")):
        with p.open("r", encoding="utf-8", newline="") as f:
            r = csv.DictReader(f)
            for row in r:
                pid = norm(row.get("paper_id"))
                key = norm(row.get("key"))
                if pid and key:
                    data[(pid, key)] = row
    return data


def build_candidates(
    session: requests.Session,
    row: Dict[str, str],
    manual: Dict[str, str],
) -> List[str]:
    key = norm(row.get("key"))
    source = norm(row.get("source"))
    source_id = norm(manual.get("source_id")) or norm(row.get("source_id"))
    doi = normalize_doi(manual.get("doi"))
    arxiv_id = norm(manual.get("arxiv_id"))
    title_query = clean_title_query(norm(manual.get("title_or_query")))

    cands: List[str] = []
    cands.extend(FORCED_URLS.get(key, []))

    if arxiv_id:
        cands.append(f"https://arxiv.org/pdf/{arxiv_id}.pdf")

    if doi:
        cands.append(f"https://doi.org/{doi}")
        if doi.startswith("10.1145/"):
            cands.append(f"https://dl.acm.org/doi/pdf/{doi}?download=true")
        if doi.startswith("10.1093/"):
            cands.append(f"https://academic.oup.com/doi/pdf/{doi}")

    cands.extend(fetch_openalex_candidates(session, source_id=source_id if source == "openalex" else "", doi=doi))
    cands.extend(fetch_s2_candidates(session, source_id=source_id if source in {"semantic_scholar", "pubmed", "crossref", "github", "openalex", "zenodo"} else "", doi=doi))

    chosen = norm(row.get("chosen_url"))
    if chosen:
        cands.append(chosen)

    if "|" in chosen:
        cands.extend([u for u in chosen.split("|") if u])

    attempted = norm(manual.get("attempted_urls"))
    if attempted:
        cands.extend([u for u in attempted.split("|") if u])

    # Fallback: title-based discovery for cases with missing/invalid ids.
    if len(cands) <= 3 and title_query:
        cands.extend(fetch_openalex_title_candidates(session, title_query))
        cands.extend(fetch_s2_title_candidates(session, title_query))

    return prioritize_candidates(uniq_keep_order(cands), max_candidates=12)


def attempt_download(
    session: requests.Session,
    url: str,
    expected_title: str,
    out_path: Path,
) -> Tuple[bool, int, str, str]:
    try:
        r = session.get(url, headers=UA, timeout=REQ_TIMEOUT, allow_redirects=True)
    except requests.exceptions.Timeout:
        return False, 0, "timeout", url
    except Exception:
        return False, 0, "all_methods_failed", url

    b = r.content or b""
    status = r.status_code
    final_url = r.url or url

    if status == 401:
        return False, len(b), "need_login", final_url
    if status == 403:
        return False, len(b), "403", final_url
    if status == 404:
        return False, len(b), "404", final_url
    if status >= 500:
        return False, len(b), f"http_{status}", final_url
    if status >= 400:
        return False, len(b), str(status), final_url

    ct = norm(r.headers.get("Content-Type", ""))
    if not is_probable_pdf(b, ct, final_url):
        txt = ""
        try:
            txt = b[:20000].decode("utf-8", errors="ignore")
        except Exception:
            txt = ""
        return False, len(b), classify_non_pdf(b, txt), final_url

    if len(b) <= MIN_VALID_PDF_BYTES:
        return False, len(b), "too_small_pdf", final_url

    if fitz is not None and expected_title:
        try:
            doc = fitz.open(stream=b, filetype="pdf")
            first = ""
            if doc.page_count > 0:
                first = doc[0].get_text("text")[:4000]
            meta_title = norm((doc.metadata or {}).get("title", ""))
            doc.close()
            check_text = f"{meta_title}\n{first}"
            if not title_match(expected_title, check_text):
                return False, len(b), "title_mismatch_pdf", final_url
        except Exception:
            pass

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(b)
    return True, len(b), "ok", final_url


def parse_round(input_path: Path, explicit_round: int | None) -> int:
    if explicit_round is not None:
        return explicit_round
    m = re.search(r"manual_backfill_round(\d+)\.", input_path.name)
    if m:
        return int(m.group(1)) + 1
    return 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-results", required=True)
    ap.add_argument("--round", type=int, default=None)
    ap.add_argument("--issues-root", default="issues/ref_pdf_download")
    ap.add_argument("--output-root", default="ref_pdfs")
    args = ap.parse_args()

    input_results = Path(args.input_results)
    issues_root = Path(args.issues_root)
    output_root = Path(args.output_root)

    round_no = parse_round(input_results, args.round)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_results = issues_root / f"manual_backfill_round{round_no}.{ts}.results.csv"
    out_log = issues_root / f"manual_backfill_round{round_no}.{ts}.log"

    skip_notes_env = norm(os.getenv("MANUAL_RETRY_SKIP_NOTES", ""))
    skip_notes = {n.strip() for n in skip_notes_env.split(",") if n.strip()}

    with input_results.open("r", encoding="utf-8", newline="") as f:
        prev_rows = []
        for r in csv.DictReader(f):
            if norm(r.get("result")) == "downloaded":
                continue
            note = norm(r.get("note"))
            if skip_notes and note in skip_notes:
                continue
            prev_rows.append(r)

    manual_map = load_manual_candidates(issues_root)

    lines: List[str] = []
    lines.append(f"ROUND{round_no}_START | failed_from_prev={len(prev_rows)} | source={input_results}")
    print(lines[-1], flush=True)

    session = requests.Session()
    session.headers.update(UA)

    out_rows: List[Dict[str, str]] = []
    fail_counter: Counter[str] = Counter()
    new_success = 0

    for idx, row in enumerate(prev_rows, start=1):
        paper_id = norm(row.get("paper_id"))
        key = norm(row.get("key"))
        source = norm(row.get("source"))
        manual = manual_map.get((paper_id, key), {})
        expected_title = norm(manual.get("title_or_query"))

        out_pdf = output_root / paper_id / f"{key}.pdf"
        if out_pdf.exists() and out_pdf.stat().st_size > MIN_VALID_PDF_BYTES:
            b = out_pdf.stat().st_size
            line = f"[{paper_id}] {key} | {source} | {out_pdf.as_posix()} | downloaded | {b} | existing_valid"
            print(line, flush=True)
            lines.append(line)
            out_rows.append(
                {
                    "paper_id": paper_id,
                    "key": key,
                    "source": source,
                    "chosen_url": out_pdf.as_posix(),
                    "result": "downloaded",
                    "bytes": str(b),
                    "note": "existing_valid",
                }
            )
            new_success += 1
            continue

        cands = build_candidates(session, row=row, manual=manual)
        planned = "|".join(cands)
        plan_line = f"[{paper_id}] {key} | {source} | {planned} | planned | 0 | candidates={len(cands)}"
        print(plan_line, flush=True)
        lines.append(plan_line)

        best_note = "all_methods_failed"
        best_url = ""
        best_bytes = 0
        success = False

        for c in cands:
            ok, b, note, final_u = attempt_download(session, c, expected_title=expected_title, out_path=out_pdf)
            if ok:
                success = True
                best_url = final_u
                best_bytes = b
                best_note = "downloaded"
                break
            best_url = final_u
            best_bytes = b
            best_note = note
            if note in {"403", "404", "need_login", "title_mismatch_pdf", "no_pdf_available", "non_pdf", "timeout"}:
                pass
            time.sleep(0.2)

        if success:
            line = f"[{paper_id}] {key} | {source} | {best_url} | downloaded | {best_bytes} | downloaded"
            out_rows.append(
                {
                    "paper_id": paper_id,
                    "key": key,
                    "source": source,
                    "chosen_url": best_url,
                    "result": "downloaded",
                    "bytes": str(best_bytes),
                    "note": "downloaded",
                }
            )
            new_success += 1
        else:
            line = f"[{paper_id}] {key} | {source} | {best_url} | failed | {best_bytes} | {best_note}"
            out_rows.append(
                {
                    "paper_id": paper_id,
                    "key": key,
                    "source": source,
                    "chosen_url": best_url,
                    "result": "failed",
                    "bytes": str(best_bytes),
                    "note": best_note,
                }
            )
            fail_counter[best_note] += 1

        print(line, flush=True)
        lines.append(line)

        if idx % 20 == 0:
            p = f"PROGRESS round={round_no} processed={idx}/{len(prev_rows)}"
            print(p, flush=True)
            lines.append(p)

    issues_root.mkdir(parents=True, exist_ok=True)
    with out_results.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["paper_id", "key", "source", "chosen_url", "result", "bytes", "note"])
        w.writeheader()
        w.writerows(out_rows)

    with out_log.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    still_failed = sum(1 for r in out_rows if r["result"] == "failed")
    failed_rows = [r for r in out_rows if r["result"] == "failed"]
    remaining_csv = sorted({f"{r['paper_id']}.manual_candidates.csv" for r in failed_rows})
    top3 = fail_counter.most_common(3)

    summary = {
        "round": round_no,
        "new_success": new_success,
        "still_failed": still_failed,
        "top3_fail_reasons": top3,
        "remaining_manual_candidates_csv": remaining_csv,
        "result_csv": out_results.as_posix(),
        "log": out_log.as_posix(),
    }
    sline = f"FINAL_SUMMARY {json.dumps(summary, ensure_ascii=False)}"
    print(sline, flush=True)
    print(json.dumps(summary, ensure_ascii=False), flush=True)

    with out_log.open("a", encoding="utf-8") as f:
        f.write(sline + "\n")
        f.write(json.dumps(summary, ensure_ascii=False) + "\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
