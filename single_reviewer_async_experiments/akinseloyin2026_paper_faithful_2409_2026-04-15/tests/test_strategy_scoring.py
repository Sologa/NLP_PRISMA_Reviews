from __future__ import annotations

import sys
import unittest
from pathlib import Path


BUNDLE_DIR = Path(__file__).resolve().parents[1]
TOOLS_DIR = BUNDLE_DIR / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import paper_faithful_lib as lib  # type: ignore  # noqa: E402


def _answer(label: str, confidence: float = 0.8) -> dict[str, object]:
    return {
        "answer_label": label,
        "confidence": confidence,
    }


class StrategyScoringTests(unittest.TestCase):
    def test_soft_vote_uses_question_level_majority_labels(self) -> None:
        review_rows = [
            {
                "candidate_key": "doc1",
                "reviewer_role": "qa_gpt54nano",
                "answers": [_answer("positive"), _answer("neutral")],
            },
            {
                "candidate_key": "doc1",
                "reviewer_role": "qa_gpt41mini",
                "answers": [_answer("positive"), _answer("negative")],
            },
            {
                "candidate_key": "doc1",
                "reviewer_role": "qa_gpt5mini",
                "answers": [_answer("negative"), _answer("negative")],
            },
        ]

        score = lib.compute_soft_vote_score(review_rows)

        self.assertAlmostEqual(score, 0.5)

    def test_mad_raw_uses_mean_of_round2_answer_scores(self) -> None:
        review_rows = [
            {"candidate_key": "doc1", "answers": [_answer("positive"), _answer("neutral")]},
            {"candidate_key": "doc1", "answers": [_answer("positive"), _answer("positive")]},
            {"candidate_key": "doc1", "answers": [_answer("negative"), _answer("neutral")]},
        ]

        score = lib.compute_mad_raw_score(review_rows)

        self.assertAlmostEqual(score, (1.0 + 0.5 + 1.0 + 1.0 + 0.0 + 0.5) / 6.0)

    def test_adj_rank_uses_judge_ratings_to_weight_primary_answers(self) -> None:
        primary_rows = {
            "qa_gpt54nano": {"answers": [_answer("positive")]},
            "qa_gpt41mini": {"answers": [_answer("negative")]},
            "qa_gpt5mini": {"answers": [_answer("neutral")]},
        }
        judge_row = {
            "answers": [
                {
                    "answer_label": "positive",
                    "reviewer_ratings": [
                        {"reviewer_role": "qa_gpt54nano", "rating": 0.9},
                        {"reviewer_role": "qa_gpt41mini", "rating": 0.1},
                        {"reviewer_role": "qa_gpt5mini", "rating": 0.5}
                    ],
                }
            ]
        }

        score = lib.compute_adj_rank_score(primary_rows=primary_rows, judge_row=judge_row)

        expected = (1.0 * 0.9 + 0.0 * 0.1 + 0.5 * 0.5) / (0.9 + 0.1 + 0.5)
        self.assertAlmostEqual(score, expected)


if __name__ == "__main__":
    unittest.main()
