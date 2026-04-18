from __future__ import annotations

import json
import unittest
from pathlib import Path


BUNDLE_DIR = Path(__file__).resolve().parents[1]


class StageConfigTests(unittest.TestCase):
    def test_stages_config_keeps_stage2_placeholder_disabled(self) -> None:
        stages_path = BUNDLE_DIR / "config" / "stages.json"
        payload = json.loads(stages_path.read_text(encoding="utf-8"))

        self.assertEqual(payload["enabled_stage_ids"], ["stage1_abstract"])
        self.assertIn("stage2_fulltext", payload["stages"])
        self.assertTrue(payload["stages"]["stage1_abstract"]["enabled"])
        self.assertFalse(payload["stages"]["stage2_fulltext"]["enabled"])
        self.assertEqual(payload["stages"]["stage2_fulltext"]["evidence_source"], "fulltext")


if __name__ == "__main__":
    unittest.main()
