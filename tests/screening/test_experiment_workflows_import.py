from __future__ import annotations

import importlib
import unittest


class ExperimentWorkflowsImportTests(unittest.TestCase):
    def test_package_import_succeeds_from_repo_root(self) -> None:
        module = importlib.import_module("scripts.screening.experiment_workflows")
        self.assertTrue(hasattr(module, "build_direct_stage_prompt_context"))
        self.assertTrue(hasattr(module, "build_stage_prompt_context"))


if __name__ == "__main__":
    unittest.main()
