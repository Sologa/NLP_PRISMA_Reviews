from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


RESEARCH_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = RESEARCH_ROOT.parent


def ensure_inside_research_root(path: Path) -> Path:
    resolved = path.resolve()
    root = RESEARCH_ROOT.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Refusing to write outside research root: {resolved}") from exc
    return resolved


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        item = json.loads(stripped)
        if not isinstance(item, dict):
            raise ValueError(f"Expected object at {path}:{line_number}")
        rows.append(item)
    return rows


def write_json(path: Path, payload: Any) -> None:
    target = ensure_inside_research_root(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    target = ensure_inside_research_root(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    target = ensure_inside_research_root(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def repo_path(relative_path: str | Path) -> Path:
    path = Path(relative_path)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def relative_to_repo(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(resolved)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest() -> dict[str, Any]:
    return load_json(REPO_ROOT / "screening/results/results_manifest.json")


def criteria_path(paper_id: str, stage: str) -> Path:
    if stage not in {"stage1", "stage2"}:
        raise ValueError(f"Unsupported stage: {stage}")
    return REPO_ROOT / f"criteria_{stage}" / f"{paper_id}.json"


def metadata_path(paper_id: str) -> Path:
    return REPO_ROOT / "refs" / paper_id / "metadata" / "title_abstracts_metadata.jsonl"


def annotated_metadata_path(paper_id: str) -> Path:
    return REPO_ROOT / "refs" / paper_id / "metadata" / "title_abstracts_metadata-annotated.jsonl"


def cutoff_path(paper_id: str) -> Path:
    return REPO_ROOT / "cutoff_jsons" / f"{paper_id}.json"


def _criterion_text(item: Any) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        return str(item.get("criterion") or item.get("text") or "").strip()
    return str(item or "").strip()


def _criterion_source(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("source") or "").strip()
    return ""


def _criterion_topic_ids(item: Any) -> list[str]:
    if isinstance(item, dict) and isinstance(item.get("topic_ids"), list):
        return [str(value) for value in item["topic_ids"]]
    return []


def _stage_observability(stage: str, criterion_text: str) -> str:
    lowered = criterion_text.lower()
    if stage == "stage1":
        if "defer" in lowered or "full-text" in lowered or "full text" in lowered:
            return "deferred_to_stage2"
        return "observable_stage1"
    if "metadata" in lowered or "language" in lowered or "full text" in lowered:
        return "metadata_only"
    return "observable_stage2"


def compile_stub_graph(paper_id: str, stage: str) -> dict[str, Any]:
    path = criteria_path(paper_id, stage)
    criteria = load_json(path)
    required = criteria.get("inclusion_criteria", {}).get("required", [])
    exclusions = criteria.get("exclusion_criteria", [])
    claims: list[dict[str, Any]] = []
    prefix = "S1" if stage == "stage1" else "S2"

    for index, item in enumerate(required, start=1):
        text = _criterion_text(item)
        if not text:
            continue
        claims.append(
            {
                "claim_id": f"{prefix}-IC{index}",
                "claim_text": text,
                "claim_type": "inclusion",
                "required_status": "support",
                "decision_operator": "all",
                "source_criterion_ids": [f"IC{index}"],
                "stage_observability": _stage_observability(stage, text),
                "source": _criterion_source(item),
                "topic_ids": _criterion_topic_ids(item),
            }
        )

    for index, item in enumerate(exclusions, start=1):
        text = _criterion_text(item)
        if not text:
            continue
        claims.append(
            {
                "claim_id": f"{prefix}-EC{index}",
                "claim_text": text,
                "claim_type": "exclusion",
                "required_status": "refute_absent",
                "decision_operator": "exclude_if_refute",
                "source_criterion_ids": [f"EC{index}"],
                "stage_observability": _stage_observability(stage, text),
                "source": _criterion_source(item),
                "topic_ids": _criterion_topic_ids(item),
            }
        )

    return {
        "schema_version": "0.1.0",
        "review_id": paper_id,
        "stage": stage,
        "criterion_source_path": relative_to_repo(path),
        "topic": str(criteria.get("topic") or ""),
        "topic_definition": str(criteria.get("topic_definition") or ""),
        "claims": claims,
        "decision_graph": {
            "include_rule": "All required inclusion claims are supported and no exclusion claim is refuted by disqualifying evidence.",
            "exclude_rule": "Any exclusion claim with validated refute evidence can force exclude when stage-observable.",
            "route_rule": "Unknown or stage-incomplete critical claims route to SeniorLead/human adjudication instead of silent include/exclude.",
        },
    }


def parse_bool(value: Any) -> bool | None:
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
    return None


def load_records(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".jsonl":
        return load_jsonl(path)
    payload = load_json(path)
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("records", "items", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
    raise ValueError(f"Unsupported record file format: {path}")


def find_key(item: dict[str, Any]) -> str | None:
    key = item.get("key")
    if key is not None:
        stripped = str(key).strip()
        if stripped:
            return stripped
    metadata = item.get("metadata")
    if isinstance(metadata, dict):
        key = metadata.get("key")
        if key is not None:
            stripped = str(key).strip()
            if stripped:
                return stripped
    return None


def _index_records_by_key(records: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], list[str], int]:
    keyed: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    dropped_no_key = 0
    for row in records:
        key = find_key(row)
        if not key:
            dropped_no_key += 1
            continue
        if key not in keyed:
            keyed[key] = row
            order.append(key)
    return keyed, order, dropped_no_key


def infer_base_review_results(report_path: Path, report: dict[str, Any]) -> Path | None:
    if "combined" not in report_path.name.lower():
        return None
    results_path = repo_path(report["results_path"])
    if results_path.name == "latte_fulltext_review_from_run01.json":
        for candidate in (
            results_path.parent / "run01" / "latte_review_results.run01.json",
            results_path.parent / "run01" / "latte_review_results.json",
        ):
            if candidate.exists():
                return candidate
        return None
    if results_path.name.startswith("latte_fulltext_review_results"):
        suffix = results_path.name.removeprefix("latte_fulltext_review_results")
        candidate = results_path.parent / f"latte_review_results{suffix}"
        if candidate.exists():
            return candidate
    if results_path.name == "latte_fulltext_review_results.json":
        candidate = results_path.parent / "latte_review_results.json"
        if candidate.exists():
            return candidate
    return None


def _int_to_bool(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)) and value == int(value):
        score = int(value)
    else:
        try:
            score = int(str(value).strip())
        except ValueError:
            return None
    if score >= 4:
        return 1
    if score <= 2:
        return 0
    return None


def to_verdict_bool(value: Any, positive_mode: str) -> int | None:
    verdict = str(value or "").strip().lower()
    if not verdict:
        return None
    match = re.match(r"^\s*([a-z]+)", verdict)
    if not match:
        return None
    label = match.group(1)
    if label == "include":
        return 1
    if label == "maybe":
        return 1 if positive_mode in {"include_or_maybe", "maybe_only"} else 0
    if label == "exclude":
        return 0
    return None


def predict_row(row: dict[str, Any], positive_mode: str) -> int:
    pred = to_verdict_bool(row.get("final_verdict"), positive_mode)
    if pred is not None:
        return pred
    if row.get("round-B_SeniorLead_evaluation") is not None:
        pred = _int_to_bool(row.get("round-B_SeniorLead_evaluation"))
    elif row.get("round-A_JuniorNano_evaluation") is not None:
        pred = _int_to_bool(row.get("round-A_JuniorNano_evaluation"))
    return 0 if pred is None else pred


def precision_recall_f1(tp: int, fp: int, fn: int) -> dict[str, float]:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def recompute_f1_from_report(report_path: Path) -> dict[str, Any]:
    report = load_json(report_path)
    results_path = repo_path(report["results_path"])
    gold_path = repo_path(report["gold_path"])
    positive_mode = str(report.get("positive_mode") or "include_or_maybe")
    results = load_records(results_path)
    base_path = infer_base_review_results(report_path, report)
    base_results = load_records(base_path) if base_path is not None else None
    gold_records = load_records(gold_path)

    gold_map: dict[str, int] = {}
    for row in gold_records:
        key = str(row.get("key") or "").strip()
        label = parse_bool(row.get("is_evidence_base"))
        if key and label is not None:
            gold_map[key] = 1 if label else 0

    pred_map: dict[str, int] = {}
    verdict_counter: dict[str, int] = {}
    combined_rows: list[dict[str, Any]]
    dropped_no_key = 0
    if base_results is not None:
        base_records, base_order, base_dropped = _index_records_by_key(base_results)
        fulltext_records, _, fulltext_dropped = _index_records_by_key(results)
        dropped_no_key = base_dropped + fulltext_dropped
        combined_rows = []
        for key in base_order:
            base_row = base_records[key]
            merged = dict(base_row)
            source_row = base_row
            if key in fulltext_records:
                fulltext_row = fulltext_records[key]
                merged.update(fulltext_row)
                merged["base_final_verdict"] = str(base_row.get("final_verdict") or "")
                source_row = fulltext_row
            verdict = str(source_row.get("final_verdict") or "")
            verdict_counter[verdict] = verdict_counter.get(verdict, 0) + 1
            pred_map[key] = predict_row(source_row, positive_mode)
            merged["key"] = key
            combined_rows.append(merged)
        for key, fulltext_row in fulltext_records.items():
            if key in base_records:
                continue
            pred_map[key] = predict_row(fulltext_row, positive_mode)
            verdict = str(fulltext_row.get("final_verdict") or "")
            verdict_counter[verdict] = verdict_counter.get(verdict, 0) + 1
            row_with_key = dict(fulltext_row)
            row_with_key["key"] = key
            combined_rows.append(row_with_key)
    else:
        combined_rows = results
        for row in results:
            verdict = str(row.get("final_verdict") or "")
            verdict_counter[verdict] = verdict_counter.get(verdict, 0) + 1
            key = find_key(row)
            if not key:
                dropped_no_key += 1
                continue
            pred_map[key] = predict_row(row, positive_mode)

    matched_keys = sorted(set(pred_map) & set(gold_map))
    tp = fp = tn = fn = 0
    for key in matched_keys:
        y_true = gold_map[key]
        y_pred = pred_map[key]
        if y_true == 1 and y_pred == 1:
            tp += 1
        elif y_true == 1 and y_pred == 0:
            fn += 1
        elif y_true == 0 and y_pred == 1:
            fp += 1
        else:
            tn += 1
    metrics = precision_recall_f1(tp, fp, fn)
    metrics.update({"tp": tp, "fp": fp, "tn": tn, "fn": fn})
    return {
        "paper_id": report.get("paper_id"),
        "report_path": relative_to_repo(report_path),
        "results_path": relative_to_repo(results_path),
        "base_review_results_path": relative_to_repo(base_path) if base_path is not None else None,
        "gold_path": relative_to_repo(gold_path),
        "positive_mode": positive_mode,
        "matched": len(matched_keys),
        "gold_size": len(gold_map),
        "results_size": len(combined_rows),
        "dropped_no_key": dropped_no_key,
        "verdict_counts": verdict_counter,
        "metrics": metrics,
        "stored_metrics": report.get("metrics", {}),
    }


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "be",
    "for",
    "from",
    "in",
    "is",
    "of",
    "on",
    "or",
    "paper",
    "papers",
    "study",
    "studies",
    "that",
    "the",
    "to",
    "with",
}


def lexical_evidence_stub(claim_text: str, candidate: dict[str, Any], source_path: Path) -> dict[str, Any] | None:
    title = str(candidate.get("title") or "")
    abstract = str(candidate.get("abstract") or "")
    text = f"{title}\n{abstract}".lower()
    tokens = [token for token in re.findall(r"[a-z][a-z0-9_-]{3,}", claim_text.lower()) if token not in STOPWORDS]
    for token in tokens[:20]:
        index = text.find(token)
        if index < 0:
            continue
        start = max(0, index - 90)
        end = min(len(text), index + 180)
        quote = f"{title} {abstract}"[start:end].strip()
        source_field = "title" if token in title.lower() else "abstract"
        return {
            "quote": quote[:500],
            "location": f"{source_field}:lexical_token:{token}",
            "source_path": relative_to_repo(source_path),
            "source_field": source_field,
        }
    return None
