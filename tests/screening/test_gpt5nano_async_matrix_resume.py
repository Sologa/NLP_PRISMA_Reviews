import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "single_reviewer_async_experiments"
    / "gpt5nano_all4_route_matrix_2026-04-14"
    / "tools"
    / "run_async_matrix.py"
)


def _load_runner_module():
    spec = importlib.util.spec_from_file_location("gpt5nano_async_runner", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ResumeBehaviorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = _load_runner_module()

    def test_selection_mode_uses_manifest_value(self) -> None:
        manifest = {"selection_mode": "smoke"}
        self.assertEqual(self.runner._selection_mode_for_resume(manifest, "20260414_full"), "smoke")

    def test_selection_mode_falls_back_to_run_id_hint(self) -> None:
        manifest = {}
        self.assertEqual(self.runner._selection_mode_for_resume(manifest, "20260414_smoke_matrix"), "smoke")
        self.assertEqual(self.runner._selection_mode_for_resume(manifest, "20260414_full_matrix"), "full")

    def test_key_map_for_resume_restores_smoke_allowlist(self) -> None:
        manifest = {
            "selection_mode": "smoke",
            "candidate_key_map": {
                "2307.05527": ["a", "b"],
                "2409.13738": ["c"],
            },
        }
        key_map = self.runner._key_map_for_resume(manifest, "20260414_smoke_matrix")
        self.assertEqual(key_map, {"2307.05527": {"a", "b"}, "2409.13738": {"c"}})

    def test_should_skip_completed_arm_only_during_resume(self) -> None:
        manifest = {"arm_status": {"direct_2stage_async": "completed"}}
        self.assertTrue(self.runner._should_skip_arm(manifest, "direct_2stage_async", resume_mode=True))
        self.assertFalse(self.runner._should_skip_arm(manifest, "direct_2stage_async", resume_mode=False))
        self.assertFalse(self.runner._should_skip_arm(manifest, "merged_ledger_2stage_async", resume_mode=True))


if __name__ == "__main__":
    unittest.main()
