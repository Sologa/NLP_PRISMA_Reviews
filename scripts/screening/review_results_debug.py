#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RESULTS_PATH = REPO_ROOT / "screening" / "results" / "cads_smoke5" / "latte_review_results.json"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _to_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize and debug screening review results.")
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS_PATH, help="Path to latte_review_results.json")
    parser.add_argument("--compare", type=Path, default=None, help="Optional second results JSON to compare against.")
    args = parser.parse_args()

    results_path = args.results.resolve()
    if not results_path.exists():
        raise SystemExit(f"Missing results file: {results_path}")

    rows = _load_json(results_path)
    if not isinstance(rows, list):
        raise SystemExit(f"Expected list JSON in {results_path}")

    verdict_counter = Counter(str(row.get("final_verdict")) for row in rows)

    disagreements: list[dict[str, Any]] = []
    senior_used: list[dict[str, Any]] = []

    for row in rows:
        metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
        key = metadata.get("key")
        title = row.get("title") or metadata.get("title")
        nano = _to_int(row.get("round-A_JuniorNano_evaluation"))
        mini = _to_int(row.get("round-A_JuniorMini_evaluation"))
        senior = _to_int(row.get("round-B_SeniorLead_evaluation"))

        if nano is not None and mini is not None and nano != mini:
            disagreements.append(
                {
                    "key": key,
                    "title": title,
                    "nano": nano,
                    "mini": mini,
                    "senior": senior,
                    "final_verdict": row.get("final_verdict"),
                }
            )
        if senior is not None:
            senior_used.append(
                {
                    "key": key,
                    "title": title,
                    "senior": senior,
                    "final_verdict": row.get("final_verdict"),
                }
            )

    print(f"results_path={results_path}")
    print(f"total={len(rows)}")
    print("verdict_counts=")
    for verdict, count in verdict_counter.items():
        print(f"  - {verdict}: {count}")

    print(f"disagreements={len(disagreements)}")
    for item in disagreements:
        print(
            f"  - {item['key']} | nano={item['nano']} mini={item['mini']} "
            f"senior={item['senior']} | {item['final_verdict']}"
        )

    print(f"senior_used={len(senior_used)}")
    for item in senior_used:
        print(f"  - {item['key']} | senior={item['senior']} | {item['final_verdict']}")

    if args.compare is not None:
        compare_path = args.compare.resolve()
        if not compare_path.exists():
            raise SystemExit(f"Missing compare file: {compare_path}")
        other_rows = _load_json(compare_path)
        if not isinstance(other_rows, list):
            raise SystemExit(f"Expected list JSON in {compare_path}")

        def _index_by_key(payload: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
            indexed: dict[str, dict[str, Any]] = {}
            for row in payload:
                metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
                key = str(metadata.get("key") or "").strip()
                if key:
                    indexed[key] = row
            return indexed

        now_index = _index_by_key(rows)
        old_index = _index_by_key(other_rows)
        changed: list[str] = []
        for key in sorted(set(now_index.keys()) & set(old_index.keys())):
            now_verdict = str(now_index[key].get("final_verdict"))
            old_verdict = str(old_index[key].get("final_verdict"))
            if now_verdict != old_verdict:
                changed.append(f"{key}: {old_verdict} -> {now_verdict}")

        print(f"compare_path={compare_path}")
        print(f"verdict_changed={len(changed)}")
        for line in changed:
            print(f"  - {line}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
