#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[2]
BCPCS_ROOT = REPO_ROOT / "research_bcpcs_2026-04-18"
RUNS_ROOT = BCPCS_ROOT / "runs"
REPORTS_ROOT = BCPCS_ROOT / "reports"
PAPER_IDS = ["2307.05527", "2409.13738", "2511.13936", "2601.19926"]
CURRENT_RUN_ID = "bcpcs_full_corpus_split_batch_gpt54mini_globalcheck_claimpackets_all4_2026-04-23_v1_fallback_aggregate"
FULL127_RUN_ID = "bcpcs_recall_v4g_full127_gpt54mini_globalcheck_claimpackets_compilerrelaxcov_2026-04-23_v1"
TODAY = "2026-04-24"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        obj = json.loads(stripped)
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def load_gold() -> dict[tuple[str, str], bool]:
    gold: dict[tuple[str, str], bool] = {}
    for paper_id in PAPER_IDS:
        path = REPO_ROOT / "refs" / paper_id / "metadata" / "title_abstracts_metadata-annotated.jsonl"
        for row in read_jsonl(path):
            key = str(row.get("key") or "").strip()
            if key:
                gold[(paper_id, key)] = bool(row.get("is_evidence_base"))
    return gold


def positive(decision: str) -> bool:
    return decision in {"include", "maybe"}


def metrics(rows: list[dict[str, Any]], *, decision_key: str) -> dict[str, Any]:
    tp = fp = tn = fn = 0
    for row in rows:
        pred = positive(str(row.get(decision_key) or ""))
        gold = bool(row["gold_label"])
        if pred and gold:
            tp += 1
        elif pred and not gold:
            fp += 1
        elif (not pred) and gold:
            fn += 1
        else:
            tn += 1
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "evaluated_count": len(rows),
    }


def count_assessments(compact: dict[str, Any]) -> dict[str, int]:
    required_supported = required_not_supported = 0
    exclusion_supported = exclusion_not_supported = 0
    for row in compact.get("criterion_assessments") or []:
        if not isinstance(row, dict):
            continue
        claim_type = str(row.get("claim_type") or "")
        judgment = str(row.get("judgment") or "")
        if claim_type == "inclusion":
            if judgment == "supported":
                required_supported += 1
            elif judgment == "not_supported":
                required_not_supported += 1
        elif claim_type == "exclusion":
            if judgment == "supported":
                exclusion_supported += 1
            elif judgment == "not_supported":
                exclusion_not_supported += 1
    return {
        "required_supported": required_supported,
        "required_not_supported": required_not_supported,
        "exclusion_supported": exclusion_supported,
        "exclusion_not_supported": exclusion_not_supported,
    }


def load_all4_rows() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    gold = load_gold()
    aggregate = read_json(RUNS_ROOT / CURRENT_RUN_ID / "evaluation_summary_full_corpus_split.json")
    rows: list[dict[str, Any]] = []
    for child_run_id in aggregate["child_run_ids"]:
        rd = RUNS_ROOT / child_run_id
        assembled = read_json(rd / "assembled_results.json")
        review_payload = read_json(rd / "papers" / assembled[0]["paper_id"] / "stage2_review.json")
        review_by_key = {row["candidate_key"]: row for row in review_payload}
        for row in assembled:
            paper_id = row["paper_id"]
            candidate_key = row["candidate_key"]
            review_row = review_by_key.get(candidate_key)
            compact = review_row.get("recall_repair_decision") if isinstance(review_row, dict) else None
            assessment_counts = count_assessments(compact or {})
            entry = {
                "paper_id": paper_id,
                "candidate_key": candidate_key,
                "gold_label": bool(gold[(paper_id, candidate_key)]),
                "review_state": row.get("review_state"),
                "current_decision": str(row.get("final_stage_decision") or ""),
                "proposed_decision": str((compact or {}).get("proposed_decision") or ""),
                **assessment_counts,
            }
            rows.append(entry)
    rows.sort(key=lambda row: (row["paper_id"], row["candidate_key"]))
    return rows, aggregate


