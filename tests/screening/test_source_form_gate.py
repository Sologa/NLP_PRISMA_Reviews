from __future__ import annotations

import unittest

from pydantic import ValidationError

from scripts.screening.experiment_workflows.source_form_gate import (
    SourceFormClassificationOutput,
    SourceFormPolicy,
    attach_source_form_gate,
    build_source_form_record,
    determine_source_form_gate,
)


class SourceFormGateTests(unittest.TestCase):
    def _classification(self, publication_type: str, *, confidence: str = "high") -> SourceFormClassificationOutput:
        return SourceFormClassificationOutput.model_validate(
            {
                "publication_type": publication_type,
                "is_primary_empirical_or_original": publication_type == "primary_empirical_or_original",
                "confidence": confidence,
                "short_rationale": "The title explicitly identifies this publication form.",
                "evidence_fields_used": ["title"],
                "title_abstract_quotes": ["systematic review"],
            }
        )

    def test_classification_schema_rejects_extra_fields(self) -> None:
        payload = self._classification("secondary_review_or_survey").model_dump(mode="json")
        payload["gate_decision"] = "exclude_source_form"
        with self.assertRaises(ValidationError):
            SourceFormClassificationOutput.model_validate(payload)

    def test_disallow_secondary_excludes_clear_review_forms(self) -> None:
        policy = SourceFormPolicy(paper_id="x", allow_secondary_source_forms=False)
        gate = determine_source_form_gate(policy, self._classification("secondary_review_or_survey"))
        self.assertEqual(gate["gate_decision"], "exclude_source_form")
        self.assertFalse(gate["gate_pass"])

    def test_allow_secondary_prevents_secondary_hard_exclusion(self) -> None:
        policy = SourceFormPolicy(paper_id="x", allow_secondary_source_forms=True)
        gate = determine_source_form_gate(policy, self._classification("secondary_review_or_survey"))
        self.assertEqual(gate["gate_decision"], "pass")
        self.assertTrue(gate["gate_pass"])

    def test_unknown_or_low_confidence_passes_to_review(self) -> None:
        policy = SourceFormPolicy(paper_id="x", allow_secondary_source_forms=False)
        gate = determine_source_form_gate(policy, self._classification("unknown", confidence="low"))
        self.assertEqual(gate["gate_decision"], "manual_or_unclear_pass")
        self.assertTrue(gate["gate_pass"])

    def test_cutoff_row_keeps_cutoff_verdict_when_gate_attached(self) -> None:
        cutoff_row = {
            "key": "k1",
            "final_verdict": "exclude (cutoff_time_window)",
            "review_output": {"cutoff_filter": {"cutoff_pass": False}},
        }
        gate = {"gate_decision": "exclude_source_form", "gate_pass": False}
        attached = attach_source_form_gate(cutoff_row, gate)
        self.assertEqual(attached["final_verdict"], "exclude (cutoff_time_window)")
        self.assertEqual(attached["review_output"]["source_form_gate"], gate)

    def test_cache_key_changes_when_inputs_change(self) -> None:
        policy = SourceFormPolicy(paper_id="x", allow_secondary_source_forms=False)
        record = {"key": "k1", "title": "A systematic review", "abstract": "review"}
        criteria = {"paper_id": "x", "criteria": []}
        classification = self._classification("secondary_review_or_survey")
        base = build_source_form_record(
            paper_id="x",
            record=record,
            classification=classification,
            policy=policy,
            stage1_criteria=criteria,
            model="gpt-5-nano",
            reasoning_effort="high",
        )
        changed_metadata = build_source_form_record(
            paper_id="x",
            record={**record, "abstract": "changed"},
            classification=classification,
            policy=policy,
            stage1_criteria=criteria,
            model="gpt-5-nano",
            reasoning_effort="high",
        )
        changed_policy = build_source_form_record(
            paper_id="x",
            record=record,
            classification=classification,
            policy=SourceFormPolicy(paper_id="x", allow_secondary_source_forms=True),
            stage1_criteria=criteria,
            model="gpt-5-nano",
            reasoning_effort="high",
        )
        changed_model = build_source_form_record(
            paper_id="x",
            record=record,
            classification=classification,
            policy=policy,
            stage1_criteria=criteria,
            model="gpt-5-mini",
            reasoning_effort="high",
        )
        changed_effort = build_source_form_record(
            paper_id="x",
            record=record,
            classification=classification,
            policy=policy,
            stage1_criteria=criteria,
            model="gpt-5-nano",
            reasoning_effort="medium",
        )
        observed = {base.cache_key, changed_metadata.cache_key, changed_policy.cache_key, changed_model.cache_key, changed_effort.cache_key}
        self.assertEqual(len(observed), 5)


if __name__ == "__main__":
    unittest.main()
