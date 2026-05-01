from __future__ import annotations

from dataclasses import dataclass


MILLION = 1_000_000.0
THOUSAND = 1_000.0


@dataclass(frozen=True)
class ModelTokenPrice:
    """OpenAI token prices in USD per 1M tokens."""

    input_per_million: float
    cached_input_per_million: float
    output_per_million: float


@dataclass(frozen=True)
class FileSearchPrice:
    """Responses API file_search prices."""

    tool_call_per_1000: float = 2.50
    vector_storage_per_gb_day: float = 0.10
    free_vector_storage_gb: float = 1.0


@dataclass(frozen=True)
class CostBreakdown:
    token_cost_usd: float
    file_search_call_cost_usd: float = 0.0
    vector_storage_cost_usd: float = 0.0

    @property
    def total_cost_usd(self) -> float:
        return (
            self.token_cost_usd
            + self.file_search_call_cost_usd
            + self.vector_storage_cost_usd
        )


# Official standard API prices observed on 2026-05-01. Keep this table explicit so
# historical screening cost reports remain reproducible when public prices change.
OPENAI_STANDARD_MODEL_PRICES: dict[str, ModelTokenPrice] = {
    "gpt-5-nano": ModelTokenPrice(
        input_per_million=0.05,
        cached_input_per_million=0.005,
        output_per_million=0.40,
    ),
    "gpt-5.4-mini": ModelTokenPrice(
        input_per_million=0.75,
        cached_input_per_million=0.075,
        output_per_million=4.50,
    ),
}


OPENAI_RESPONSES_FILE_SEARCH_PRICE = FileSearchPrice()


def token_cost_usd(
    *,
    input_tokens: int,
    output_tokens: int,
    model_price: ModelTokenPrice,
    cached_input_tokens: int = 0,
) -> float:
    """Return model token cost in USD."""

    _require_nonnegative_int("input_tokens", input_tokens)
    _require_nonnegative_int("output_tokens", output_tokens)
    _require_nonnegative_int("cached_input_tokens", cached_input_tokens)

    cached = min(cached_input_tokens, input_tokens)
    uncached = input_tokens - cached
    return (
        uncached * model_price.input_per_million / MILLION
        + cached * model_price.cached_input_per_million / MILLION
        + output_tokens * model_price.output_per_million / MILLION
    )


def inline_fulltext_cost_usd(
    *,
    input_tokens: int,
    output_tokens: int,
    model_price: ModelTokenPrice,
    cached_input_tokens: int = 0,
) -> CostBreakdown:
    """Cost for the current inline full-text strategy."""

    return CostBreakdown(
        token_cost_usd=token_cost_usd(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_input_tokens=cached_input_tokens,
            model_price=model_price,
        )
    )


def responses_file_search_cost_usd(
    *,
    base_prompt_tokens_per_call: int,
    retrieved_tokens_per_call: int,
    output_tokens_per_call: int,
    tool_calls: int,
    model_price: ModelTokenPrice,
    cached_input_tokens_per_call: int = 0,
    file_search_price: FileSearchPrice = OPENAI_RESPONSES_FILE_SEARCH_PRICE,
    vector_store_gb: float = 0.0,
    storage_days: float = 0.0,
) -> CostBreakdown:
    """Cost for Responses API file_search plus model tokens.

    `base_prompt_tokens_per_call` is the non-fulltext prompt sent with each
    retrieval call. `retrieved_tokens_per_call` is the retrieved context that is
    ultimately supplied to the model after file_search ranking.
    """

    _require_nonnegative_int("base_prompt_tokens_per_call", base_prompt_tokens_per_call)
    _require_nonnegative_int("retrieved_tokens_per_call", retrieved_tokens_per_call)
    _require_nonnegative_int("output_tokens_per_call", output_tokens_per_call)
    _require_nonnegative_int("tool_calls", tool_calls)
    _require_nonnegative_int(
        "cached_input_tokens_per_call", cached_input_tokens_per_call
    )
    _require_nonnegative_float("vector_store_gb", vector_store_gb)
    _require_nonnegative_float("storage_days", storage_days)

    input_tokens = tool_calls * (
        base_prompt_tokens_per_call + retrieved_tokens_per_call
    )
    output_tokens = tool_calls * output_tokens_per_call
    cached_input_tokens = tool_calls * cached_input_tokens_per_call
    token_cost = token_cost_usd(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_input_tokens=cached_input_tokens,
        model_price=model_price,
    )
    call_cost = tool_calls * file_search_price.tool_call_per_1000 / THOUSAND
    billable_gb = max(0.0, vector_store_gb - file_search_price.free_vector_storage_gb)
    storage_cost = billable_gb * storage_days * file_search_price.vector_storage_per_gb_day
    return CostBreakdown(
        token_cost_usd=token_cost,
        file_search_call_cost_usd=call_cost,
        vector_storage_cost_usd=storage_cost,
    )