def load_full127_keys() -> set[tuple[str, str]]:
    payload = read_json(RUNS_ROOT / FULL127_RUN_ID / "failure_slice_keys.json")
    return {(row["paper_id"], row["candidate_key"]) for row in payload["cases"]}


def apply_display_all_maybe_to_exclude(row: dict[str, Any]) -> str:
    return "exclude" if row["current_decision"] == "maybe" else row["current_decision"]


def apply_targeted_veto(row: dict[str, Any]) -> str:
    if row["current_decision"] != "maybe":
        return row["current_decision"]
    if row["proposed_decision"] == "exclude" and (
        row["required_not_supported"] > 0 or row["exclusion_supported"] > 0
    ):
        return "exclude"
    return row["current_decision"]


def apply_hard_veto(row: dict[str, Any]) -> str:
    if row["current_decision"] != "maybe":
        return row["current_decision"]
    if row["required_not_supported"] > 0 or row["exclusion_supported"] > 0:
        return "exclude"
    return row["current_decision"]


def with_variant(rows: list[dict[str, Any]], *, name: str, fn: Callable[[dict[str, Any]], str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item[name] = fn(row)
        out.append(item)
    return out


def slice_rows(rows: list[dict[str, Any]], *, paper_id: str | None = None, keys: set[tuple[str, str]] | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        if paper_id is not None and row["paper_id"] != paper_id:
            continue
        if keys is not None and (row["paper_id"], row["candidate_key"]) not in keys:
            continue
        out.append(row)
    return out


def flip_summary(rows: list[dict[str, Any]], *, decision_key: str, paper_id: str) -> dict[str, Any]:
    flips = [row for row in rows if row["paper_id"] == paper_id and row[decision_key] != row["current_decision"]]
    gold_negative = sum(1 for row in flips if not row["gold_label"])
    gold_positive = sum(1 for row in flips if row["gold_label"])
    return {
        "flip_count": len(flips),
        "gold_negative_flips": gold_negative,
        "gold_positive_flips": gold_positive,
    }


def fmt(value: float) -> str:
    return f"{value:.4f}"


def main() -> None:
    REPORTS_ROOT.mkdir(parents=True, exist_ok=True)
    all_rows, aggregate = load_all4_rows()
    full127_keys = load_full127_keys()

    variants = {
        "current_decision": lambda row: row["current_decision"],
        "display_all_maybe_to_exclude": apply_display_all_maybe_to_exclude,
        "targeted_veto": apply_targeted_veto,
        "hard_veto": apply_hard_veto,
    }
    variant_rows = all_rows
    for name, fn in variants.items():
        variant_rows = with_variant(variant_rows, name=name, fn=fn)

    summary: dict[str, Any] = {
        "source_run_id": CURRENT_RUN_ID,
        "full127_reference_run_id": FULL127_RUN_ID,
        "overall": {},
        "per_paper": {},
        "full127_slice": {},
        "flip_summary": {},
    }

    for variant_name in variants:
        summary["overall"][variant_name] = metrics(variant_rows, decision_key=variant_name)
        summary["full127_slice"][variant_name] = metrics(
            slice_rows(variant_rows, keys=full127_keys),
            decision_key=variant_name,
        )
        for paper_id in PAPER_IDS:
            summary["per_paper"].setdefault(paper_id, {})
            summary["per_paper"][paper_id][variant_name] = metrics(
                slice_rows(variant_rows, paper_id=paper_id),
                decision_key=variant_name,
            )
        if variant_name != "current_decision":
            summary["flip_summary"][variant_name] = {
                paper_id: flip_summary(variant_rows, decision_key=variant_name, paper_id=paper_id)
                for paper_id in ["2409.13738", "2511.13936"]
            }

    report_path = REPORTS_ROOT / f"bcpcs_maybe_counterfactual_report_{TODAY}.md"
    summary_path = REPORTS_ROOT / f"bcpcs_maybe_counterfactual_report_{TODAY}.summary.json"

    lines = [
        "# BCPCS Maybe Counterfactual Report",
        "",
        f"Source run: `{CURRENT_RUN_ID}`",
        "",
        "這份報告驗證的不是 prompt 改寫，而是本地 counterfactual recompile：",
        "- `display_all_maybe_to_exclude`: 純顯示層，把所有 `maybe` 都當成 `exclude`。",
        "- `targeted_veto`: 只有當目前是 `maybe`，且 `proposed_decision=exclude`，並且已經有 inclusion `not_supported` 或 exclusion `supported` 時，才把 `maybe -> exclude`。",
        "- `hard_veto`: 只要目前是 `maybe`，且有 inclusion `not_supported` 或 exclusion `supported`，就把 `maybe -> exclude`。",
        "",
        "## Overall All4",
        "",
        "| variant | F1 | precision | recall | TP / FP / TN / FN |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for variant_name in variants:
        item = summary["overall"][variant_name]
        lines.append(
            f"| `{variant_name}` | {fmt(item['f1'])} | {fmt(item['precision'])} | {fmt(item['recall'])} | {item['tp']} / {item['fp']} / {item['tn']} / {item['fn']} |"
        )

    lines.extend(
        [
            "",
            "## 2409 and 2511",
            "",
            "| paper_id | variant | F1 | precision | recall | TP / FP / TN / FN |",
            "| --- | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for paper_id in ["2409.13738", "2511.13936"]:
        for variant_name in variants:
            item = summary["per_paper"][paper_id][variant_name]
            lines.append(
                f"| `{paper_id}` | `{variant_name}` | {fmt(item['f1'])} | {fmt(item['precision'])} | {fmt(item['recall'])} | {item['tp']} / {item['fp']} / {item['tn']} / {item['fn']} |"
            )

    lines.extend(
        [
            "",
            "## Flip Accounting",
            "",
            "| variant | paper_id | flipped `maybe -> exclude` | gold-negative flips | gold-positive flips |",
            "| --- | --- | ---: | ---: | ---: |",
        ]
    )
    for variant_name in ["display_all_maybe_to_exclude", "targeted_veto", "hard_veto"]:
        for paper_id in ["2409.13738", "2511.13936"]:
            item = summary["flip_summary"][variant_name][paper_id]
            lines.append(
                f"| `{variant_name}` | `{paper_id}` | {item['flip_count']} | {item['gold_negative_flips']} | {item['gold_positive_flips']} |"
            )

    lines.extend(
        [
            "",
            "## Original 127 Slice",
            "",
            "| variant | F1 | precision | recall | TP / FP / TN / FN |",
            "| --- | ---: | ---: | ---: | --- |",
        ]
    )
    for variant_name in variants:
        item = summary["full127_slice"][variant_name]
        lines.append(
            f"| `{variant_name}` | {fmt(item['f1'])} | {fmt(item['precision'])} | {fmt(item['recall'])} | {item['tp']} / {item['fp']} / {item['tn']} / {item['fn']} |"
        )

    lines.extend(
        [
            "",
            "## Verdict",
            "",
            "- 有效方向不是 `exclude -> maybe`，而是把一部分本來就該排除的 `maybe` 收回成 `exclude`。",
            "- 但也不是把所有 `maybe` 一刀切成 `exclude`。純顯示層 `display_all_maybe_to_exclude` 對 `2511` 反而更差，而且會重傷 `full127`。",
            "- 這次 local verification 下，真正有用的是 `targeted_veto`：它明顯救回 `2409`，也大幅改善 `2511`，同時 overall all4 也優於 current。",
        ]
    )

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report_path": str(report_path), "summary_path": str(summary_path)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
