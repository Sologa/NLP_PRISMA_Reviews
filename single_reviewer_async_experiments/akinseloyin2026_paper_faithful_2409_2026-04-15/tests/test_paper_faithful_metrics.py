from __future__ import annotations

import sys
import unittest
from pathlib import Path


BUNDLE_DIR = Path(__file__).resolve().parents[1]
TOOLS_DIR = BUNDLE_DIR / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import paper_faithful_lib as lib  # type: ignore  # noqa: E402


class PaperFaithfulMetricsTests(unittest.TestCase):
    def test_compute_ranking_metrics_prefers_front_loaded_relevant_documents(self) -> None:
        ranked_rows = [
            {"key": "a", "score": 0.95, "gold_label": 1},
            {"key": "b", "score": 0.90, "gold_label": 1},
            {"key": "c", "score": 0.80, "gold_label": 1},
            {"key": "d", "score": 0.30, "gold_label": 0},
            {"key": "e", "score": 0.10, "gold_label": 0},
        ]

        metrics = lib.compute_ranking_metrics(ranked_rows)

        self.assertAlmostEqual(metrics["map"], 1.0)
        self.assertAlmostEqual(metrics["wss95"], 0.35)
        self.assertEqual(metrics["last_relevant_rank"], 3)
        self.assertAlmostEqual(metrics["recall_at_percent"]["R@20%"], 1 / 3)

    def test_choose_oracle_threshold_k_maximizes_f1(self) -> None:
        ranked_rows = [
            {"key": "a", "score": 0.95, "gold_label": 1},
            {"key": "b", "score": 0.80, "gold_label": 0},
            {"key": "c", "score": 0.75, "gold_label": 1},
            {"key": "d", "score": 0.40, "gold_label": 0},
            {"key": "e", "score": 0.10, "gold_label": 0},
        ]

        oracle = lib.choose_oracle_threshold_k(ranked_rows)

        self.assertEqual(oracle["k"], 3)
        self.assertAlmostEqual(oracle["metrics"]["f1"], 0.8)


if __name__ == "__main__":
    unittest.main()