def responses_file_search_response_cost_usd(
    *,
    base_prompt_tokens: int,
    retrieved_tokens_total: int,
    output_tokens: int,
    tool_calls: int,
    model_price: ModelTokenPrice,
    cached_input_tokens: int = 0,
    file_search_price: FileSearchPrice = OPENAI_RESPONSES_FILE_SEARCH_PRICE,
    vector_store_gb: float = 0.0,
    storage_days: float = 0.0,
) -> CostBreakdown:
    """Cost for one Responses request that may perform file_search tool calls.

    Use this when a single final answer sees one base prompt plus all retrieved
    context. `tool_calls` affects the file_search fee, not the base prompt count.
    """

    _require_nonnegative_int("base_prompt_tokens", base_prompt_tokens)
    _require_nonnegative_int("retrieved_tokens_total", retrieved_tokens_total)
    _require_nonnegative_int("output_tokens", output_tokens)
    _require_nonnegative_int("tool_calls", tool_calls)
    _require_nonnegative_int("cached_input_tokens", cached_input_tokens)
    _require_nonnegative_float("vector_store_gb", vector_store_gb)
    _require_nonnegative_float("storage_days", storage_days)

    token_cost = token_cost_usd(
        input_tokens=base_prompt_tokens + retrieved_tokens_total,
        output_tokens=output_tokens,
        cached_input_tokens=cached_input_tokens,
        model_price=model_price,
    )
    call_cost = tool_calls * file_search_price.tool_call_per_1000 / THOUSAND
    billable_gb = max(0.0, vector_store_gb - file_search_price.free_vector_storage_gb)
    storage_cost = billable_gb * storage_days * file_search_price.vector_storage_per_gb_day
    return CostBreakdown(
        token_cost_usd=token_cost,
        file_search_call_cost_usd=call_cost,
        vector_storage_cost_usd=storage_cost,
    )


def compare_inline_to_responses_file_search(
    *,
    inline_input_tokens: int,
    inline_output_tokens: int,
    base_prompt_tokens_per_call: int,
    retrieved_tokens_per_call: int,
    file_search_output_tokens_per_call: int,
    tool_calls: int,
    model_price: ModelTokenPrice,
    inline_cached_input_tokens: int = 0,
    file_search_cached_input_tokens_per_call: int = 0,
    file_search_price: FileSearchPrice = OPENAI_RESPONSES_FILE_SEARCH_PRICE,
    vector_store_gb: float = 0.0,
    storage_days: float = 0.0,
) -> dict[str, CostBreakdown]:
    """Return comparable cost breakdowns for inline and Responses file_search."""

    return {
        "inline": inline_fulltext_cost_usd(
            input_tokens=inline_input_tokens,
            output_tokens=inline_output_tokens,
            cached_input_tokens=inline_cached_input_tokens,
            model_price=model_price,
        ),
        "responses_file_search": responses_file_search_cost_usd(
            base_prompt_tokens_per_call=base_prompt_tokens_per_call,
            retrieved_tokens_per_call=retrieved_tokens_per_call,
            output_tokens_per_call=file_search_output_tokens_per_call,
            tool_calls=tool_calls,
            cached_input_tokens_per_call=file_search_cached_input_tokens_per_call,
            file_search_price=file_search_price,
            vector_store_gb=vector_store_gb,
            storage_days=storage_days,
            model_price=model_price,
        ),
    }


def _require_nonnegative_int(name: str, value: int) -> None:
    if not isinstance(value, int):
        raise TypeError(f"{name} must be an int")
    if value < 0:
        raise ValueError(f"{name} must be non-negative")


def _require_nonnegative_float(name: str, value: float) -> None:
    if value < 0:
        raise ValueError(f"{name} must be non-negative")
