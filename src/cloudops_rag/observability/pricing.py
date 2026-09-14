"""On-demand Bedrock list prices, USD per 1M tokens (us-east-1, checked 2026-09).

Estimates only — actual billing comes from Cost Explorer. Unknown models estimate as 0 and
are flagged so the UI never shows a fabricated cost.
"""

PRICES: dict[str, tuple[float, float]] = {
    # model id: (input, output)
    "amazon.nova-micro-v1:0": (0.035, 0.14),
    "amazon.nova-lite-v1:0": (0.06, 0.24),
    "amazon.nova-pro-v1:0": (0.80, 3.20),
    "amazon.titan-embed-text-v2:0": (0.02, 0.0),
    "deepseek.v3-v1:0": (0.62, 1.85),
    "stub-model": (0.0, 0.0),
    "stub-rerank": (0.0, 0.0),
    "stub-embed": (0.0, 0.0),
}


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int = 0) -> float:
    inp, out = PRICES.get(model, (0.0, 0.0))
    return round((input_tokens * inp + output_tokens * out) / 1_000_000, 6)


# Rerank models bill per query (per 1,000 queries), not per token.
RERANK_PRICE_PER_QUERY: dict[str, float] = {"cohere.rerank-v3-5:0": 2.00 / 1000}


def estimate_rerank_cost_usd(model: str, queries: int = 1) -> float:
    return round(RERANK_PRICE_PER_QUERY.get(model, 0.0) * queries, 6)


def is_priced(model: str) -> bool:
    return model in PRICES
