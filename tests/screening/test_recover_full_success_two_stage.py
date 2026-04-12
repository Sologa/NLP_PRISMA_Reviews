from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "single_reviewer_batch_experiments"
    / "single_reviewer_official_batch_2stage_direct_review_2409_2511_2026-04-06"
    / "tools"
    / "recover_full_success_two_stage.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("recover_full_success_two_stage", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MergeStageRowsTests(unittest.TestCase):
    def test_merge_stage_rows_keeps_first_success_per_candidate_key(self) -> None:
        mod = _load_module()
        merged, source_runs = mod.merge_stage_rows(
            [
                (
                    "run_a",
                    [
                        {"candidate_key": "a", "stage_score": 1},
                        {"candidate_key": "b", "stage_score": 4},
                    ],
                ),
                (
                    "run_b",
                    [
                        {"candidate_key": "b", "stage_score": 5},
                        {"candidate_key": "c", "stage_score": 3},
                    ],
                ),
            ]
        )

        self.assertEqual(["a", "b", "c"], [row["candidate_key"] for row in merged])
        self.assertEqual({"a": "run_a", "b": "run_a", "c": "run_b"}, source_runs)


class AggregateAttemptUsageTests(unittest.TestCase):
    def test_aggregate_attempt_usage_sums_usage_and_cost(self) -> None:
        mod = _load_module()
        summary = mod.aggregate_attempt_usage(
            [
                {
                    "phase": "stage1_review",
                    "usage": {
                        "input_tokens": 100,
                        "cached_input_tokens": 10,
                        "output_tokens": 20,
                        "reasoning_tokens": 12,
                        "total_tokens": 120,
                    },
                    "cost_usd": 1.25,
                },
                {
                    "phase": "stage2_review",
                    "usage": {
                        "input_tokens": 50,
                        "cached_input_tokens": 0,
                        "output_tokens": 10,
                        "reasoning_tokens": 4,
                        "total_tokens": 60,
                    },
                    "cost_usd": 0.75,
                },
            ]
        )

        self.assertEqual(150, summary["input_tokens"])
        self.assertEqual(10, summary["cached_input_tokens"])
        self.assertEqual(30, summary["output_tokens"])
        self.assertEqual(16, summary["reasoning_tokens"])
        self.assertEqual(180, summary["total_tokens"])
        self.assertEqual(2.0, summary["cost_usd"])


class SummarizeErrorMessagesTests(unittest.TestCase):
    def test_summarize_error_messages_counts_unique_messages(self) -> None:
        mod = _load_module()
        summary = mod.summarize_error_messages(
            [
                {"response": {"body": {"error": {"message": "The server had an error while processing your request. Sorry about that!"}}}},
                {"response": {"body": {"error": {"message": "The server had an error while processing your request. Sorry about that!"}}}},
                {"response": {"body": {"error": {"message": "Unsupported value"}}}},
            ]
        )

        self.assertEqual(
            [
                ("The server had an error while processing your request. Sorry about that!", 2),
                ("Unsupported value", 1),
            ],
            summary,
        )


if __name__ == "__main__":
    unittest.main()
