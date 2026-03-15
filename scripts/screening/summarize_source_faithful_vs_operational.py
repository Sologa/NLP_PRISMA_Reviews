#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Dict, List, Optional, Tuple


PAPERS = ("2511.13936", "2409.13738")
VARIANTS = ("operational", "source_faithful")

SPOT_CHECK_KEYS = {
    "2511.13936": [
        "lotfian2016retrieving",
        "han2020ordinal",
        "parthasarathy2018preference",
        "parthasarathy2016using",
        "chumbalov2020scalable",
    ],
    "2409.13738": [
        "etikala2021extracting",
        "honkisz2018concept",
        "goncalves2011let",
        "kourani_process_modelling_with_llm",
        "grohs2023large",
        "bellan2020qualitative",
        "bellan2021process",
        "lopez2021challenges",
    ],
}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _find_key(item: Dict[str, Any]) -> Optional[str]:
    key = item.get("key")
    if key is not None:
        text = str(key).strip()
        if text:
            return text
    metadata = item.get("metadata")
    if isinstance(metadata, dict):
        key = metadata.get("key")
        if key is not None:
            text = str(key).strip()
            if text:
                return text
    return None


def _to_score(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, (int, float)) and value == int(value):
        return int(value)
    try:
        return int(str(value).strip())
    except Exception:
        return None


def _verdict_label(value: Any) -> str:
    verdict = str(value or "").strip().lower()
    if not verdict:
        return "unknown"
    m = re.match(r"^\s*([a-z]+)", verdict)
    if not m:
        return "unknown"
    label = m.group(1)
    return label if label in {"include", "maybe", "exclude", "discard"} else "unknown"


def _predict_row_positive(row: Dict[str, Any], positive_mode: str = "include_or_maybe") -> int:
    label = _verdict_label(row.get("final_verdict"))
    if label == "include":
        return 1
    if label == "exclude":
        return 0
    if label == "maybe":
        return 1 if positive_mode in {"include_or_maybe", "maybe_only"} else 0
    senior_eval = _to_score(row.get("round-B_SeniorLead_evaluation"))
    if senior_eval is not None:
        if senior_eval >= 4:
            return 1
        if senior_eval <= 2:
            return 0
    nano_eval = _to_score(row.get("round-A_JuniorNano_evaluation"))
    if nano_eval is not None:
        if nano_eval >= 4:
            return 1
        if nano_eval <= 2:
            return 0
    return 0


def _index_rows_by_key(rows: List[Dict[str, Any]]) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    keyed: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []
    for row in rows:
        key = _find_key(row)
        if not key:
            continue
        if key not in keyed:
            keyed[key] = row
            order.append(key)
    return keyed, order


