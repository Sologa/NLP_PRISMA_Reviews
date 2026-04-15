from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "single_reviewer_async_experiments"
    / "criterion_ledger_current_kernel_2409_2026-04-15"
    / "tools"
    / "ledger_kernel_lib.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("criterion_ledger_current_kernel_2409_lib", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ModelConfigTests(unittest.TestCase):
    def test_role_model_settings_use_expected_models(self) -> None:
        mod = _load_module()

        self.assertEqual(mod.role_model_settings("junior_nano")["model"], "gpt-5-nano")
        self.assertEqual(mod.role_model_settings("junior_mini")["model"], "gpt-4.1-mini")
        self.assertEqual(mod.role_model_settings("senior")["model"], "gpt-5-mini")
        self.assertEqual(mod.role_model_settings("junior_nano")["reasoning_effort"], "medium")
        self.assertIsNone(mod.role_model_settings("junior_mini")["reasoning_effort"])
        self.assertEqual(mod.role_model_settings("senior")["reasoning_effort"], "medium")


class AdjudicationRuleTests(unittest.TestCase):
    def test_stage1_auto_passes_include_only_when_both_include_and_clear(self) -> None:
        mod = _load_module()
        junior_a = {
            "stage_score": 4,
            "criterion_assessments": [
                {"criterion_id": "I1", "status": "YES"},
                {"criterion_id": "I2", "status": "YES"},
                {"criterion_id": "E1", "status": "NO"},
            ],
        }
        junior_b = {
            "stage_score": 5,
            "criterion_assessments": [
                {"criterion_id": "I1", "status": "YES"},
                {"criterion_id": "I2", "status": "YES"},
                {"criterion_id": "E1", "status": "NO"},
            ],
        }

        adjudication = mod.build_adjudication_decision(stage="stage1", junior_nano=junior_a, junior_mini=junior_b)

        self.assertFalse(adjudication["route_to_senior"])
        self.assertEqual(adjudication["auto_final_decision"], "include")

    def test_stage1_routes_when_both_exclude_but_inclusion_not_all_no(self) -> None:
        mod = _load_module()
        junior_a = {
            "stage_score": 2,
            "criterion_assessments": [
                {"criterion_id": "I1", "status": "UNCLEAR"},
                {"criterion_id": "E1", "status": "YES"},
            ],
        }
        junior_b = {
            "stage_score": 1,
            "criterion_assessments": [
                {"criterion_id": "I1", "status": "NO"},
                {"criterion_id": "E1", "status": "YES"},
            ],
        }

        adjudication = mod.build_adjudication_decision(stage="stage1", junior_nano=junior_a, junior_mini=junior_b)

        self.assertTrue(adjudication["route_to_senior"])
        self.assertIn("stage1_exclude_with_positive_or_unclear_inclusion", adjudication["reasons"])

    def test_stage2_routes_even_when_decisions_match_but_any_criterion_unclear(self) -> None:
        mod = _load_module()
        junior_a = {
            "stage_score": 4,
            "criterion_assessments": [
                {"criterion_id": "I1", "status": "YES"},
                {"criterion_id": "I2", "status": "UNCLEAR"},
                {"criterion_id": "E1", "status": "NO"},
            ],
        }
        junior_b = {
            "stage_score": 4,
            "criterion_assessments": [
                {"criterion_id": "I1", "status": "YES"},
                {"criterion_id": "I2", "status": "UNCLEAR"},
                {"criterion_id": "E1", "status": "NO"},
            ],
        }

        adjudication = mod.build_adjudication_decision(stage="stage2", junior_nano=junior_a, junior_mini=junior_b)

        self.assertTrue(adjudication["route_to_senior"])
        self.assertIn("criterion_unclear", adjudication["reasons"])

    def test_effective_review_prefers_senior_when_present(self) -> None:
        mod = _load_module()
        junior_a = {"stage_score": 2}
        junior_b = {"stage_score": 2}
        senior = {"stage_score": 4}
        adjudication = {
            "route_to_senior": True,
            "auto_final_decision": None,
            "final_source": "senior",
        }

        effective = mod.effective_stage_review(
            junior_nano=junior_a,
            junior_mini=junior_b,
            senior=senior,
            adjudication=adjudication,
        )

        self.assertEqual(effective["stage_score"], 4)


if __name__ == "__main__":
    unittest.main()
