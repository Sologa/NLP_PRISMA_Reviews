from __future__ import annotations

import unittest

from scripts.screening.fulltext_cost_estimator import (
    FileSearchPrice,
    ModelTokenPrice,
    compare_inline_to_responses_file_search,
    inline_fulltext_cost_usd,
    responses_file_search_cost_usd,
    responses_file_search_response_cost_usd,
    token_cost_usd,
)


class FulltextCostEstimatorTests(unittest.TestCase):
    def test_token_cost_separates_cached_input_and_output(self) -> None:
        price = ModelTokenPrice(
            input_per_million=1.0,
            cached_input_per_million=0.1,
            output_per_million=10.0,
        )

        cost = token_cost_usd(
            input_tokens=1_000_000,
            cached_input_tokens=250_000,
            output_tokens=100_000,
            model_price=price,
        )

        self.assertAlmostEqual(1.775, cost)

    def test_inline_fulltext_returns_token_only_breakdown(self) -> None:
        breakdown = inline_fulltext_cost_usd(
            input_tokens=10_000,
            output_tokens=1_000,
            model_price=ModelTokenPrice(
                input_per_million=0.05,
                cached_input_per_million=0.005,
                output_per_million=0.40,
            ),
        )

        self.assertAlmostEqual(0.0009, breakdown.total_cost_usd)
        self.assertEqual(0.0, breakdown.file_search_call_cost_usd)

    def test_responses_file_search_includes_call_and_billable_storage(self) -> None:
        breakdown = responses_file_search_cost_usd(
            base_prompt_tokens_per_call=1_000,
            retrieved_tokens_per_call=4_000,
            output_tokens_per_call=500,
            tool_calls=2,
            vector_store_gb=2.5,
            storage_days=3,
            file_search_price=FileSearchPrice(
                tool_call_per_1000=2.50,
                vector_storage_per_gb_day=0.10,
                free_vector_storage_gb=1.0,
            ),
            model_price=ModelTokenPrice(
                input_per_million=1.0,
                cached_input_per_million=0.1,
                output_per_million=10.0,
            ),
        )

        self.assertAlmostEqual(0.02, breakdown.token_cost_usd)
        self.assertAlmostEqual(0.005, breakdown.file_search_call_cost_usd)
        self.assertAlmostEqual(0.45, breakdown.vector_storage_cost_usd)
        self.assertAlmostEqual(0.475, breakdown.total_cost_usd)

    def test_single_response_file_search_does_not_repeat_base_prompt(self) -> None:
        breakdown = responses_file_search_response_cost_usd(
            base_prompt_tokens=1_000,
            retrieved_tokens_total=12_000,
            output_tokens=500,
            tool_calls=3,
            model_price=ModelTokenPrice(
                input_per_million=1.0,
                cached_input_per_million=0.1,
                output_per_million=10.0,
            ),
        )

        self.assertAlmostEqual(0.018, breakdown.token_cost_usd)
        self.assertAlmostEqual(0.0075, breakdown.file_search_call_cost_usd)

    def test_compare_inline_to_responses_file_search(self) -> None:
        result = compare_inline_to_responses_file_search(
            inline_input_tokens=10_000,
            inline_output_tokens=1_000,
            base_prompt_tokens_per_call=2_000,
            retrieved_tokens_per_call=4_000,
            file_search_output_tokens_per_call=1_000,
            tool_calls=1,
            model_price=ModelTokenPrice(
                input_per_million=1.0,
                cached_input_per_million=0.1,
                output_per_million=1.0,
            ),
        )

        self.assertEqual({"inline", "responses_file_search"}, set(result))
        self.assertLess(
            result["responses_file_search"].token_cost_usd,
            result["inline"].token_cost_usd,
        )
        self.assertGreater(
            result["responses_file_search"].file_search_call_cost_usd,
            result["inline"].file_search_call_cost_usd,
        )


if __name__ == "__main__":
    unittest.main()
