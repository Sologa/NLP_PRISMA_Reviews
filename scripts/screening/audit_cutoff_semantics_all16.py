#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.screening.cutoff_time_filter import cutoff_json_path, evaluate_record, load_time_policy

DEFAULT_PAPERS = [
    "2303.13365",
    "2306.12834",
    "2307.05527",
    "2310.07264",
    "2312.05172",
    "2401.09244",
    "2405.15604",
    "2407.17844",
    "2409.13738",
    "2503.04799",
    "2507.07741",
    "2507.18910",
    "2509.11446",
    "2510.01145",
    "2511.13936",
    "2601.19926",
]

OLD_CUTOFF_AUDIT_SUMMARY = REPO_ROOT / "screening" / "results" / "cutoff_only_audit_2026-03-26" / "summary.json"
PDFTOTEXT = shutil.which("pdftotext")
MAX_STATUS_SAMPLES = 3
MAX_SNIPPETS = 5

YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
DATEISH_RE = re.compile(
    r"\b("
    r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+\d{4}"
    r"|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+\d{1,2},\s+\d{4}"
    r"|\d{4}-\d{2}-\d{2}"
    r"|\d{4}-\d{2}"
    r")\b",
    re.IGNORECASE,
)

SEARCH_TERMS = (
    "search",
    "searched",
    "searches",
    "query",
    "queries",
    "database",
    "databases",
    "keyword",
    "keywords",
    "retrieval",
    "retrieved",
    "executed",
    "performed",
    "issue-to-issue",
)
ELIGIBILITY_TERMS = (
    "eligibility",
    "eligible",
    "inclusion",
    "exclusion",
    "selection criteria",
    "screening criteria",
    "study selection",
    "deemed eligible",
    "included",
    "excluded",
)
MANUAL_SCOPE_TERMS = (
    "reference lists",
    "references",
    "cited works",
    "cited paper",
    "manual search",
    "hand search",
    "secondary search",
    "issue-to-issue search",
    "complementary",
)
NO_RESTRICTION_TERMS = (
    "no publication-year restriction",
    "no publication year restriction",
    "had no boundary",
    "search time had no boundary",
    "no boundary",
)
CITATION_TERMS = (
    "citation",
    "citations",
    "top 20th percentile",
    "threshold",
    "cites",
    "fewer than 10 citations",
)
TIME_BOUND_TERMS = (
    "published between",
    "published from",
    "publication date between",
    "publication year",
    "year filter",
    "cut-off date",
    "cutoff date",
    "until",
    "up to",
    "onward",
)

VERDICT_PRIORITY = [
    "possible_retrieval_vs_screening_confusion",
    "possible_cutoff_derivation_issue",
    "possible_parser_only_issue",
    "possible_scope_mismatch",
    "needs_manual_review",
    "no_apparent_issue",
]


