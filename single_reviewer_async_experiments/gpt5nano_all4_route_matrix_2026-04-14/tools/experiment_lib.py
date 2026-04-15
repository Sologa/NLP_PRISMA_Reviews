from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any


FULLTEXT_TRUNCATION_MARKER = "\n\n[...TRUNCATED...]\n\n"
METHOD_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(method|approach|model|training)\b", re.IGNORECASE)
EVAL_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(evaluation|experiment|experiments|results)\b", re.IGNORECASE)
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+")
WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_\-/+]*")


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
        if isinstance(value, str):
            replacement = value
        else:
            replacement = json.dumps(value, ensure_ascii=False, indent=2)
        rendered = rendered.replace(placeholder, replacement)
    return rendered


def decision_from_score(score: int) -> str:
    if score >= 4:
        return "include"
    if score <= 2:
        return "exclude"
    return "maybe"


def stage_verdict(stage: str, stage_score: int) -> str:
    return f"{decision_from_score(stage_score)} ({stage}:{stage_score})"


def verdict_label(final_verdict: str) -> str:
    match = re.match(r"^\s*([a-z]+)", safe_text(final_verdict).lower())
    if not match:
        return "unknown"
    return match.group(1)


def prediction_from_verdict(final_verdict: str, positive_mode: str = "include_or_maybe") -> int:
    label = verdict_label(final_verdict)
    if label == "include":
        return 1
    if label == "maybe":
        return 1 if positive_mode == "include_or_maybe" else 0
    return 0


def _fbeta(precision: float, recall: float, beta: float) -> float:
    beta_sq = beta * beta
    denom = beta_sq * precision + recall
    if denom == 0.0:
        return 0.0
    return (1 + beta_sq) * precision * recall / denom


def compute_metrics(*, tp: int, fp: int, tn: int, fn: int) -> dict[str, Any]:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": _fbeta(precision, recall, 1.0),
        "f2": _fbeta(precision, recall, 2.0),
        "f3": _fbeta(precision, recall, 3.0),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
    }


def compute_metrics_from_rows(
    *,
    results: list[dict[str, Any]],
    gold_records: list[dict[str, Any]],
    positive_mode: str = "include_or_maybe",
) -> dict[str, Any]:
    gold_map: dict[str, int] = {}
    for row in gold_records:
        key = safe_text(row.get("key"))
        if not key:
            continue
        label = row.get("is_evidence_base")
        gold_map[key] = 1 if bool(label) else 0

    pred_map: dict[str, int] = {}
    for row in results:
        key = safe_text(row.get("key"))
        if not key:
            continue
        pred_map[key] = prediction_from_verdict(safe_text(row.get("final_verdict")), positive_mode=positive_mode)

    matched_keys = sorted(set(gold_map) & set(pred_map))
    tp = fp = tn = fn = 0
    for key in matched_keys:
        truth = gold_map[key]
        pred = pred_map[key]
        if truth == 1 and pred == 1:
            tp += 1
        elif truth == 1 and pred == 0:
            fn += 1
        elif truth == 0 and pred == 1:
            fp += 1
        else:
            tn += 1
    metrics = compute_metrics(tp=tp, fp=fp, tn=tn, fn=fn)
    metrics["matched"] = len(matched_keys)
    metrics["gold_size"] = len(gold_map)
    metrics["results_size"] = len(results)
    return metrics


