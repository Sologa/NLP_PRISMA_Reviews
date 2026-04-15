from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


BUNDLE_DIR = (
    Path(__file__).resolve().parents[2]
    / "single_reviewer_async_experiments"
    / "criterion_ledger_current_kernel_2511_2026-04-15"
)
MODULE_PATH = BUNDLE_DIR / "tools" / "ledger_kernel_lib.py"
CONFIG_PATH = BUNDLE_DIR / "config" / "experiment.json"


def _load_module():
    spec = importlib.util.spec_from_file_location("criterion_ledger_current_kernel_2511_lib", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class BundleWiringTests(unittest.TestCase):
    def test_config_points_to_2511_assets_and_metrics(self) -> None:
        config = json.loads(CONFIG_PATH.read_text())

        self.assertEqual(config["paper_id"], "2511.13936")
        self.assertEqual(config["workflow_arm"], "criterion_ledger_current_kernel")

        repo_root = BUNDLE_DIR.parents[1]
        for rel_path in (
            config["current_authority_stage1_path"],
            config["current_authority_combined_path"],
            config["reference_single_reviewer_stage1_path"],
            config["reference_single_reviewer_combined_path"],
            "criteria_stage1/2511.13936.json",
            "criteria_stage2/2511.13936.json",
            "cutoff_jsons/2511.13936.json",
            "refs/2511.13936/metadata/title_abstracts_metadata.jsonl",
            "refs/2511.13936/metadata/title_abstracts_metadata-annotated.jsonl",
        ):
            self.assertTrue((repo_root / rel_path).exists(), rel_path)

        self.assertTrue((BUNDLE_DIR / "assets" / "merged" / "2511.13936.stage1.json").exists())
        self.assertTrue((BUNDLE_DIR / "assets" / "merged" / "2511.13936.stage2.json").exists())

    def test_role_model_settings_match_current_kernel_plan(self) -> None:
        mod = _load_module()

        self.assertEqual(mod.role_model_settings("junior_nano")["model"], "gpt-5-nano")
        self.assertEqual(mod.role_model_settings("junior_mini")["model"], "gpt-4.1-mini")
        self.assertEqual(mod.role_model_settings("senior")["model"], "gpt-5-mini")
        self.assertEqual(mod.role_model_settings("junior_nano")["reasoning_effort"], "medium")
        self.assertIsNone(mod.role_model_settings("junior_mini")["reasoning_effort"])
        self.assertEqual(mod.role_model_settings("senior")["reasoning_effort"], "medium")


if __name__ == "__main__":
    unittest.main()
