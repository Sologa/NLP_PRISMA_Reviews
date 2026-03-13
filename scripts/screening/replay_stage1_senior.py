#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


REPO_ROOT = Path(__file__).resolve().parents[2]
VENDOR_ROOT = REPO_ROOT / "scripts" / "screening" / "vendor"
if str(VENDOR_ROOT) not in sys.path:
    sys.path.insert(0, str(VENDOR_ROOT))

from src.pipelines.runtime_prompt_loader import load_stage1_senior_prompt
from src.pipelines.topic_pipeline import (  # type: ignore
    _criteria_context_from_payload,
    _criteria_payload_to_strings,
    _derive_final_verdict_from_row,
    _ensure_latte_review_importable,
)
from src.utils.env import load_env_file


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _to_score(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        if int(value) != value:
            return None
        score = int(value)
    else:
        text = str(value).strip()
        if not text:
            return None
        if not re.fullmatch(r"-?\d+", text):
            return None
        score = int(text)
    if score < 1 or score > 5:
        return None
    return score


def _extract_verdict_label(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return "unknown"
    m = re.match(r"^([a-z]+)", text)
    if not m:
        return "unknown"
    label = m.group(1)
    if label in {"include", "exclude", "maybe", "discard"}:
        return label
    return "unknown"


def _verdict_to_pred(value: Any) -> Optional[int]:
    label = _extract_verdict_label(value)
    if label in {"include", "maybe"}:
        return 1
    if label in {"exclude", "discard"}:
        return 0
    return None


def _load_gold_labels(path: Path) -> Dict[str, int]:
    gold: Dict[str, int] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        row = json.loads(stripped)
        if not isinstance(row, dict):
            continue
        key = str(row.get("key") or "").strip()
        if not key:
            continue
        value = row.get("is_evidence_base")
        if isinstance(value, bool):
            gold[key] = 1 if value else 0
        elif isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "1", "yes", "y"}:
                gold[key] = 1
            elif lowered in {"false", "0", "no", "n"}:
                gold[key] = 0
    return gold


def _compute_metrics(rows: List[Dict[str, Any]], gold: Dict[str, int]) -> Dict[str, Any]:
    pred_map: Dict[str, int] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        key = str(row.get("key") or "").strip()
        if not key:
            continue
        pred = _verdict_to_pred(row.get("final_verdict"))
        if pred is None:
            continue
        pred_map[key] = pred

    matched = sorted(set(pred_map.keys()) & set(gold.keys()))
    tp = fp = tn = fn = 0
    for key in matched:
        y_true = gold[key]
        y_pred = pred_map[key]
        if y_true == 1 and y_pred == 1:
            tp += 1
        elif y_true == 1 and y_pred == 0:
            fn += 1
        elif y_true == 0 and y_pred == 1:
            fp += 1
        else:
            tn += 1

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    return {
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "matched": len(matched),
        "gold_size": len(gold),
        "pred_size": len(pred_map),
    }


def _build_frozen_cases(baseline_rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    frozen_cases: List[Dict[str, Any]] = []
    sent_to_senior: Dict[str, int] = {}

    for idx, row in enumerate(baseline_rows):
        if not isinstance(row, dict):
            continue
        key = str(row.get("key") or "").strip()
        if not key:
            continue
        senior_eval = _to_score(row.get("round-B_SeniorLead_evaluation"))
        if senior_eval is None:
            continue
        case = {
            "baseline_index": idx,
            "key": key,
            "title": str(row.get("title") or ""),
            "abstract": str(row.get("abstract") or ""),
            "round-A_JuniorNano_output": row.get("round-A_JuniorNano_output"),
            "round-A_JuniorNano_evaluation": _to_score(row.get("round-A_JuniorNano_evaluation")),
            "round-A_JuniorMini_output": row.get("round-A_JuniorMini_output"),
            "round-A_JuniorMini_evaluation": _to_score(row.get("round-A_JuniorMini_evaluation")),
            "baseline_round-B_SeniorLead_reasoning": row.get("round-B_SeniorLead_reasoning"),
            "baseline_round-B_SeniorLead_evaluation": senior_eval,
            "baseline_final_verdict": row.get("final_verdict"),
        }
        frozen_cases.append(case)
        sent_to_senior[key] = idx

    return frozen_cases, sent_to_senior


def _score_distribution(scores: List[Optional[int]]) -> Dict[str, int]:
    low = mid = high = missing = 0
    for score in scores:
        if score is None:
            missing += 1
        elif score <= 2:
            low += 1
        elif score == 3:
            mid += 1
        else:
            high += 1
    return {
        "1_2": low,
        "3": mid,
        "4_5": high,
        "missing": missing,
        "total": len(scores),
    }


def _load_criteria_payload(criteria_path: Path) -> Dict[str, Any]:
    payload = _read_json(criteria_path)
    if not isinstance(payload, dict):
        return {}
    structured = payload.get("structured_payload")
    if isinstance(structured, dict):
        return structured
    return payload


def _run_senior_replay(
    frozen_cases: List[Dict[str, Any]],
    *,
    criteria_payload: Dict[str, Any],
    prompt_id: str,
    senior_model: str,
    senior_reasoning_effort: str,
    max_concurrent_requests: int,
) -> Dict[str, Dict[str, Any]]:
    if not frozen_cases:
        return {}

    _ensure_latte_review_importable()

    import pandas as pd
    from resources.LatteReview.lattereview.agents import TitleAbstractReviewer
    from resources.LatteReview.lattereview.providers.openai_provider import OpenAIProvider
    from resources.LatteReview.lattereview.workflows import ReviewWorkflow

    inclusion_criteria, exclusion_criteria = _criteria_payload_to_strings(criteria_payload)
    criteria_context = _criteria_context_from_payload(criteria_payload)
    if not inclusion_criteria:
        inclusion_criteria = "論文需與指定主題高度相關，且提供可用於評估的英文內容（全文或摘要/方法）。"
    if not exclusion_criteria:
        exclusion_criteria = "論文若與主題無關，或缺乏可判斷的英文題名/摘要/方法描述則排除。"

    senior_prompt = load_stage1_senior_prompt(prompt_id)
    context = criteria_context
    if senior_prompt.additional_context:
        context = f"{criteria_context}\n{senior_prompt.additional_context}" if criteria_context else senior_prompt.additional_context

    reviewer = TitleAbstractReviewer(
        name="SeniorLead",
        provider=OpenAIProvider(model=senior_model),
        inclusion_criteria=inclusion_criteria,
        exclusion_criteria=exclusion_criteria,
        model_args={"reasoning_effort": senior_reasoning_effort} if senior_reasoning_effort else {},
        reasoning="brief",
        backstory=senior_prompt.backstory,
        additional_context=context,
        max_concurrent_requests=max_concurrent_requests,
        verbose=False,
    )

    df = pd.DataFrame(
        [
            {
                "key": case["key"],
                "title": case["title"],
                "abstract": case["abstract"],
                "round-A_JuniorNano_output": case["round-A_JuniorNano_output"],
                "round-A_JuniorNano_evaluation": case["round-A_JuniorNano_evaluation"],
                "round-A_JuniorMini_output": case["round-A_JuniorMini_output"],
                "round-A_JuniorMini_evaluation": case["round-A_JuniorMini_evaluation"],
            }
            for case in frozen_cases
        ]
    )
    df.index = [int(case["baseline_index"]) for case in frozen_cases]

    workflow = ReviewWorkflow.model_validate(
        {
            "workflow_schema": [
                {
                    "round": "B",
                    "reviewers": [reviewer],
                    "text_inputs": [
                        "title",
                        "abstract",
                        "round-A_JuniorNano_output",
                        "round-A_JuniorNano_evaluation",
                        "round-A_JuniorMini_output",
                        "round-A_JuniorMini_evaluation",
                    ],
                }
            ],
            "verbose": False,
        },
        context={"data": df},
    )
    result_df = asyncio.run(workflow.run(df))

    out: Dict[str, Dict[str, Any]] = {}
    for _, row in result_df.iterrows():
        key = str(row.get("key") or "").strip()
        if not key:
            continue
        reasoning = row.get("round-B_SeniorLead_reasoning")
        score = _to_score(row.get("round-B_SeniorLead_evaluation"))
        out[key] = {
            "key": key,
            "round-B_SeniorLead_reasoning": reasoning,
            "round-B_SeniorLead_evaluation": score,
        }
    return out


def _reconstruct_stage1(
    baseline_rows: List[Dict[str, Any]],
    replay_map: Dict[str, Dict[str, Any]],
    sent_to_senior: Dict[str, int],
) -> List[Dict[str, Any]]:
    reconstructed: List[Dict[str, Any]] = []
    sent_keys = set(sent_to_senior.keys())

    for row in baseline_rows:
        if not isinstance(row, dict):
            continue
        new_row = dict(row)
        key = str(new_row.get("key") or "").strip()
        if key and key in sent_keys and key in replay_map:
            replay = replay_map[key]
            reasoning = replay.get("round-B_SeniorLead_reasoning")
            evaluation = replay.get("round-B_SeniorLead_evaluation")
            new_row["round-B_SeniorLead_reasoning"] = reasoning
            new_row["round-B_SeniorLead_evaluation"] = evaluation
            new_row["round-B_SeniorLead_output"] = {
                "reasoning": reasoning,
                "evaluation": evaluation,
            }
            new_row["final_verdict"] = _derive_final_verdict_from_row(new_row)
        reconstructed.append(new_row)

    return reconstructed


def _spot_check_rows(
    *,
    paper_id: str,
    baseline_rows: List[Dict[str, Any]],
    replay_no_marker: Dict[str, Dict[str, Any]],
    replay_tuned: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    targets = {
        "2409.13738": ["etikala2021extracting"],
        "2511.13936": ["lotfian2016retrieving", "han2020ordinal"],
        "2601.19926": ["mccoy_right_2019"],
        "2307.05527": ["Suh2021AI"],
    }
    needed = set(targets.get(paper_id, []))
    if not needed:
        return []

    by_key = {
        str(row.get("key") or "").strip(): row
        for row in baseline_rows
        if isinstance(row, dict) and str(row.get("key") or "").strip()
    }

    rows: List[Dict[str, Any]] = []
    for key in targets.get(paper_id, []):
        base = by_key.get(key, {})
        rows.append(
            {
                "paper_id": paper_id,
                "key": key,
                "baseline_junior_scores": {
                    "JuniorNano": _to_score(base.get("round-A_JuniorNano_evaluation")),
                    "JuniorMini": _to_score(base.get("round-A_JuniorMini_evaluation")),
                },
                "baseline_senior_score": _to_score(base.get("round-B_SeniorLead_evaluation")),
                "replay_no_marker_senior_score": _to_score(
                    (replay_no_marker.get(key) or {}).get("round-B_SeniorLead_evaluation")
                ),
                "replay_tuned_senior_score": _to_score(
                    (replay_tuned.get(key) or {}).get("round-B_SeniorLead_evaluation")
                ),
            }
        )
    return rows


def _paper_ids_from_args(arg_ids: List[str]) -> List[str]:
    if arg_ids:
        return arg_ids
    return ["2307.05527", "2409.13738", "2511.13936", "2601.19926"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay stage1 senior adjudication on frozen junior inputs.")
    parser.add_argument("--paper-id", action="append", default=[], help="Paper id (repeatable).")
    parser.add_argument("--senior-model", default="gpt-5-mini")
    parser.add_argument("--senior-reasoning-effort", default="medium")
    parser.add_argument("--max-concurrent-requests", type=int, default=50)
    parser.add_argument("--output-subdir", default="frozen_senior_replay")
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=Path("screening/results/frozen_senior_replay_summary.json"),
    )
    args = parser.parse_args()

    load_env_file()
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY 未設定，無法執行 senior replay。")

    paper_ids = _paper_ids_from_args(args.paper_id)

    aggregate_view1 = {
        "baseline_no_marker": [],
        "replay_stage1_senior_no_marker": [],
        "replay_stage1_senior_prompt_tuned": [],
    }
    aggregate_metrics = {
        "baseline_no_marker": {"tp": 0, "fp": 0, "tn": 0, "fn": 0},
        "replay_stage1_senior_no_marker": {"tp": 0, "fp": 0, "tn": 0, "fn": 0},
        "replay_stage1_senior_prompt_tuned": {"tp": 0, "fp": 0, "tn": 0, "fn": 0},
    }
    aggregate_spot_checks: List[Dict[str, Any]] = []

    per_paper_reports: Dict[str, Any] = {}

    for paper_id in paper_ids:
        result_dir = REPO_ROOT / "screening" / "results" / f"{paper_id}_full"
        baseline_path = result_dir / "latte_review_results.senior_no_marker.json"
        criteria_path = REPO_ROOT / "criteria_jsons" / f"{paper_id}.json"
        gold_path = REPO_ROOT / "refs" / paper_id / "metadata" / "title_abstracts_metadata-annotated.jsonl"
        output_dir = result_dir / args.output_subdir

        if not baseline_path.exists():
            raise FileNotFoundError(f"找不到 baseline 檔案：{baseline_path}")
        if not criteria_path.exists():
            raise FileNotFoundError(f"找不到 criteria 檔案：{criteria_path}")
        if not gold_path.exists():
            raise FileNotFoundError(f"找不到 gold metadata：{gold_path}")

        baseline_rows = _read_json(baseline_path)
        if not isinstance(baseline_rows, list):
            raise ValueError(f"baseline 檔案格式錯誤：{baseline_path}")

        criteria_payload = _load_criteria_payload(criteria_path)
        frozen_cases, sent_to_senior = _build_frozen_cases(baseline_rows)

        output_dir.mkdir(parents=True, exist_ok=True)
        frozen_input_path = output_dir / "frozen_stage1_senior_inputs.json"
        _write_json(frozen_input_path, frozen_cases)

        replay_no_marker = _run_senior_replay(
            frozen_cases,
            criteria_payload=criteria_payload,
            prompt_id="stage1_senior_no_marker",
            senior_model=args.senior_model,
            senior_reasoning_effort=args.senior_reasoning_effort,
            max_concurrent_requests=args.max_concurrent_requests,
        )
        replay_tuned = _run_senior_replay(
            frozen_cases,
            criteria_payload=criteria_payload,
            prompt_id="stage1_senior_prompt_tuned",
            senior_model=args.senior_model,
            senior_reasoning_effort=args.senior_reasoning_effort,
            max_concurrent_requests=args.max_concurrent_requests,
        )

        replay_no_marker_rows = [
            {
                "key": case["key"],
                "round-B_SeniorLead_reasoning": (replay_no_marker.get(case["key"]) or {}).get(
                    "round-B_SeniorLead_reasoning"
                ),
                "round-B_SeniorLead_evaluation": (replay_no_marker.get(case["key"]) or {}).get(
                    "round-B_SeniorLead_evaluation"
                ),
            }
            for case in frozen_cases
        ]
        replay_tuned_rows = [
            {
                "key": case["key"],
                "round-B_SeniorLead_reasoning": (replay_tuned.get(case["key"]) or {}).get(
                    "round-B_SeniorLead_reasoning"
                ),
                "round-B_SeniorLead_evaluation": (replay_tuned.get(case["key"]) or {}).get(
                    "round-B_SeniorLead_evaluation"
                ),
            }
            for case in frozen_cases
        ]

        replay_no_marker_output_path = output_dir / "senior_replay_outputs.stage1_senior_no_marker.json"
        replay_tuned_output_path = output_dir / "senior_replay_outputs.stage1_senior_prompt_tuned.json"
        _write_json(replay_no_marker_output_path, replay_no_marker_rows)
        _write_json(replay_tuned_output_path, replay_tuned_rows)

        reconstructed_no_marker = _reconstruct_stage1(baseline_rows, replay_no_marker, sent_to_senior)
        reconstructed_tuned = _reconstruct_stage1(baseline_rows, replay_tuned, sent_to_senior)

        reconstructed_no_marker_path = output_dir / "latte_review_results.reconstructed_replay_stage1_senior_no_marker.json"
        reconstructed_tuned_path = output_dir / "latte_review_results.reconstructed_replay_stage1_senior_prompt_tuned.json"
        _write_json(reconstructed_no_marker_path, reconstructed_no_marker)
        _write_json(reconstructed_tuned_path, reconstructed_tuned)

        gold = _load_gold_labels(gold_path)
        baseline_metrics = _compute_metrics(baseline_rows, gold)
        replay_no_marker_metrics = _compute_metrics(reconstructed_no_marker, gold)
        replay_tuned_metrics = _compute_metrics(reconstructed_tuned, gold)

        baseline_scores = [case.get("baseline_round-B_SeniorLead_evaluation") for case in frozen_cases]
        replay_no_marker_scores = [
            _to_score((replay_no_marker.get(case["key"]) or {}).get("round-B_SeniorLead_evaluation"))
            for case in frozen_cases
        ]
        replay_tuned_scores = [
            _to_score((replay_tuned.get(case["key"]) or {}).get("round-B_SeniorLead_evaluation"))
            for case in frozen_cases
        ]

        view1 = {
            "baseline_no_marker": _score_distribution(baseline_scores),
            "replay_stage1_senior_no_marker": _score_distribution(replay_no_marker_scores),
            "replay_stage1_senior_prompt_tuned": _score_distribution(replay_tuned_scores),
        }

        spot_checks = _spot_check_rows(
            paper_id=paper_id,
            baseline_rows=baseline_rows,
            replay_no_marker=replay_no_marker,
            replay_tuned=replay_tuned,
        )

        paper_report = {
            "paper_id": paper_id,
            "paths": {
                "baseline": str(baseline_path),
                "frozen_inputs": str(frozen_input_path),
                "replay_no_marker_outputs": str(replay_no_marker_output_path),
                "replay_tuned_outputs": str(replay_tuned_output_path),
                "reconstructed_no_marker": str(reconstructed_no_marker_path),
                "reconstructed_tuned": str(reconstructed_tuned_path),
                "gold": str(gold_path),
            },
            "counts": {
                "baseline_total": len(baseline_rows),
                "sent_to_senior": len(frozen_cases),
                "not_sent_to_senior": len(baseline_rows) - len(frozen_cases),
            },
            "view1_senior_subset_distribution": view1,
            "view2_stage1_metrics": {
                "baseline_no_marker": baseline_metrics,
                "replay_stage1_senior_no_marker": replay_no_marker_metrics,
                "replay_stage1_senior_prompt_tuned": replay_tuned_metrics,
            },
            "spot_checks": spot_checks,
        }
        _write_json(output_dir / "replay_summary.json", paper_report)
        per_paper_reports[paper_id] = paper_report

        aggregate_view1["baseline_no_marker"].extend(baseline_scores)
        aggregate_view1["replay_stage1_senior_no_marker"].extend(replay_no_marker_scores)
        aggregate_view1["replay_stage1_senior_prompt_tuned"].extend(replay_tuned_scores)

        for bucket, metrics in (
            ("baseline_no_marker", baseline_metrics),
            ("replay_stage1_senior_no_marker", replay_no_marker_metrics),
            ("replay_stage1_senior_prompt_tuned", replay_tuned_metrics),
        ):
            aggregate_metrics[bucket]["tp"] += int(metrics["tp"])
            aggregate_metrics[bucket]["fp"] += int(metrics["fp"])
            aggregate_metrics[bucket]["tn"] += int(metrics["tn"])
            aggregate_metrics[bucket]["fn"] += int(metrics["fn"])

        aggregate_spot_checks.extend(spot_checks)

    def _metrics_from_confusion(conf: Dict[str, int]) -> Dict[str, Any]:
        tp = conf["tp"]
        fp = conf["fp"]
        fn = conf["fn"]
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        out = dict(conf)
        out.update({"precision": precision, "recall": recall, "f1": f1})
        return out

    aggregate_report = {
        "paper_ids": paper_ids,
        "view1_senior_subset_distribution": {
            k: _score_distribution(v) for k, v in aggregate_view1.items()
        },
        "view2_stage1_metrics": {
            k: _metrics_from_confusion(v) for k, v in aggregate_metrics.items()
        },
        "spot_checks": aggregate_spot_checks,
    }

    summary = {
        "per_paper": per_paper_reports,
        "aggregate": aggregate_report,
    }

    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    args.summary_output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"summary_output": str(args.summary_output), "paper_count": len(paper_ids)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
