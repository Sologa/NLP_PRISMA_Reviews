from __future__ import annotations

import sys
import unittest
from pathlib import Path


BUNDLE_DIR = Path(__file__).resolve().parents[1]
TOOLS_DIR = BUNDLE_DIR / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import paper_faithful_lib as lib  # type: ignore  # noqa: E402


class PaperFaithfulThresholdTests(unittest.TestCase):
    def test_build_threshold_results_preserves_cutoff_excludes_and_top_k(self) -> None:
        ranked_rows = [
            {"key": "a", "title": "A", "score": 0.95, "gold_label": 1},
            {"key": "b", "title": "B", "score": 0.85, "gold_label": 0},
            {"key": "c", "title": "C", "score": 0.75, "gold_label": 1},
            {"key": "d", "title": "D", "score": 0.65, "gold_label": 0},
        ]
        cutoff_excluded_rows = [
            {"key": "x", "title": "X", "gold_label": 0},
            {"key": "y", "title": "Y", "gold_label": 0},
        ]

        payload = lib.build_threshold_results(
            ranked_rows=ranked_rows,
            cutoff_excluded_rows=cutoff_excluded_rows,
            k=2,
            strategy_id="soft_vote",
            threshold_id="current_authority_k",
        )

        include_keys = {row["key"] for row in payload["results"] if row["prediction"] == 1}
        exclude_keys = {row["key"] for row in payload["results"] if row["prediction"] == 0}

        self.assertEqual(include_keys, {"a", "b"})
        self.assertTrue({"x", "y", "c", "d"}.issubset(exclude_keys))
        self.assertEqual(len(payload["results"]), 6)
        self.assertEqual(payload["metrics"]["tp"], 1)
        self.assertEqual(payload["metrics"]["fp"], 1)
        self.assertEqual(payload["metrics"]["fn"], 1)
        self.assertEqual(payload["metrics"]["tn"], 3)


if __name__ == "__main__":
    unittest.main()