def _combined_source_rows(
    base_rows: List[Dict[str, Any]],
    fulltext_rows: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    base_map, base_order = _index_rows_by_key(base_rows)
    full_map, _ = _index_rows_by_key(fulltext_rows)
    out: Dict[str, Dict[str, Any]] = {}
    for key in base_order:
        out[key] = full_map[key] if key in full_map else base_map[key]
    for key, row in full_map.items():
        if key not in out:
            out[key] = row
    return out


def _metric_stats(run_metrics: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    keys = ("precision", "recall", "f1", "tp", "fp", "tn", "fn")
    out: Dict[str, Dict[str, float]] = {}
    for key in keys:
        vals = [float(m[key]) for m in run_metrics if key in m and m[key] is not None]
        if not vals:
            out[key] = {"mean": 0.0, "std": 0.0}
            continue
        out[key] = {"mean": mean(vals), "std": pstdev(vals) if len(vals) > 1 else 0.0}
    return out


def _binary_stability(pred_maps: List[Dict[str, int]]) -> Dict[str, Any]:
    all_keys = set()
    for pred in pred_maps:
        all_keys.update(pred.keys())
    unstable: List[Dict[str, Any]] = []
    for key in sorted(all_keys):
        values = [pred.get(key) for pred in pred_maps]
        present = [v for v in values if v is not None]
        if len(set(present)) > 1:
            unstable.append({"key": key, "predictions": values})
    return {
        "total_keys": len(all_keys),
        "unstable_count": len(unstable),
        "unstable_keys": unstable,
    }


def _extract_reasoning_text(row: Optional[Dict[str, Any]], field: str) -> Optional[str]:
    if not row:
        return None
    payload = row.get(field)
    if isinstance(payload, dict):
        reasoning = payload.get("reasoning")
        if reasoning is not None:
            text = str(reasoning).strip()
            if text:
                return text
    return None


def _spot_case_summary(run_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    stage1_verdicts = [str(r.get("stage1_final_verdict") or "") for r in run_rows]
    combined_verdicts = [str(r.get("combined_final_verdict") or "") for r in run_rows]
    stage1_pos = [int(r.get("stage1_positive", 0)) for r in run_rows]
    combined_pos = [int(r.get("combined_positive", 0)) for r in run_rows]
    return {
        "runs": run_rows,
        "stage1_verdicts": stage1_verdicts,
        "combined_verdicts": combined_verdicts,
        "stage1_positive_rate": (sum(stage1_pos) / len(stage1_pos)) if stage1_pos else 0.0,
        "combined_positive_rate": (sum(combined_pos) / len(combined_pos)) if combined_pos else 0.0,
        "stage1_unstable": len(set(stage1_pos)) > 1 if stage1_pos else False,
        "combined_unstable": len(set(combined_pos)) > 1 if combined_pos else False,
    }


def _run_tag_from_dir(path: Path) -> str:
    return path.name


def _collect_variant(
    paper_id: str,
    variant: str,
    variant_dir: Path,
) -> Dict[str, Any]:
    if not variant_dir.exists():
        return {
            "paper_id": paper_id,
            "variant": variant,
            "runs": [],
            "stage1": {"run_metrics": [], "stats": _metric_stats([]), "stability": _binary_stability([])},
            "combined": {"run_metrics": [], "stats": _metric_stats([]), "stability": _binary_stability([])},
            "spot_checks": {},
        }

    run_dirs = sorted(p for p in variant_dir.iterdir() if p.is_dir() and p.name.startswith("run"))
    stage1_metrics: List[Dict[str, Any]] = []
    combined_metrics: List[Dict[str, Any]] = []
    stage1_pred_maps: List[Dict[str, int]] = []
    combined_pred_maps: List[Dict[str, int]] = []
    spot_per_key: Dict[str, List[Dict[str, Any]]] = {k: [] for k in SPOT_CHECK_KEYS.get(paper_id, [])}
    runs: List[Dict[str, Any]] = []

    for run_dir in run_dirs:
        run_tag = _run_tag_from_dir(run_dir)
        stage1_f1_path = run_dir / "stage1_f1.json"
        combined_f1_path = run_dir / "combined_f1.json"
        stage1_results_path = run_dir / "latte_review_results.json"
        fulltext_results_path = run_dir / "latte_fulltext_review_results.json"
        if not (stage1_f1_path.exists() and combined_f1_path.exists() and stage1_results_path.exists() and fulltext_results_path.exists()):
            continue

        stage1_f1 = _load_json(stage1_f1_path)
        combined_f1 = _load_json(combined_f1_path)
        stage1_metric = dict(stage1_f1.get("metrics") or {})
        combined_metric = dict(combined_f1.get("metrics") or {})
        stage1_metrics.append(stage1_metric)
        combined_metrics.append(combined_metric)

        stage1_rows = [row for row in _load_json(stage1_results_path) if isinstance(row, dict)]
        fulltext_rows = [row for row in _load_json(fulltext_results_path) if isinstance(row, dict)]
        stage1_map, _ = _index_rows_by_key(stage1_rows)
        combined_source_map = _combined_source_rows(stage1_rows, fulltext_rows)

        stage1_pred = {k: _predict_row_positive(v) for k, v in stage1_map.items()}
        combined_pred = {k: _predict_row_positive(v) for k, v in combined_source_map.items()}
        stage1_pred_maps.append(stage1_pred)
        combined_pred_maps.append(combined_pred)

        runs.append(
            {
                "run_tag": run_tag,
                "run_dir": str(run_dir),
                "stage1_metrics": stage1_metric,
                "combined_metrics": combined_metric,
            }
        )

        for key in spot_per_key:
            stage1_row = stage1_map.get(key)
            combined_row = combined_source_map.get(key)
            spot_per_key[key].append(
                {
                    "run_tag": run_tag,
                    "stage1_final_verdict": stage1_row.get("final_verdict") if stage1_row else None,
                    "stage1_positive": _predict_row_positive(stage1_row) if stage1_row else None,
                    "stage1_junior_nano_eval": stage1_row.get("round-A_JuniorNano_evaluation") if stage1_row else None,
                    "stage1_junior_mini_eval": stage1_row.get("round-A_JuniorMini_evaluation") if stage1_row else None,
                    "stage1_senior_eval": stage1_row.get("round-B_SeniorLead_evaluation") if stage1_row else None,
                    "stage1_senior_reasoning": _extract_reasoning_text(stage1_row, "round-B_SeniorLead_output"),
                    "stage1_junior_mini_reasoning": _extract_reasoning_text(stage1_row, "round-A_JuniorMini_output"),
                    "combined_final_verdict": combined_row.get("final_verdict") if combined_row else None,
                    "combined_positive": _predict_row_positive(combined_row) if combined_row else None,
                    "combined_base_final_verdict": combined_row.get("base_final_verdict") if combined_row else None,
                    "combined_review_state": combined_row.get("review_state") if combined_row else None,
                    "combined_junior_nano_eval": combined_row.get("round-A_JuniorNano_evaluation") if combined_row else None,
                    "combined_junior_mini_eval": combined_row.get("round-A_JuniorMini_evaluation") if combined_row else None,
                    "combined_senior_eval": combined_row.get("round-B_SeniorLead_evaluation") if combined_row else None,
                    "combined_senior_reasoning": _extract_reasoning_text(combined_row, "round-B_SeniorLead_output"),
                    "combined_junior_mini_reasoning": _extract_reasoning_text(combined_row, "round-A_JuniorMini_output"),
                }
            )

    spot_summary = {key: _spot_case_summary(rows) for key, rows in spot_per_key.items()}
    return {
        "paper_id": paper_id,
        "variant": variant,
        "runs": runs,
        "stage1": {
            "run_metrics": stage1_metrics,
            "stats": _metric_stats(stage1_metrics),
            "stability": _binary_stability(stage1_pred_maps),
        },
        "combined": {
            "run_metrics": combined_metrics,
            "stats": _metric_stats(combined_metrics),
            "stability": _binary_stability(combined_pred_maps),
        },
        "spot_checks": spot_summary,
    }


def build_summary(results_root: Path) -> Dict[str, Any]:
    papers_out: Dict[str, Any] = {}
    for paper_id in PAPERS:
        paper_dir = results_root / paper_id
        variants_out: Dict[str, Any] = {}
        for variant in VARIANTS:
            variants_out[variant] = _collect_variant(paper_id, variant, paper_dir / variant)
        papers_out[paper_id] = variants_out
    return {
        "results_root": str(results_root),
        "papers": papers_out,
        "spot_check_keys": SPOT_CHECK_KEYS,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize source-faithful vs operational benchmark results.")
    parser.add_argument(
        "--results-root",
        type=Path,
        default=Path("screening/results/source_faithful_vs_operational_2409_2511"),
        help="Root directory containing benchmark runs.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help="Output summary JSON path (default: <results-root>/summary.json).",
    )
    args = parser.parse_args()

    results_root = args.results_root.resolve()
    if not results_root.exists():
        raise SystemExit(f"Missing results root: {results_root}")

    output_json = args.output_json.resolve() if args.output_json else (results_root / "summary.json").resolve()
    summary = build_summary(results_root)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[done] summary={output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
