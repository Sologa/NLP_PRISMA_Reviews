from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.screening.experiment_workflows import (
    build_fulltext_resolution_audit,
    load_artifact_gate_result,
)
from scripts.screening.metadata_gate import evaluate_fulltext_gate


class ArtifactGateTests(unittest.TestCase):
    def test_explicit_false_flag_excludes_record(self) -> None:
        records = [
            {
                "key": "portal_page",
                "title": "Portal Page",
                "artifact_gate_pass": False,
                "artifact_gate_reason": "non_scholarly_webpage",
            },
            {
                "key": "real_paper",
                "title": "Real Paper",
            },
        ]

        result = load_artifact_gate_result(records=records)

        self.assertEqual([row["key"] for row in result["kept_records"]], ["real_paper"])
        self.assertEqual([row["key"] for row in result["excluded_records"]], ["portal_page"])
        self.assertFalse(result["decisions_by_key"]["portal_page"]["gate_pass"])
        self.assertEqual(
            result["decisions_by_key"]["portal_page"]["gate_reason"],
            "non_scholarly_webpage",
        )
        self.assertEqual(result["audit_payload"]["artifact_excluded_count"], 1)


class FulltextGateTests(unittest.TestCase):
    def test_zero_byte_fulltext_fails_resolution_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            fulltext_root = repo_root / "refs" / "2409.13738" / "mds"
            fulltext_root.mkdir(parents=True, exist_ok=True)
            (fulltext_root / "empty_record.md").write_text("", encoding="utf-8")

            resolution_by_key, audit = build_fulltext_resolution_audit(
                paper_id="2409.13738",
                records=[{"key": "empty_record", "title": "Empty Record"}],
                fulltext_root=fulltext_root,
                repo_root=repo_root,
            )

        resolution = resolution_by_key["empty_record"]
        self.assertEqual(resolution["resolution_status"], "exact")
        self.assertFalse(resolution["fulltext_gate_pass"])
        self.assertEqual(resolution["fulltext_gate_reason"], "zero_byte_md")
        self.assertEqual(audit["fulltext_gate_failed_count"], 1)

    def test_metadata_flag_false_fails_even_with_nonempty_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            fulltext_root = repo_root / "refs" / "2511.13936" / "mds"
            fulltext_root.mkdir(parents=True, exist_ok=True)
            path = fulltext_root / "gated_record.md"
            path.write_text("real content", encoding="utf-8")

            decision = evaluate_fulltext_gate(
                {
                    "key": "gated_record",
                    "fulltext_gate_pass": False,
                    "fulltext_gate_reason": "wrong_content",
                },
                {
                    "resolution_status": "exact",
                    "resolved_path": str(path.relative_to(repo_root)),
                    "exact_candidate_path": str(path.relative_to(repo_root)),
                },
                repo_root=repo_root,
            )

        self.assertFalse(decision["gate_pass"])
        self.assertEqual(decision["gate_reason"], "wrong_content")


if __name__ == "__main__":
    unittest.main()
