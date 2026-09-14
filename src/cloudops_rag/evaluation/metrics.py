"""Retrieval, citation and abstention metrics. Pure functions; binary relevance.

``ranked`` is the ordered list of retrieved *document* ids (deduplicated, best first);
``relevant`` is the set of expected document ids.
"""

import math
from collections.abc import Sequence


def recall_at_k(ranked: Sequence[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    return len(set(ranked[:k]) & relevant) / len(relevant)


def precision_at_k(ranked: Sequence[str], relevant: set[str], k: int) -> float:
    top = ranked[:k]
    return len(set(top) & relevant) / k if k else 0.0


def mrr(ranked: Sequence[str], relevant: set[str]) -> float:
    for i, d in enumerate(ranked, start=1):
        if d in relevant:
            return 1.0 / i
    return 0.0


def ndcg_at_k(ranked: Sequence[str], relevant: set[str], k: int) -> float:
    dcg = sum(1.0 / math.log2(i + 1) for i, d in enumerate(ranked[:k], start=1) if d in relevant)
    ideal = sum(1.0 / math.log2(i + 1) for i in range(1, min(len(relevant), k) + 1))
    return dcg / ideal if ideal else 0.0


def hit_at_k(ranked: Sequence[str], relevant: set[str], k: int) -> float:
    return 1.0 if set(ranked[:k]) & relevant else 0.0


def citation_precision(cited: Sequence[str], relevant: set[str]) -> float:
    """Fraction of cited documents that are expected. Undefined (0) with no citations."""
    return len(set(cited) & relevant) / len(set(cited)) if cited else 0.0


def citation_recall(cited: Sequence[str], relevant: set[str]) -> float:
    return len(set(cited) & relevant) / len(relevant) if relevant else 0.0


def dedupe_keep_order(ids: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def mean(values: Sequence[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def percentile(values: Sequence[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = min(len(s) - 1, max(0, math.ceil(p / 100 * len(s)) - 1))
    return round(s[idx], 2)