def unresolved_criterion_ids(review_output: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for item in review_output.get("criterion_assessments", []):
        if safe_text(item.get("status")).upper() == "UNCLEAR":
            out.append(safe_text(item.get("criterion_id")))
    return out


def _criterion_conflict(review_output: dict[str, Any]) -> bool:
    seen_yes_inclusion = False
    seen_yes_exclusion = False
    for item in review_output.get("criterion_assessments", []):
        status = safe_text(item.get("status")).upper()
        criterion_id = safe_text(item.get("criterion_id")).upper()
        if status != "YES":
            continue
        if criterion_id.startswith("I"):
            seen_yes_inclusion = True
        if criterion_id.startswith("E"):
            seen_yes_exclusion = True
    return seen_yes_inclusion and seen_yes_exclusion


def _notes_blob(review_output: dict[str, Any]) -> str:
    parts: list[str] = [safe_text(review_output.get("decision_rationale")), safe_text(review_output.get("routing_note"))]
    for item in review_output.get("criterion_assessments", []):
        parts.append(safe_text(item.get("notes")))
        parts.extend([safe_text(v) for v in item.get("supporting_quotes", [])])
        parts.extend([safe_text(v) for v in item.get("counter_quotes", [])])
    return "\n".join(part for part in parts if part)


def should_route_verification(
    *,
    paper_id: str,
    stage: str,
    review_output: dict[str, Any],
    paper_profile: dict[str, Any],
) -> dict[str, Any]:
    reasons: list[str] = []
    if bool(review_output.get("manual_review_needed")):
        reasons.append("manual_review_needed")

    unclear_ids = unresolved_criterion_ids(review_output)
    if unclear_ids:
        reasons.append("criterion_unclear")

    if _criterion_conflict(review_output):
        reasons.append("evidence_conflict")

    if stage == "stage1" and int(review_output.get("stage_score") or 3) <= 2:
        inclusion_statuses = [
            safe_text(item.get("status")).upper()
            for item in review_output.get("criterion_assessments", [])
            if safe_text(item.get("criterion_id")).upper().startswith("I")
        ]
        if inclusion_statuses and any(status != "NO" for status in inclusion_statuses):
            reasons.append("stage1_exclude_not_all_core_no")

    blob = _notes_blob(review_output).lower()
    trap_hits: list[str] = []
    for term in paper_profile.get("semantic_traps", []):
        normalized = safe_text(term).lower()
        if normalized and normalized in blob:
            trap_hits.append(normalized)
    if trap_hits:
        reasons.append("semantic_trap")

    return {
        "paper_id": paper_id,
        "stage": stage,
        "should_route": bool(reasons),
        "reasons": reasons,
        "trap_hits": trap_hits,
        "unclear_criterion_ids": unclear_ids,
    }


def _tokenize(text: str) -> set[str]:
    return {token.lower() for token in WORD_RE.findall(text)}


def _chunk_markdown(text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    chunks: list[dict[str, Any]] = []
    current_heading = "ROOT"
    buffer: list[str] = []

    def flush() -> None:
        nonlocal buffer
        chunk_text = "\n".join(buffer).strip()
        if chunk_text:
            chunks.append(
                {
                    "heading": current_heading,
                    "text": chunk_text,
                    "char_count": len(chunk_text),
                }
            )
        buffer = []

    for line in lines:
        if HEADING_RE.match(line):
            flush()
            current_heading = line.strip()
            buffer.append(line)
            continue
        if not line.strip() and buffer:
            flush()
            continue
        buffer.append(line)
    flush()
    return chunks


def _score_chunk(
    chunk: dict[str, Any],
    *,
    unresolved_ids: list[str],
    paper_profile: dict[str, Any],
) -> float:
    heading = safe_text(chunk.get("heading"))
    text = safe_text(chunk.get("text"))
    lowered = text.lower()
    score = 0.0
    if METHOD_HEADING_RE.match(heading):
        score += 10.0
    if EVAL_HEADING_RE.match(heading):
        score += 10.0

    keywords = []
    keywords.extend(paper_profile.get("retrieval_priority_terms", []))
    keywords.extend(paper_profile.get("verification_focus", []))
    keywords.extend(paper_profile.get("core_fit_terms", []))
    for item in keywords:
        term = safe_text(item).lower()
        if term and term in lowered:
            score += 6.0

    for item in paper_profile.get("non_target_terms", []):
        term = safe_text(item).lower()
        if term and term in lowered:
            score += 3.0

    token_set = _tokenize(text)
    for criterion_id in unresolved_ids:
        for token in _tokenize(criterion_id.replace("_", " ")):
            if token in token_set:
                score += 1.0

    score += min(len(text) / 2000.0, 2.0)
    return score


def select_snippet_pack(
    *,
    fulltext_text: str,
    prior_review_output: dict[str, Any],
    paper_profile: dict[str, Any],
    max_chars: int = 24000,
) -> tuple[str, dict[str, Any]]:
    chunks = _chunk_markdown(fulltext_text)
    unresolved_ids = unresolved_criterion_ids(prior_review_output)
    ranked = sorted(
        (
            {
                **chunk,
                "score": _score_chunk(chunk, unresolved_ids=unresolved_ids, paper_profile=paper_profile),
            }
            for chunk in chunks
        ),
        key=lambda item: (-float(item["score"]), safe_text(item.get("heading"))),
    )

    selected: list[dict[str, Any]] = []
    total_chars = 0
    for chunk in ranked:
        text = safe_text(chunk.get("text"))
        if not text:
            continue
        projected = total_chars + len(text)
        if selected and projected > max_chars:
            continue
        selected.append(chunk)
        total_chars = projected
        if total_chars >= max_chars:
            break

    selected_text = "\n\n".join(safe_text(item.get("text")) for item in selected)
    if len(selected_text) > max_chars:
        selected_text = selected_text[:max_chars] + FULLTEXT_TRUNCATION_MARKER
    return selected_text, {
        "selected_chunk_count": len(selected),
        "fulltext_chars_total": len(fulltext_text),
        "fulltext_chars_used": len(selected_text),
        "selected_headings": [safe_text(item.get("heading")) for item in selected],
        "unresolved_criterion_ids": unresolved_ids,
    }


def compute_auto_resolution_coverage(*, total_rows: int, verification_rows: int) -> float:
    if total_rows <= 0:
        return 0.0
    return (total_rows - verification_rows) / total_rows


def compute_verification_overturn_rate(*, verification_rows: int, overturned_rows: int) -> float:
    if verification_rows <= 0:
        return 0.0
    return overturned_rows / verification_rows


def load_best_observed_single_reviewer(summary_csv_path: Path) -> dict[str, dict[str, Any]]:
    best_by_paper: dict[str, dict[str, Any]] = {}
    with summary_csv_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if not isinstance(row, dict):
                continue
            paper_id = safe_text(row.get("paper_id"))
            if not paper_id:
                continue
            try:
                combined_f1 = float(row.get("combined_f1") or 0.0)
            except ValueError:
                combined_f1 = 0.0
            current = best_by_paper.get(paper_id)
            if current is None or combined_f1 > float(current.get("combined_f1") or 0.0):
                best_by_paper[paper_id] = dict(row)
    return best_by_paper


def summarize_terminal_failures(failure_rows: list[dict[str, Any]]) -> dict[str, Any]:
    counter: Counter[str] = Counter()
    for row in failure_rows:
        counter[safe_text(row.get("error_type")) or safe_text(row.get("status")) or "unknown"] += 1
    return {"terminal_failure_count": len(failure_rows), "by_error_type": dict(counter)}


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
