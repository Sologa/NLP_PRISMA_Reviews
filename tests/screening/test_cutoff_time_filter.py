from __future__ import annotations

import unittest
from datetime import date

from scripts.screening.cutoff_time_filter import TimePolicy, _parse_candidate_date, evaluate_record


class ParseCandidateDateTests(unittest.TestCase):
    def test_existing_supported_formats_still_parse(self) -> None:
        cases = {
            "2024-02-07": date(2024, 2, 7),
            "2024/02/07": date(2024, 2, 7),
            "March 17, 2024": date(2024, 3, 17),
            "Mar 17, 2024": date(2024, 3, 17),
            "2024": date(2024, 1, 1),
            "2024-02-07T03:04:05": date(2024, 2, 7),
            "2024-02-07T03:04:05Z": date(2024, 2, 7),
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(_parse_candidate_date(raw), expected)

    def test_year_month_real_audit_examples_parse_to_first_of_month(self) -> None:
        cases = {
            "2020-12": date(2020, 12, 1),
            "2018-10": date(2018, 10, 1),
            "2025-05": date(2025, 5, 1),
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(_parse_candidate_date(raw), expected)

    def test_unsupported_formats_remain_none(self) -> None:
        for raw in ("March 2020", "2020/12", "2020-13", "2020-00", "2020-12-XX"):
            with self.subTest(raw=raw):
                self.assertIsNone(_parse_candidate_date(raw))


class PreprintSplitCutoffTests(unittest.TestCase):
    def setUp(self) -> None:
        self.base_policy = TimePolicy(
            enabled=True,
            date_field="published",
            start_date=date(2018, 2, 1),
            start_inclusive=True,
            end_date=date(2023, 2, 1),
            end_inclusive=True,
            timezone="UTC",
        )
        self.split_policy = TimePolicy(
            enabled=True,
            date_field="published",
            start_date=date(2018, 2, 1),
            start_inclusive=True,
            end_date=date(2023, 2, 1),
            end_inclusive=True,
            timezone="UTC",
            preprint_split_submitted_date=True,
        )

    def test_flag_off_keeps_existing_published_only_behavior(self) -> None:
        record = {
            "key": "wang_neural_2019-1",
            "source": "arxiv",
            "source_id": "1810.11946v4",
            "published_date": "2018",
            "source_metadata": {
                "published": "2018-10-29T04:10:40Z",
                "comment": "Submitted to ICASSP 2019",
            },
        }
        decision = evaluate_record(record, self.base_policy)
        self.assertFalse(decision["cutoff_pass"])
        self.assertEqual(decision["cutoff_status"], "before_start")

    def test_split_mode_uses_submitted_date_for_preprint(self) -> None:
        record = {
            "key": "wang_neural_2019-1",
            "source": "arxiv",
            "source_id": "1810.11946v4",
            "published_date": "2018",
            "source_metadata": {
                "published": "2018-10-29T04:10:40Z",
                "comment": "Submitted to ICASSP 2019",
            },
        }
        decision = evaluate_record(record, self.split_policy)
        self.assertTrue(decision["cutoff_pass"])
        self.assertEqual(decision["cutoff_date_role"], "preprint")
        self.assertEqual(decision["cutoff_date_basis"], "submitted_date")
        self.assertEqual(decision["cutoff_interval_start_iso"], "2018-10-29")

    def test_split_mode_uses_publish_side_for_peer_reviewed_arxiv(self) -> None:
        record = {
            "key": "kameoka_convs2s-vc_2020",
            "source": "arxiv",
            "source_id": "1811.01609v3",
            "published_date": "2018",
            "source_metadata": {
                "comment": "Published in IEEE/ACM Trans. ASLP https://ieeexplore.ieee.org/document/9113442",
            },
        }
        decision = evaluate_record(record, self.split_policy)
        self.assertTrue(decision["cutoff_pass"])
        self.assertEqual(decision["cutoff_date_role"], "peer_reviewed")
        self.assertEqual(decision["cutoff_interval_start_iso"], "2020-01-01")
        self.assertEqual(decision["cutoff_interval_end_iso"], "2020-12-31")

    def test_split_mode_falls_back_to_arxiv_source_id_month_for_preprint(self) -> None:
        record = {
            "key": "luo_mg-vae_2019",
            "source": "arxiv",
            "source_id": "1909.13287",
            "published_date": "2020",
            "source_metadata": {
                "year": "2020",
            },
        }
        decision = evaluate_record(record, self.split_policy)
        self.assertTrue(decision["cutoff_pass"])
        self.assertEqual(decision["cutoff_date_role"], "preprint")
        self.assertEqual(decision["cutoff_interval_start_iso"], "2019-09-01")
        self.assertEqual(decision["cutoff_interval_end_iso"], "2019-09-30")

    def test_split_mode_allows_submitted_fallback_for_peer_reviewed_arxiv(self) -> None:
        record = {
            "key": "bollepalli_generative_2017",
            "source": "arxiv",
            "source_id": "1903.05955v1",
            "published_date": "2019",
            "source_metadata": {
                "published": "2019-03-14T12:53:45Z",
                "doi": "10.21437/Interspeech.2017-1288",
                "comment": "Accepted in Interspeech",
                "journal_ref": "Interspeech-2017",
            },
        }
        decision = evaluate_record(record, self.split_policy)
        self.assertTrue(decision["cutoff_pass"])
        self.assertEqual(decision["cutoff_date_role"], "peer_reviewed")
        self.assertEqual(decision["cutoff_date_basis"], "submitted_date_fallback")
        self.assertEqual(decision["cutoff_interval_start_iso"], "2019-03-14")

    def test_split_mode_still_excludes_out_of_window_preprint(self) -> None:
        record = {
            "key": "vaswani2017attention",
            "source": "arxiv",
            "source_id": "1706.03762v7",
            "published_date": "2017",
            "source_metadata": {
                "published": "2017-06-12T17:57:01Z",
            },
        }
        decision = evaluate_record(record, self.split_policy)
        self.assertFalse(decision["cutoff_pass"])
        self.assertEqual(decision["cutoff_status"], "before_start")


if __name__ == "__main__":
    unittest.main()
