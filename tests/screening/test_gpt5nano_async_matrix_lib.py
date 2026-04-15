from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "single_reviewer_async_experiments"
    / "gpt5nano_all4_route_matrix_2026-04-14"
    / "tools"
    / "experiment_lib.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("gpt5nano_async_matrix_lib", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RoutingRuleTests(unittest.TestCase):
    def test_should_route_when_manual_review_or_unclear_or_trap_hits(self) -> None:
        mod = _load_module()
        stage_review = {
            "manual_review_needed": False,
            "criterion_assessments": [
                {"criterion_id": "I1", "status": "YES", "supporting_quotes": [], "counter_quotes": [], "notes": ""},
                {"criterion_id": "I2", "status": "UNCLEAR", "supporting_quotes": [], "counter_quotes": [], "notes": ""},
            ],
            "decision_rationale": "The paper evaluates preference models in audio generation.",
            "routing_note": "",
        }
        profile = {
            "semantic_traps": ["preference only for evaluation"],
            "verification_focus": ["learning vs evaluation distinction"],
        }

        routed = mod.should_route_verification(
            paper_id="2511.13936",
            stage="stage2",
            review_output=stage_review,
            paper_profile=profile,
        )

        self.assertTrue(routed["should_route"])
        self.assertIn("criterion_unclear", routed["reasons"])

    def test_should_route_when_stage1_exclude_but_core_inclusion_not_all_no(self) -> None:
        mod = _load_module()
        stage_review = {
            "manual_review_needed": False,
            "criterion_assessments": [
                {"criterion_id": "I1_CORE_EXPLICIT", "status": "UNCLEAR", "supporting_quotes": [], "counter_quotes": [], "notes": ""},
                {"criterion_id": "E1_NOT_TARGET_FIT", "status": "YES", "supporting_quotes": [], "counter_quotes": [], "notes": ""},
            ],
            "decision_rationale": "The abstract focuses on process prediction rather than extraction.",
            "routing_note": "",
            "stage_score": 2,
        }
        profile = {"semantic_traps": ["process redesign", "process prediction"], "verification_focus": []}

        routed = mod.should_route_verification(
            paper_id="2409.13738",
            stage="stage1",
            review_output=stage_review,
            paper_profile=profile,
        )

        self.assertTrue(routed["should_route"])
        self.assertIn("stage1_exclude_not_all_core_no", routed["reasons"])


class SnippetSelectionTests(unittest.TestCase):
    def test_select_snippet_pack_prioritizes_method_eval_and_keywords(self) -> None:
        mod = _load_module()
        text = """# Introduction
This paper studies audio preference learning.

# Method
We train an audio model with pairwise preference ranking and reinforcement learning.

# Evaluation
Human A/B comparisons are used in the learning loop rather than evaluation only.

# Discussion
This section is less relevant.
"""
        review_output = {
            "criterion_assessments": [
                {"criterion_id": "I1_PREFERENCE_LEARNING_FIT", "status": "UNCLEAR", "supporting_quotes": [], "counter_quotes": [], "notes": ""}
            ]
        }
        profile = {
            "retrieval_priority_terms": ["pairwise preference", "reinforcement learning", "A/B"],
            "verification_focus": ["learning vs evaluation distinction"],
            "core_fit_terms": [],
            "non_target_terms": [],
            "semantic_traps": ["evaluation only"],
        }

        selected_text, meta = mod.select_snippet_pack(
            fulltext_text=text,
            prior_review_output=review_output,
            paper_profile=profile,
            max_chars=500,
        )

        self.assertIn("pairwise preference ranking", selected_text)
        self.assertIn("Human A/B comparisons", selected_text)
        self.assertGreaterEqual(meta["selected_chunk_count"], 2)


class MetricTests(unittest.TestCase):
    def test_compute_beta_metrics_returns_f1_f2_f3(self) -> None:
        mod = _load_module()
        metrics = mod.compute_metrics(tp=8, fp=2, tn=5, fn=1)

        self.assertAlmostEqual(0.8, metrics["precision"])
        self.assertAlmostEqual(8 / 9, metrics["recall"])
        self.assertIn("f1", metrics)
        self.assertIn("f2", metrics)
        self.assertIn("f3", metrics)


if __name__ == "__main__":
    unittest.main()