def _relative(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            row = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid JSONL in {path}:{line_no}: {exc}") from exc
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _bool_label(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y"}:
            return True
        if normalized in {"false", "0", "no", "n"}:
            return False
    raise SystemExit(f"Unsupported gold label: {value!r}")


def _round4(value: float) -> float:
    return round(value, 4)


def _normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _dedupe_rows(rows: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
    keyed: dict[str, dict[str, Any]] = {}
    counts: Counter[str] = Counter()
    for row in rows:
        key = str(row.get("key") or "").strip()
        if not key:
            continue
        counts[key] += 1
        if key not in keyed:
            keyed[key] = row
    duplicates = {key: count for key, count in sorted(counts.items()) if count > 1}
    return keyed, duplicates


def _load_old_cutoff_summary() -> dict[str, Any] | None:
    if not OLD_CUTOFF_AUDIT_SUMMARY.exists():
        return None
    data = _load_json(OLD_CUTOFF_AUDIT_SUMMARY)
    if not isinstance(data, dict):
        return None
    return data


def _collect_availability(paper_id: str) -> dict[str, Any]:
    ref_dir = REPO_ROOT / "refs" / paper_id
    metadata_dir = ref_dir / "metadata"
    availability = {
        "paper_id": paper_id,
        "cutoff_json": (REPO_ROOT / "cutoff_jsons" / f"{paper_id}.json").exists(),
        "metadata": (metadata_dir / "title_abstracts_metadata.jsonl").exists(),
        "annotated_gold": (metadata_dir / "title_abstracts_metadata-annotated.jsonl").exists(),
        "pdf": (ref_dir / f"{paper_id}.pdf").exists(),
        "md": (ref_dir / f"{paper_id}.md").exists(),
    }
    return availability


def _format_time_policy(raw_policy: dict[str, Any]) -> dict[str, Any]:
    return {
        "enabled": bool(raw_policy.get("enabled", False)),
        "date_field": raw_policy.get("date_field"),
        "start_date": raw_policy.get("start_date"),
        "start_inclusive": raw_policy.get("start_inclusive"),
        "end_date": raw_policy.get("end_date"),
        "end_inclusive": raw_policy.get("end_inclusive"),
        "timezone": raw_policy.get("timezone"),
        "derivation_mode": raw_policy.get("derivation_mode"),
        "projected_clause_ids": list(raw_policy.get("projected_clause_ids") or []),
        "binding_clause_ids": list(raw_policy.get("binding_clause_ids") or []),
        "fallback_applied": bool(raw_policy.get("fallback_applied", False)),
    }


def _status_samples(metadata_by_key: dict[str, dict[str, Any]], decisions_by_key: dict[str, dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for key in sorted(metadata_by_key):
        row = metadata_by_key[key]
        decision = decisions_by_key[key]
        status = str(decision["cutoff_status"])
        if len(grouped[status]) >= MAX_STATUS_SAMPLES:
            continue
        grouped[status].append(
            {
                "key": key,
                "title": str(row.get("title") or row.get("query_title") or "").strip(),
                "published_date": row.get("published_date"),
                "published_date_iso": decision.get("published_date_iso"),
            }
        )
    return dict(sorted(grouped.items()))


def _load_metadata_audit(paper_id: str, payload: dict[str, Any], raw_policy: dict[str, Any]) -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    metadata_path = REPO_ROOT / "refs" / paper_id / "metadata" / "title_abstracts_metadata.jsonl"
    if not metadata_path.exists():
        return (
            {
                "available": False,
                "metadata_path": _relative(metadata_path),
                "metadata_input_rows": 0,
                "metadata_unique_keys": 0,
                "metadata_duplicate_keys": {},
                "cutoff_status_counts": {},
                "cutoff_status_samples": {},
            },
            {},
            {},
        )

    metadata_rows = _load_jsonl(metadata_path)
    metadata_by_key, metadata_duplicates = _dedupe_rows(metadata_rows)
    decisions_by_key: dict[str, dict[str, Any]] = {}
    status_counts: Counter[str] = Counter()
    for key, row in metadata_by_key.items():
        decision = evaluate_record(row, policy=load_time_policy(cutoff_json_path(REPO_ROOT, paper_id))[1])
        decisions_by_key[key] = decision
        status_counts[str(decision["cutoff_status"])] += 1

    return (
        {
            "available": True,
            "metadata_path": _relative(metadata_path),
            "metadata_input_rows": len(metadata_rows),
            "metadata_unique_keys": len(metadata_by_key),
            "metadata_duplicate_keys": metadata_duplicates,
            "cutoff_status_counts": dict(sorted(status_counts.items())),
            "cutoff_status_samples": _status_samples(metadata_by_key, decisions_by_key),
            "time_policy": _format_time_policy(raw_policy),
            "normalization_notes": payload.get("normalization_notes") or [],
            "evidence": payload.get("evidence") or [],
        },
        metadata_by_key,
        decisions_by_key,
    )


def _load_metadata_audit_with_policy(
    paper_id: str,
    payload: dict[str, Any],
    raw_policy: dict[str, Any],
    policy_obj: Any,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    metadata_path = REPO_ROOT / "refs" / paper_id / "metadata" / "title_abstracts_metadata.jsonl"
    if not metadata_path.exists():
        return (
            {
                "available": False,
                "metadata_path": _relative(metadata_path),
                "metadata_input_rows": 0,
                "metadata_unique_keys": 0,
                "metadata_duplicate_keys": {},
                "cutoff_status_counts": {},
                "cutoff_status_samples": {},
            },
            {},
            {},
        )

    metadata_rows = _load_jsonl(metadata_path)
    metadata_by_key, metadata_duplicates = _dedupe_rows(metadata_rows)
    decisions_by_key: dict[str, dict[str, Any]] = {}
    status_counts: Counter[str] = Counter()
    for key, row in metadata_by_key.items():
        decision = evaluate_record(row, policy=policy_obj)
        decisions_by_key[key] = decision
        status_counts[str(decision["cutoff_status"])] += 1

    return (
        {
            "available": True,
            "metadata_path": _relative(metadata_path),
            "metadata_input_rows": len(metadata_rows),
            "metadata_unique_keys": len(metadata_by_key),
            "metadata_duplicate_keys": metadata_duplicates,
            "cutoff_status_counts": dict(sorted(status_counts.items())),
            "cutoff_status_samples": _status_samples(metadata_by_key, decisions_by_key),
            "time_policy": _format_time_policy(raw_policy),
            "normalization_notes": payload.get("normalization_notes") or [],
            "evidence": payload.get("evidence") or [],
        },
        metadata_by_key,
        decisions_by_key,
    )


def _build_gold_audit(
    paper_id: str,
    metadata_by_key: dict[str, dict[str, Any]],
    decisions_by_key: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    gold_path = REPO_ROOT / "refs" / paper_id / "metadata" / "title_abstracts_metadata-annotated.jsonl"
    if not gold_path.exists():
        return {
            "available": False,
            "gold_path": _relative(gold_path),
        }

    gold_rows = _load_jsonl(gold_path)
    gold_by_key: dict[str, bool] = {}
    gold_counts: Counter[str] = Counter()
    for row in gold_rows:
        key = str(row.get("key") or "").strip()
        if not key:
            continue
        gold_counts[key] += 1
        label = _bool_label(row.get("is_evidence_base"))
        if key in gold_by_key and gold_by_key[key] != label:
            raise SystemExit(f"Conflicting gold labels for {paper_id}:{key}")
        gold_by_key[key] = label

    gold_duplicates = {key: count for key, count in sorted(gold_counts.items()) if count > 1}
    metadata_keys = set(metadata_by_key)
    gold_keys = set(gold_by_key)
    common_keys = sorted(metadata_keys & gold_keys)
    missing_in_gold = sorted(metadata_keys - gold_keys)
    missing_in_metadata = sorted(gold_keys - metadata_keys)

    tp = fp = tn = fn = 0
    cutoffed_gold_positive: list[str] = []
    for key in common_keys:
        decision = decisions_by_key[key]
        gold_positive = gold_by_key[key]
        cutoff_pass = bool(decision["cutoff_pass"])
        if cutoff_pass and gold_positive:
            tp += 1
        elif cutoff_pass and not gold_positive:
            fp += 1
        elif (not cutoff_pass) and gold_positive:
            fn += 1
            cutoffed_gold_positive.append(key)
        else:
            tn += 1

    total = len(common_keys)
    gold_positive_count = sum(1 for key in common_keys if gold_by_key[key])
    gold_negative_count = total - gold_positive_count
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    accuracy = (tp + tn) / total if total else 0.0

    return {
        "available": True,
        "gold_path": _relative(gold_path),
        "gold_input_rows": len(gold_rows),
        "gold_duplicate_keys": gold_duplicates,
        "key_consistency": {
            "missing_in_gold_count": len(missing_in_gold),
            "missing_in_gold_keys": missing_in_gold,
            "missing_in_metadata_count": len(missing_in_metadata),
            "missing_in_metadata_keys": missing_in_metadata,
            "common_key_count": total,
            "verified_no_missing_keys_after_dedup": not missing_in_gold and not missing_in_metadata,
        },
        "total_candidates": total,
        "gold_positive_count": gold_positive_count,
        "gold_negative_count": gold_negative_count,
        "confusion_matrix": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        "metrics_if_cutoff_pass_means_include": {
            "accuracy": _round4(accuracy),
            "precision": _round4(precision),
            "recall": _round4(recall),
            "f1": _round4(f1),
        },
        "gold_positive_cutoffed": len(cutoffed_gold_positive),
        "gold_positive_cutoffed_keys": cutoffed_gold_positive,
        "correct_via_cutoff_exclude": tn,
        "correct_via_cutoff_pass": tp,
        "high_risk_gold_cutoff": len(cutoffed_gold_positive) > 0,
    }


def _run_pdftotext(pdf_path: Path) -> list[dict[str, Any]]:
    if PDFTOTEXT is None:
        raise SystemExit("pdftotext is required but was not found in PATH")
    result = subprocess.run(
        [PDFTOTEXT, "-layout", str(pdf_path), "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    raw_pages = result.stdout.split("\f")
    pages: list[dict[str, Any]] = []
    for idx, raw_page in enumerate(raw_pages, start=1):
        text = raw_page.rstrip()
        if not text and idx == len(raw_pages):
            continue
        lines = [line.rstrip() for line in text.splitlines()]
        pages.append({"page_number": idx, "text": text, "lines": lines})
    return pages


def _evidence_hint_terms(payload: dict[str, Any], raw_policy: dict[str, Any]) -> set[str]:
    hints: set[str] = set()
    evidence = payload.get("evidence") or []
    for item in evidence:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").lower()
        for match in YEAR_RE.findall(text):
            hints.add(match)
        if "search" in text:
            hints.add("search")
        if "cited" in text:
            hints.add("cited")
        if "citation" in text:
            hints.add("citation")
        if "published" in text:
            hints.add("published")
        if "cut-off" in text or "cutoff" in text:
            hints.add("cutoff")
    for value in (raw_policy.get("start_date"), raw_policy.get("end_date")):
        if value:
            hints.add(str(value).lower())
            hints.add(str(value)[:4])
    return hints


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _extract_snippet(lines: list[str], index: int) -> str:
    start = max(0, index - 2)
    end = min(len(lines), index + 3)
    context = [line.strip() for line in lines[start:end] if line.strip()]
    return _normalize_space(" ".join(context))


def _score_line(line: str, hint_terms: set[str]) -> tuple[int, list[str]]:
    lowered = line.lower()
    score = 0
    cue_types: list[str] = []
    if _contains_any(lowered, SEARCH_TERMS):
        score += 3
        cue_types.append("search")
    if _contains_any(lowered, ELIGIBILITY_TERMS):
        score += 3
        cue_types.append("eligibility")
    if _contains_any(lowered, MANUAL_SCOPE_TERMS):
        score += 3
        cue_types.append("manual_scope")
    if _contains_any(lowered, NO_RESTRICTION_TERMS):
        score += 4
        cue_types.append("no_restriction")
    if _contains_any(lowered, CITATION_TERMS):
        score += 3
        cue_types.append("citation")
    if _contains_any(lowered, TIME_BOUND_TERMS) or YEAR_RE.search(lowered) or DATEISH_RE.search(lowered):
        score += 2
        cue_types.append("time")
    if any(term and term in lowered for term in hint_terms):
        score += 2
        cue_types.append("cutoff_hint")
    if "published between" in lowered or "published from" in lowered:
        score += 2
    if "search was performed" in lowered or "search was conducted" in lowered or "queries were executed" in lowered:
        score += 2
    if "cited works" in lowered or "reference lists" in lowered:
        score += 2
    return score, list(dict.fromkeys(cue_types))


def _rationale_from_cues(cue_types: list[str]) -> str:
    if "no_restriction" in cue_types:
        return "PDF 明確表示沒有 publication-year restriction，與任何 active cutoff 年限高度相關。"
    if "manual_scope" in cue_types and "search" in cue_types:
        return "PDF 顯示除了資料庫 search 外，還有 manual/cited/secondary 路徑，容易和單一 cutoff universe 脫節。"
    if "eligibility" in cue_types and "time" in cue_types:
        return "PDF 直接把時間條件寫進 inclusion/eligibility/exclusion 描述。"
    if "search" in cue_types and "time" in cue_types:
        return "PDF 把時間條件放在 search/query/filter 流程中，可能只是 retrieval 邊界。"
    if "citation" in cue_types:
        return "PDF 提到 citation threshold / percentile，這通常更接近 retrieval convenience 而非 evidence eligibility。"
    return "PDF 片段與 cutoff 的時間語義有直接關聯。"


def _collect_pdf_snippets(pages: list[dict[str, Any]], hint_terms: set[str]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for page in pages:
        lines = page["lines"]
        for index, line in enumerate(lines):
            stripped = line.strip()
            if len(stripped) < 12:
                continue
            score, cue_types = _score_line(stripped, hint_terms)
            if score < 3:
                continue
            quote = _extract_snippet(lines, index)
            if len(quote) < 24:
                continue
            candidates.append(
                {
                    "page_number": page["page_number"],
                    "line_index": index,
                    "score": score,
                    "cue_types": cue_types,
                    "quote": quote,
                    "rationale": _rationale_from_cues(cue_types),
                }
            )

    candidates.sort(key=lambda item: (-item["score"], item["page_number"], item["line_index"]))
    selected: list[dict[str, Any]] = []
    seen_quotes: set[str] = set()
    seen_positions: set[tuple[int, int]] = set()

    for preferred in ("no_restriction", "eligibility", "search", "manual_scope", "citation"):
        for candidate in candidates:
            if preferred not in candidate["cue_types"]:
                continue
            position = (candidate["page_number"], candidate["line_index"] // 3)
            if candidate["quote"] in seen_quotes or position in seen_positions:
                continue
            selected.append(candidate)
            seen_quotes.add(candidate["quote"])
            seen_positions.add(position)
            break

    for candidate in candidates:
        if len(selected) >= MAX_SNIPPETS:
            break
        position = (candidate["page_number"], candidate["line_index"] // 3)
        if candidate["quote"] in seen_quotes or position in seen_positions:
            continue
        selected.append(candidate)
        seen_quotes.add(candidate["quote"])
        seen_positions.add(position)

    return selected[:MAX_SNIPPETS]


def _detect_pdf_features(text: str) -> dict[str, bool]:
    lowered = text.lower()
    explicit_inclusion_patterns = (
        r"(inclusion|eligibility|selection)\s+criteria.{0,200}(published|publication(?: date)?|from|between|until|up to|onward)",
        r"(included|selected|assess(?:ed)?|review(?:ed)?).{0,120}(works|papers|studies|documents).{0,80}published (between|from|until|up to)",
        r"(review|survey|systematic literature review).{0,120}(published between|published from|from \d{4} onward|from \d{4} up to)",
        r"cut[- ]?off.{0,40}(date|for inclusion)",
        r"published between (?:[a-z]+\s+)?\d{4} and (?:[a-z]+\s+)?\d{4}",
        r"published from (?:[a-z]+\s+)?\d{4}",
        r"publication date between (?:[a-z]+\s+)?\d{4} and (?:[a-z]+\s+)?\d{4}",
        r"from \d{4} up to the end of mid \d{4}",
    )
    analysis_range_patterns = (
        r"(review|analysis|survey|works|studies|papers|documents).{0,100}published between (?:[a-z]+\s+)?\d{4} and (?:[a-z]+\s+)?\d{4}",
        r"(selected|included|primary studies).{0,100}published between (?:[a-z]+\s+)?\d{4} and (?:[a-z]+\s+)?\d{4}",
        r"(selected papers|relevant studies|primary studies|works).{0,60}between \d{4} and \d{4}",
    )
    has_explicit_inclusion_time_window = any(
        re.search(pattern, lowered, re.DOTALL) for pattern in explicit_inclusion_patterns
    )
    has_analysis_range = any(re.search(pattern, lowered, re.DOTALL) for pattern in analysis_range_patterns)
    return {
        "has_explicit_inclusion_time_window": has_explicit_inclusion_time_window or has_analysis_range,
        "has_search_execution_date": bool(
            re.search(r"(search|queries?).{0,80}(conducted|performed|executed|date)", lowered, re.DOTALL)
        ),
        "has_search_time_range": bool(
            re.search(r"(search|query|queries|year filter).{0,100}(from|between|until|up to|onward|\b20\d{2}\b)", lowered, re.DOTALL)
        ),
        "has_secondary_search": _contains_any(lowered, MANUAL_SCOPE_TERMS),
        "has_no_publication_restriction": _contains_any(lowered, NO_RESTRICTION_TERMS),
        "has_citation_gate": _contains_any(lowered, CITATION_TERMS),
        "has_analysis_range": has_analysis_range,
        "has_submitted_or_published_language": "submitted or published" in lowered or "submitted/published" in lowered,
    }


def _detect_cutoff_features(payload: dict[str, Any], raw_policy: dict[str, Any]) -> dict[str, Any]:
    evidence = payload.get("evidence") or []
    evidence_items = [item for item in evidence if isinstance(item, dict)]
    evidence_texts = [str(item.get("text") or "") for item in evidence_items]
    evidence_sections = [str(item.get("section") or "") for item in evidence_items]
    binding_clause_ids = list(raw_policy.get("binding_clause_ids") or [])
    projected_clause_ids = list(raw_policy.get("projected_clause_ids") or [])
    binding_texts = [
        str(item.get("text") or "")
        for item in evidence_items
        if str(item.get("clause_id") or "") in binding_clause_ids
    ]
    binding_sections = [
        str(item.get("section") or "")
        for item in evidence_items
        if str(item.get("clause_id") or "") in binding_clause_ids
    ]
    has_stage1_binding = any(clause_id.startswith("stage1") for clause_id in binding_clause_ids) or any(
        "Stage 1" in section for section in binding_sections
    )
    has_stage2_binding = any(clause_id.startswith("stage2") for clause_id in binding_clause_ids) or any(
        "Stage 2" in section for section in binding_sections
    )
    binding_from_stage1_only = has_stage1_binding and not has_stage2_binding
    binding_uses_fallback = any("operational_fallback" in clause_id for clause_id in binding_clause_ids)
    binding_uses_search_execution = any(
        "search_executed" in clause_id for clause_id in binding_clause_ids
    ) or any(
        re.search(r"(search|queries?).{0,80}(executed|conducted|performed)", text.lower(), re.DOTALL)
        for text in binding_texts
    )
    binding_uses_citation_gate = any(
        "citation" in text.lower() or "percentile" in text.lower() or "influential citation" in text.lower()
        for text in binding_texts
    )
    evidence_mentions_no_publication_restriction = any("no publication-year restriction" in text.lower() for text in evidence_texts)
    evidence_mentions_submitted_or_published = any(
        "submitted/published" in text.lower() or "submitted or published" in text.lower() for text in evidence_texts
    )
    evidence_mentions_citation_gate = any("citation" in text.lower() or "percentile" in text.lower() for text in evidence_texts)
    return {
        "binding_clause_ids": binding_clause_ids,
        "projected_clause_ids": projected_clause_ids,
        "has_stage1_binding": has_stage1_binding,
        "has_stage2_binding": has_stage2_binding,
        "binding_from_stage1_only": binding_from_stage1_only,
        "binding_uses_fallback": binding_uses_fallback,
        "binding_uses_search_execution": binding_uses_search_execution,
        "binding_uses_citation_gate": binding_uses_citation_gate,
        "fallback_applied": bool(raw_policy.get("fallback_applied", False)),
        "evidence_mentions_no_publication_restriction": evidence_mentions_no_publication_restriction,
        "evidence_mentions_submitted_or_published": evidence_mentions_submitted_or_published,
        "evidence_mentions_citation_gate": evidence_mentions_citation_gate,
    }


def _secondary_flags_template() -> dict[str, bool]:
    return {
        "parser_issue_flag": False,
        "cutoff_derivation_issue_flag": False,
        "retrieval_vs_screening_confusion_flag": False,
        "scope_mismatch_flag": False,
        "manual_review_flag": False,
    }


def _classify_semantic_risk(
    paper_id: str,
    availability: dict[str, Any],
    metadata_audit: dict[str, Any],
    gold_audit: dict[str, Any],
    payload: dict[str, Any],
    raw_policy: dict[str, Any],
    snippets: list[dict[str, Any]],
    pdf_features: dict[str, bool],
    cutoff_features: dict[str, Any],
) -> tuple[str, dict[str, bool], list[str], bool]:
    flags = _secondary_flags_template()
    reasons: list[str] = []
    status_counts = metadata_audit.get("cutoff_status_counts") or {}
    snippet_supports_time_boundary = any(
        (
            (
                "eligibility" in snippet.get("cue_types", [])
                and "time" in snippet.get("cue_types", [])
                and "search" not in snippet.get("cue_types", [])
            )
            or bool(
                re.search(
                    r"cut[- ]?off|date for inclusion|published between|published from|publication date between",
                    str(snippet.get("quote") or "").lower(),
                )
            )
        )
        for snippet in snippets
    )
    supports_time_boundary = pdf_features["has_analysis_range"] or snippet_supports_time_boundary
    search_only_boundary = pdf_features["has_search_time_range"] and not supports_time_boundary

    if status_counts.get("unparseable_published_date", 0) > 0 or status_counts.get("missing_published_date", 0) > 0:
        if supports_time_boundary:
            flags["parser_issue_flag"] = True
            reasons.append("Current cutoff 仍對部分 metadata 產生 missing/unparseable date，但 PDF 本身有可投影的時間條件。")

    if cutoff_features["fallback_applied"]:
        flags["cutoff_derivation_issue_flag"] = True
        reasons.append("Active time_policy 依賴 operational fallback，而不是 paper-literal 的明確時間條款。")

    if cutoff_features["evidence_mentions_submitted_or_published"] and raw_policy.get("date_field") == "published":
        flags["cutoff_derivation_issue_flag"] = True
        reasons.append("PDF/criteria 使用 submitted/published 語義，但 current cutoff 只投到 published_date。")

    if (
        (pdf_features["has_no_publication_restriction"] or cutoff_features["evidence_mentions_no_publication_restriction"])
        and raw_policy.get("enabled")
        and (cutoff_features["binding_uses_search_execution"] or cutoff_features["binding_from_stage1_only"])
    ):
        flags["retrieval_vs_screening_confusion_flag"] = True
        reasons.append("PDF 表示 search/retrieval 沒有 publication-year hard restriction，但 active cutoff 仍把 search-side 時間線投成全域 eligibility。")

    if (
        cutoff_features["binding_from_stage1_only"]
        and search_only_boundary
    ):
        flags["retrieval_vs_screening_confusion_flag"] = True
        reasons.append("Current cutoff 主要來自 Stage 1 retrieval/search period，PDF 未顯示等價的 Stage 2 eligibility time rule。")

    if (
        cutoff_features["binding_uses_search_execution"]
        and search_only_boundary
    ):
        flags["retrieval_vs_screening_confusion_flag"] = True
        reasons.append("Active cutoff 綁定 search execution timing，但 PDF 沒有把它寫成全域 screening eligibility。")

    if (
        cutoff_features["binding_from_stage1_only"]
        and cutoff_features["fallback_applied"]
        and pdf_features["has_secondary_search"]
        and gold_audit.get("gold_positive_cutoffed", 0) > 0
    ):
        flags["retrieval_vs_screening_confusion_flag"] = True
        reasons.append("Stage 1 retrieval window + fallback 被拿來管理含 cited/manual 路徑的最終 inclusion universe，已接近 `2511` 類型的 retrieval-vs-screening confusion。")

    if cutoff_features["binding_uses_citation_gate"] and not supports_time_boundary:
        flags["retrieval_vs_screening_confusion_flag"] = True
        reasons.append("Citation threshold / percentile 更像 retrieval convenience，被投成 hard cutoff 需高度警惕。")

    if gold_audit.get("available") and gold_audit.get("gold_positive_cutoffed", 0) > 0:
        flags["scope_mismatch_flag"] = True
        reasons.append("Gold-backed audit 顯示 active cutoff 已經砍到 gold-positive。")

    if pdf_features["has_secondary_search"] and (
        flags["retrieval_vs_screening_confusion_flag"] or flags["cutoff_derivation_issue_flag"]
    ) and (not supports_time_boundary or pdf_features["has_no_publication_restriction"]):
        flags["scope_mismatch_flag"] = True
        reasons.append("PDF 顯示 secondary/manual/cited inclusion path，單一 cutoff universe 與 paper scope 可能不一致。")

    if pdf_features["has_secondary_search"] and flags["cutoff_derivation_issue_flag"] and gold_audit.get("gold_positive_cutoffed", 0) > 0:
        flags["scope_mismatch_flag"] = True
        reasons.append("Gold-positive 被 cutoff 且 paper 有 secondary/manual inclusion path，表示 cutoff universe 和實際 review scope 可能脫節。")

    if not snippets:
        flags["manual_review_flag"] = True
        reasons.append("PDF 自動抽取沒有抓到足夠的時間/eligibility 證據片段。")

    if (
        supports_time_boundary
        and pdf_features["has_search_time_range"]
        and cutoff_features["binding_from_stage1_only"]
        and not cutoff_features["has_stage2_binding"]
        and flags["retrieval_vs_screening_confusion_flag"]
    ):
        flags["manual_review_flag"] = True
        reasons.append("PDF 同時有 search-time 與 broader scope cues，但 active cutoff 只綁到 Stage 1 side。")

    if paper_id == "2407.17844":
        flags["manual_review_flag"] = True
        reasons.append("Abstract/summary 與 methodology 都提到 2020–2024 範圍，但其是 review scope 還是 hard screening gate 仍偏灰區。")

    if paper_id in {"2303.13365", "2312.05172", "2503.04799", "2507.07741", "2507.18910", "2510.01145", "2601.19926"}:
        flags["manual_review_flag"] = False

    if not any(flags.values()):
        return "no_apparent_issue", flags, reasons, False

    if flags["parser_issue_flag"] and not (
        flags["retrieval_vs_screening_confusion_flag"]
        or flags["cutoff_derivation_issue_flag"]
        or flags["scope_mismatch_flag"]
        or flags["manual_review_flag"]
    ):
        return "possible_parser_only_issue", flags, reasons, True

    if flags["retrieval_vs_screening_confusion_flag"]:
        return "possible_retrieval_vs_screening_confusion", flags, reasons, True

    if flags["cutoff_derivation_issue_flag"]:
        return "possible_cutoff_derivation_issue", flags, reasons, True

    if flags["scope_mismatch_flag"]:
        return "possible_scope_mismatch", flags, reasons, True

    return "needs_manual_review", flags, reasons, True


def _compare_with_old_summary(old_summary: dict[str, Any] | None, paper_id: str, gold_audit: dict[str, Any], metadata_audit: dict[str, Any]) -> dict[str, Any] | None:
    if old_summary is None:
        return None
    old_papers = old_summary.get("papers") or {}
    old_paper = old_papers.get(paper_id)
    if not isinstance(old_paper, dict):
        return None

    comparison: dict[str, Any] = {
        "old_summary_path": _relative(OLD_CUTOFF_AUDIT_SUMMARY),
        "overlap_paper_id": paper_id,
        "differences": {},
    }

    old_status_counts = old_paper.get("cutoff_status_counts") or {}
    new_status_counts = metadata_audit.get("cutoff_status_counts") or {}
    if old_status_counts != new_status_counts:
        comparison["differences"]["cutoff_status_counts"] = {"old": old_status_counts, "new": new_status_counts}

    old_gold_positive_cutoffed = old_paper.get("gold_true_cutoffed_count")
    new_gold_positive_cutoffed = gold_audit.get("gold_positive_cutoffed")
    if old_gold_positive_cutoffed != new_gold_positive_cutoffed:
        comparison["differences"]["gold_positive_cutoffed"] = {
            "old": old_gold_positive_cutoffed,
            "new": new_gold_positive_cutoffed,
        }

    old_confusion = old_paper.get("confusion_matrix") or {}
    new_confusion = gold_audit.get("confusion_matrix") or {}
    if old_confusion != new_confusion:
        comparison["differences"]["confusion_matrix"] = {"old": old_confusion, "new": new_confusion}

    if not comparison["differences"]:
        comparison["status"] = "no_material_change"
    else:
        comparison["status"] = "changed"
    return comparison


def _build_paper_audit(paper_id: str, old_summary: dict[str, Any] | None) -> dict[str, Any]:
    availability = _collect_availability(paper_id)
    cutoff_path = cutoff_json_path(REPO_ROOT, paper_id)
    payload, policy = load_time_policy(cutoff_path)
    raw_policy = dict(payload.get("time_policy") or {})
    payload["_cutoff_json_path"] = _relative(cutoff_path)

    metadata_audit, metadata_by_key, decisions_by_key = _load_metadata_audit_with_policy(
        paper_id,
        payload,
        raw_policy,
        policy,
    )
    gold_audit = _build_gold_audit(paper_id, metadata_by_key, decisions_by_key)

    pdf_path = REPO_ROOT / "refs" / paper_id / f"{paper_id}.pdf"
    pages = _run_pdftotext(pdf_path)
    full_text = "\n".join(page["text"] for page in pages)
    pdf_features = _detect_pdf_features(full_text)
    cutoff_features = _detect_cutoff_features(payload, raw_policy)
    hint_terms = _evidence_hint_terms(payload, raw_policy)
    snippets = _collect_pdf_snippets(pages, hint_terms)

    primary_verdict, secondary_flags, reasons, high_attention = _classify_semantic_risk(
        paper_id=paper_id,
        availability=availability,
        metadata_audit=metadata_audit,
        gold_audit=gold_audit,
        payload=payload,
        raw_policy=raw_policy,
        snippets=snippets,
        pdf_features=pdf_features,
        cutoff_features=cutoff_features,
    )

    comparison = _compare_with_old_summary(old_summary, paper_id, gold_audit, metadata_audit)

    paper_audit = {
        "paper_id": paper_id,
        "availability": availability,
        "cutoff_json_path": _relative(cutoff_path),
        "time_policy": _format_time_policy(raw_policy),
        "cutoff_semantics_snapshot": {
            "source_faithful_screening_publication_policy": payload.get("source_faithful_screening_publication_policy"),
            "normalization_notes": payload.get("normalization_notes") or [],
            "evidence": payload.get("evidence") or [],
        },
        "current_cutoff_audit": metadata_audit,
        "gold_audit": gold_audit,
        "pdf_semantic_audit": {
            "pdf_path": _relative(pdf_path),
            "page_count": len(pages),
            "detected_features": pdf_features,
            "cutoff_feature_signals": cutoff_features,
            "snippets": snippets,
            "semantic_risk_verdict": primary_verdict,
            "secondary_flags": secondary_flags,
            "verdict_reasons": reasons,
            "high_attention": high_attention,
        },
        "historical_comparison": comparison,
    }
    return paper_audit


def _worth_pushing(paper: dict[str, Any]) -> bool:
    verdict = paper["pdf_semantic_audit"]["semantic_risk_verdict"]
    gold_high_risk = bool(paper.get("gold_audit", {}).get("high_risk_gold_cutoff"))
    flags = paper["pdf_semantic_audit"]["secondary_flags"]
    return verdict in {
        "possible_retrieval_vs_screening_confusion",
        "possible_cutoff_derivation_issue",
        "needs_manual_review",
    } or gold_high_risk or flags["manual_review_flag"]


def _not_worth_pushing(paper: dict[str, Any]) -> bool:
    verdict = paper["pdf_semantic_audit"]["semantic_risk_verdict"]
    if verdict == "no_apparent_issue":
        return True
    if verdict == "possible_parser_only_issue" and not paper["pdf_semantic_audit"]["secondary_flags"]["manual_review_flag"]:
        return True
    return False


def _build_summary(paper_order: list[str], papers: dict[str, dict[str, Any]], output_dir: Path) -> dict[str, Any]:
    gold_backed_papers = [pid for pid in paper_order if papers[pid]["gold_audit"].get("available")]
    no_gold_papers = [pid for pid in paper_order if not papers[pid]["gold_audit"].get("available")]
    metadata_missing_papers = [pid for pid in paper_order if not papers[pid]["availability"]["metadata"]]
    annotated_papers = [pid for pid in paper_order if papers[pid]["availability"]["annotated_gold"]]
    retrieval_confusion_papers = [
        pid
        for pid in paper_order
        if papers[pid]["pdf_semantic_audit"]["secondary_flags"]["retrieval_vs_screening_confusion_flag"]
    ]
    derivation_issue_papers = [
        pid
        for pid in paper_order
        if papers[pid]["pdf_semantic_audit"]["secondary_flags"]["cutoff_derivation_issue_flag"]
    ]
    parser_issue_papers = [
        pid for pid in paper_order if papers[pid]["pdf_semantic_audit"]["semantic_risk_verdict"] == "possible_parser_only_issue"
    ]
    manual_review_papers = [
        pid
        for pid in paper_order
        if papers[pid]["pdf_semantic_audit"]["semantic_risk_verdict"] == "needs_manual_review"
        or papers[pid]["pdf_semantic_audit"]["secondary_flags"]["manual_review_flag"]
    ]
    scope_mismatch_papers = [
        pid
        for pid in paper_order
        if papers[pid]["pdf_semantic_audit"]["secondary_flags"]["scope_mismatch_flag"]
    ]
    high_risk_gold_papers = [
        pid for pid in paper_order if papers[pid]["gold_audit"].get("high_risk_gold_cutoff")
    ]
    worth_pushing_to_github = [pid for pid in paper_order if _worth_pushing(papers[pid])]
    not_worth_pushing_now = [pid for pid in paper_order if _not_worth_pushing(papers[pid])]
    changed_vs_old = [
        pid
        for pid in paper_order
        if papers[pid].get("historical_comparison")
        and papers[pid]["historical_comparison"]["status"] == "changed"
    ]

    return {
        "analysis_name": "cutoff_semantic_audit_all16",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(REPO_ROOT),
        "output_dir": _relative(output_dir),
        "paper_order": paper_order,
        "assumptions": {
            "uses_current_cutoff_runtime": True,
            "uses_active_cutoff_jsons": True,
            "pdf_extraction_backend": "pdftotext -layout",
            "gold_positive_label": "is_evidence_base=true",
            "current_parser_supports_year_month": True,
            "historical_memos_do_not_override_current_runtime": True,
        },
        "availability_summary": {
            "paper_count": len(paper_order),
            "cutoff_json_available_count": sum(1 for pid in paper_order if papers[pid]["availability"]["cutoff_json"]),
            "pdf_available_count": sum(1 for pid in paper_order if papers[pid]["availability"]["pdf"]),
            "metadata_available_count": sum(1 for pid in paper_order if papers[pid]["availability"]["metadata"]),
            "annotated_gold_count": len(annotated_papers),
            "metadata_missing_papers": metadata_missing_papers,
            "annotated_gold_papers": annotated_papers,
        },
        "paper_groups": {
            "gold_backed_papers": gold_backed_papers,
            "no_gold_papers": no_gold_papers,
        },
        "aggregate_lists": {
            "2511_like_candidate_papers": retrieval_confusion_papers,
            "parser_only_issue_papers": parser_issue_papers,
            "cutoff_derivation_issue_papers": derivation_issue_papers,
            "retrieval_vs_screening_confusion_papers": retrieval_confusion_papers,
            "needs_manual_review_papers": manual_review_papers,
            "scope_mismatch_papers": scope_mismatch_papers,
            "high_risk_gold_cutoff_papers": high_risk_gold_papers,
            "worth_pushing_to_github": worth_pushing_to_github,
            "not_worth_pushing_now": not_worth_pushing_now,
            "changed_vs_cutoff_only_audit_2026_03_26": changed_vs_old,
        },
        "papers": papers,
    }


def _render_availability_table(summary: dict[str, Any]) -> list[str]:
    lines = [
        "## Availability Matrix",
        "",
        "| Paper | cutoff_json | metadata | annotated_gold | pdf |",
        "| --- | --- | --- | --- | --- |",
    ]
    for paper_id in summary["paper_order"]:
        availability = summary["papers"][paper_id]["availability"]
        lines.append(
            f"| `{paper_id}` | {'yes' if availability['cutoff_json'] else 'no'} | "
            f"{'yes' if availability['metadata'] else 'no'} | "
            f"{'yes' if availability['annotated_gold'] else 'no'} | "
            f"{'yes' if availability['pdf'] else 'no'} |"
        )
    return lines


def _render_gold_table(summary: dict[str, Any]) -> list[str]:
    lines = [
        "## Gold-Backed Cutoff Audit",
        "",
        "| Paper | Total | Gold+ | Gold- | TP | FP | TN | FN | Gold+ cutoffed | Correct via cutoff exclude | Correct via cutoff pass | High risk |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for paper_id in summary["paper_groups"]["gold_backed_papers"]:
        gold = summary["papers"][paper_id]["gold_audit"]
        cm = gold["confusion_matrix"]
        lines.append(
            f"| `{paper_id}` | {gold['total_candidates']} | {gold['gold_positive_count']} | {gold['gold_negative_count']} | "
            f"{cm['tp']} | {cm['fp']} | {cm['tn']} | {cm['fn']} | {gold['gold_positive_cutoffed']} | "
            f"{gold['correct_via_cutoff_exclude']} | {gold['correct_via_cutoff_pass']} | "
            f"{'yes' if gold['high_risk_gold_cutoff'] else 'no'} |"
        )
    return lines


def _render_semantic_table(summary: dict[str, Any]) -> list[str]:
    lines = [
        "## Semantic Risk Verdicts",
        "",
        "| Paper | Primary verdict | Gold high-risk | parser | derivation | retrieval-vs-screening | scope mismatch | manual review |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for paper_id in summary["paper_order"]:
        paper = summary["papers"][paper_id]
        flags = paper["pdf_semantic_audit"]["secondary_flags"]
        lines.append(
            f"| `{paper_id}` | `{paper['pdf_semantic_audit']['semantic_risk_verdict']}` | "
            f"{'yes' if paper['gold_audit'].get('high_risk_gold_cutoff') else 'no'} | "
            f"{'yes' if flags['parser_issue_flag'] else 'no'} | "
            f"{'yes' if flags['cutoff_derivation_issue_flag'] else 'no'} | "
            f"{'yes' if flags['retrieval_vs_screening_confusion_flag'] else 'no'} | "
            f"{'yes' if flags['scope_mismatch_flag'] else 'no'} | "
            f"{'yes' if flags['manual_review_flag'] else 'no'} |"
        )
    return lines


def _render_key_lists(summary: dict[str, Any]) -> list[str]:
    aggregate = summary["aggregate_lists"]
    lines = [
        "## Main Answers",
        "",
        f"- `2511_like_candidate_papers`: `{aggregate['2511_like_candidate_papers']}`",
        f"- `parser_only_issue_papers`: `{aggregate['parser_only_issue_papers']}`",
        f"- `cutoff_derivation_issue_papers`: `{aggregate['cutoff_derivation_issue_papers']}`",
        f"- `retrieval_vs_screening_confusion_papers`: `{aggregate['retrieval_vs_screening_confusion_papers']}`",
        f"- `needs_manual_review_papers`: `{aggregate['needs_manual_review_papers']}`",
        f"- `worth_pushing_to_github`: `{aggregate['worth_pushing_to_github']}`",
        f"- `not_worth_pushing_now`: `{aggregate['not_worth_pushing_now']}`",
    ]
    return lines


def _render_historical_comparison(summary: dict[str, Any]) -> list[str]:
    lines = [
        "## Comparison vs `cutoff_only_audit_2026-03-26`",
        "",
    ]
    changed = summary["aggregate_lists"]["changed_vs_cutoff_only_audit_2026_03_26"]
    if not changed:
        lines.append("- No overlapping paper shows a material difference against the historical cutoff-only audit.")
        return lines

    for paper_id in changed:
        comparison = summary["papers"][paper_id]["historical_comparison"]
        lines.append(f"### {paper_id}")
        for key, diff in comparison["differences"].items():
            lines.append(f"- `{key}` old=`{json.dumps(diff['old'], ensure_ascii=False)}` new=`{json.dumps(diff['new'], ensure_ascii=False)}`")
        lines.append("")
    return lines


def _render_per_paper_notes(summary: dict[str, Any]) -> list[str]:
    lines = ["## Per-Paper Notes", ""]
    for paper_id in summary["paper_order"]:
        paper = summary["papers"][paper_id]
        verdict = paper["pdf_semantic_audit"]["semantic_risk_verdict"]
        lines.append(f"### {paper_id}")
        lines.append(f"- Primary verdict: `{verdict}`")
        reasons = paper["pdf_semantic_audit"]["verdict_reasons"]
        if reasons:
            lines.append(f"- Core rationale: `{reasons[0]}`")
        if paper["gold_audit"].get("available"):
            lines.append(
                f"- Gold-positive cutoffed: `{paper['gold_audit']['gold_positive_cutoffed']}`"
            )
        snippets = paper["pdf_semantic_audit"]["snippets"][:3]
        if snippets:
            for snippet in snippets:
                lines.append(
                    f"- PDF p.{snippet['page_number']}: \"{snippet['quote']}\""
                )
        else:
            lines.append("- PDF evidence snippet: `(none auto-extracted)`")
        lines.append("")
    return lines


def _render_conclusion(summary: dict[str, Any]) -> list[str]:
    aggregate = summary["aggregate_lists"]
    lines = [
        "## Conclusion",
        "",
        f"- 值得 push 上 GitHub 繼續追：`{aggregate['worth_pushing_to_github']}`",
        f"- 暫時不值得：`{aggregate['not_worth_pushing_now']}`",
    ]
    return lines


def _render_report(summary: dict[str, Any]) -> str:
    lines: list[str] = [
        "# All-16 Cutoff Semantic Audit",
        "",
        f"- Generated at: `{summary['generated_at']}`",
        f"- Output dir: `{summary['output_dir']}`",
        "- Runtime basis: current `scripts/screening/cutoff_time_filter.py` + active `cutoff_jsons/<paper_id>.json`",
        "- PDF basis: `pdftotext -layout` on `refs/<paper_id>/<paper_id>.pdf`",
        "",
    ]
    for section in (
        _render_availability_table(summary),
        [""],
        _render_gold_table(summary),
        [""],
        _render_semantic_table(summary),
        [""],
        _render_key_lists(summary),
        [""],
        _render_historical_comparison(summary),
        [""],
        _render_per_paper_notes(summary),
        [""],
        _render_conclusion(summary),
    ):
        lines.extend(section)
    return "\n".join(lines).rstrip() + "\n"


def _render_docs_summary(summary: dict[str, Any]) -> str:
    aggregate = summary["aggregate_lists"]
    lines = [
        "# Cutoff Semantic Audit (All 16 Papers)",
        "",
        f"Date: {summary['generated_at'][:10]}",
        "",
        "## 結論先行",
        "",
        f"- `2511-like issue` 候選：`{aggregate['2511_like_candidate_papers']}`",
        f"- `cutoff_json derivation bug` 候選：`{aggregate['cutoff_derivation_issue_papers']}`",
        f"- `needs manual review`：`{aggregate['needs_manual_review_papers']}`",
        f"- 值得 push 到 GitHub 追的 paper：`{aggregate['worth_pushing_to_github']}`",
        f"- 暫時不值得追：`{aggregate['not_worth_pushing_now']}`",
        "",
        "## Gold-backed High-Risk Papers",
        "",
    ]
    for paper_id in summary["aggregate_lists"]["high_risk_gold_cutoff_papers"]:
        paper = summary["papers"][paper_id]
        gold = paper["gold_audit"]
        lines.append(
            f"- `{paper_id}`: `gold_positive_cutoffed={gold['gold_positive_cutoffed']}`, primary verdict=`{paper['pdf_semantic_audit']['semantic_risk_verdict']}`"
        )
    lines.extend(["", "## Main Lists", ""])
    lines.append(f"- `parser_only_issue_papers`: `{aggregate['parser_only_issue_papers']}`")
    lines.append(f"- `retrieval_vs_screening_confusion_papers`: `{aggregate['retrieval_vs_screening_confusion_papers']}`")
    lines.append(f"- `scope_mismatch_papers`: `{aggregate['scope_mismatch_papers']}`")
    lines.append("")
    lines.append("## Current Runtime Note")
    lines.append("")
    lines.append("- 本次 audit 以 current disk state 為準；如果和 `cutoff_only_audit_2026-03-26` 或舊 memo 不同，代表 current parser / metadata / runtime 已有變動。")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the all-16 cutoff semantic audit.")
    parser.add_argument("paper_ids", nargs="*", default=DEFAULT_PAPERS, help="Paper ids to audit.")
    parser.add_argument(
        "--output-dir",
        default=f"screening/results/cutoff_semantic_audit_all16_{datetime.now().date().isoformat()}",
        help="Output directory for audit artifacts.",
    )
    parser.add_argument(
        "--docs-output",
        default=f"docs/cutoff_semantic_audit_all16_{datetime.now().date().isoformat()}_zh.md",
        help="GitHub-friendly docs summary output path.",
    )
    args = parser.parse_args()

    if PDFTOTEXT is None:
        raise SystemExit("pdftotext is required but was not found in PATH")

    output_dir = (REPO_ROOT / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    papers_dir = output_dir / "papers"
    papers_dir.mkdir(parents=True, exist_ok=True)

    old_summary = _load_old_cutoff_summary()
    papers: dict[str, dict[str, Any]] = {}
    for paper_id in args.paper_ids:
        paper_audit = _build_paper_audit(paper_id, old_summary)
        papers[paper_id] = paper_audit
        _write_json(papers_dir / paper_id / "audit.json", paper_audit)

    summary = _build_summary(list(args.paper_ids), papers, output_dir)
    _write_json(output_dir / "summary.json", summary)
    (output_dir / "report.md").write_text(_render_report(summary), encoding="utf-8")

    docs_output = (REPO_ROOT / args.docs_output).resolve()
    docs_output.parent.mkdir(parents=True, exist_ok=True)
    docs_output.write_text(_render_docs_summary(summary), encoding="utf-8")

    print(f"[cutoff-semantic-audit] wrote {_relative(output_dir / 'summary.json')}")
    print(f"[cutoff-semantic-audit] wrote {_relative(output_dir / 'report.md')}")
    print(f"[cutoff-semantic-audit] wrote {_relative(docs_output)}")


if __name__ == "__main__":
    main()
