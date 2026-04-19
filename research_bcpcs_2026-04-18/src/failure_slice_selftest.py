#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from pathlib import Path

from failure_slice_common import CostRates, estimate_batch_cost, estimate_text_tokens
from failure_slice_inventory import build_failure_slice_inventory
from failure_slice_validate import find_forbidden_prompt_terms


def test_inventory_counts() -> None:
    inventory = build_failure_slice_inventory()
    assert len(inventory["cases"]) == 127
    assert inventory["summary"]["primary_count"] == 22
    assert inventory["summary"]["secondary_count"] == 105


def test_prompt_forbidden_scan() -> None:
    clean = "Use title, abstract, metadata, and criteria. Missingness may be source_gold_tension."
    dirty = "Do not leak primary_label or why_primary into prompts."
    assert find_forbidden_prompt_terms(clean) == []
    hits = find_forbidden_prompt_terms(dirty)
    assert "primary_label" in hits
    assert "why_primary" in hits


def test_cost_estimate_batch_discount() -> None:
    tokens = estimate_text_tokens("a" * 3500)
    assert 900 <= tokens <= 1100
    cost = estimate_batch_cost(input_tokens=1_000_000, output_tokens=1_000_000, rates=CostRates.gpt5_nano_batch())
    assert abs(cost - 0.225) < 1e-9


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        assert Path(tmp).exists()
    test_inventory_counts()
    test_prompt_forbidden_scan()
    test_cost_estimate_batch_discount()
    print("failure_slice_selftest passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
