#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
RESEARCH_ROOT = REPO_ROOT / "research_bcpcs_2026-04-18"
RUNS_ROOT = RESEARCH_ROOT / "runs"
REPORTS_ROOT = RESEARCH_ROOT / "reports"
SRC_ROOT = RESEARCH_ROOT / "src"
SCHEMA_ROOT = RESEARCH_ROOT / "schemas"
DEFAULT_MODEL = "gpt-5-nano"
DEFAULT_ENDPOINT = "/v1/chat/completions"
DEFAULT_COST_CAP_USD = 10.0


if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


class PathGuardError(ValueError):
    pass


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ensure_under_research(path: Path) -> Path:
    resolved = path.resolve()
    root = RESEARCH_ROOT.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise PathGuardError(f"Refusing to write outside research root: {resolved}") from exc
    return resolved


def ensure_dir(path: Path) -> Path:
    guarded = ensure_under_research(path)
    guarded.mkdir(parents=True, exist_ok=True)
    return guarded


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    guarded = ensure_under_research(path)
    guarded.parent.mkdir(parents=True, exist_ok=True)
    guarded.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        item = json.loads(stripped)
        if not isinstance(item, dict):
            raise ValueError(f"Expected object JSONL row at {path}:{index}")
        rows.append(item)
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    guarded = ensure_under_research(path)
    guarded.parent.mkdir(parents=True, exist_ok=True)
    with guarded.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repo_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path)


def safe_text(value: Any) -> str:
    return str(value or "").strip()


def load_dotenv_if_present() -> None:
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def run_dir(run_id: str) -> Path:
    return RUNS_ROOT / run_id


def batch_dir(run_id: str, phase: str, model: str = DEFAULT_MODEL) -> Path:
    return run_dir(run_id) / "batch_jobs" / phase / model


def paper_dir(run_id: str, paper_id: str) -> Path:
    return run_dir(run_id) / "papers" / paper_id


def cost_dir(run_id: str) -> Path:
    return run_dir(run_id) / "cost"


def estimate_text_tokens(text: str) -> int:
    conservative = max(1, int((len(text) + 3.5 - 1) // 3.5))
    try:
        import tiktoken  # type: ignore

        try:
            encoding = tiktoken.encoding_for_model(DEFAULT_MODEL)
        except Exception:  # noqa: BLE001
            encoding = tiktoken.get_encoding("o200k_base")
        return max(len(encoding.encode(text)), conservative)
    except Exception:  # noqa: BLE001
        return conservative


@dataclass(frozen=True)
class CostRates:
    input_per_million: float
    cached_input_per_million: float
    output_per_million: float
    batch_discount: float = 0.5
    source: str = "https://developers.openai.com/api/docs/models/gpt-5-nano"

    @classmethod
    def gpt5_nano_standard(cls) -> "CostRates":
        return cls(input_per_million=0.05, cached_input_per_million=0.005, output_per_million=0.40, batch_discount=0.0)

    @classmethod
    def gpt5_nano_batch(cls) -> "CostRates":
        return cls(input_per_million=0.05, cached_input_per_million=0.005, output_per_million=0.40, batch_discount=0.5)

    def effective_input_per_million(self) -> float:
        return self.input_per_million * (1.0 - self.batch_discount)

    def effective_output_per_million(self) -> float:
        return self.output_per_million * (1.0 - self.batch_discount)


def estimate_batch_cost(*, input_tokens: int, output_tokens: int, rates: CostRates | None = None) -> float:
    selected = rates or CostRates.gpt5_nano_batch()
    return (input_tokens / 1_000_000) * selected.effective_input_per_million() + (
        output_tokens / 1_000_000
    ) * selected.effective_output_per_million()


def pricing_snapshot_payload() -> dict[str, Any]:
    rates = CostRates.gpt5_nano_batch()
    return {
        "captured_at": utc_now_iso(),
        "model": DEFAULT_MODEL,
        "pricing_basis": "Batch API text tokens, per 1M tokens",
        "standard_rates_usd_per_1m": {
            "input": rates.input_per_million,
            "cached_input": rates.cached_input_per_million,
            "output": rates.output_per_million,
        },
        "batch_discount": rates.batch_discount,
        "effective_batch_rates_usd_per_1m": {
            "input": rates.effective_input_per_million(),
            "output": rates.effective_output_per_million(),
        },
        "sources": [
            "https://developers.openai.com/api/docs/models/gpt-5-nano",
            "https://platform.openai.com/docs/pricing",
            "https://openai.com/api/pricing/",
        ],
        "notes": [
            "OpenAI model page lists gpt-5-nano input $0.05 / 1M tokens and output $0.40 / 1M tokens.",
            "OpenAI pricing page documents Batch API savings on inputs and outputs.",
        ],
    }


def request_rows_token_estimate(rows: list[dict[str, Any]]) -> int:
    return sum(estimate_text_tokens(json.dumps(row.get("body", row), ensure_ascii=False)) for row in rows)


def usage_from_batch_output_row(row: dict[str, Any]) -> dict[str, int] | None:
    response = row.get("response")
    if not isinstance(response, dict):
        return None
    body = response.get("body")
    if not isinstance(body, dict):
        return None
    usage = body.get("usage")
    if not isinstance(usage, dict):
        return None
    input_tokens = usage.get("prompt_tokens", usage.get("input_tokens"))
    output_tokens = usage.get("completion_tokens", usage.get("output_tokens"))
    total_tokens = usage.get("total_tokens")
    out: dict[str, int] = {}
    if isinstance(input_tokens, int):
        out["input_tokens"] = input_tokens
    if isinstance(output_tokens, int):
        out["output_tokens"] = output_tokens
    if isinstance(total_tokens, int):
        out["total_tokens"] = total_tokens
    return out if out else None


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    guarded = ensure_under_research(path)
    guarded.parent.mkdir(parents=True, exist_ok=True)
    with guarded.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
