"""Rank fusion for hybrid retrieval (spec §9). Documented, tested, never "average the scores".

Both functions take per-source rankings of *chunk ids* (best first) with their raw scores and
return a fused ranking with fused scores.
"""

from collections.abc import Mapping, Sequence


def rrf(rankings: Sequence[Sequence[str]], *, k: int = 60) -> list[tuple[str, float]]:
    """Reciprocal Rank Fusion: score(d) = Σ_sources 1 / (k + rank_source(d)).

    Rank-only, scale-free — the robust default when score distributions differ (cosine vs BM25).
    """
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, cid in enumerate(ranking, start=1):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))


def _min_max(scores: Mapping[str, float]) -> dict[str, float]:
    if not scores:
        return {}
    lo, hi = min(scores.values()), max(scores.values())
    if hi - lo < 1e-12:
        return {k: 1.0 for k in scores}
    return {k: (v - lo) / (hi - lo) for k, v in scores.items()}


def weighted(
    sources: Sequence[Mapping[str, float]], weights: Sequence[float]
) -> list[tuple[str, float]]:
    """Convex combination of per-source min-max-normalised scores.

    A document missing from a source contributes 0 from it. Weights are normalised to sum 1.
    """
    if len(sources) != len(weights):
        raise ValueError("sources and weights length mismatch")
    total = sum(weights)
    if total <= 0:
        raise ValueError("weights must sum to a positive number")
    norm_w = [w / total for w in weights]
    fused: dict[str, float] = {}
    for src, w in zip(sources, norm_w, strict=True):
        for cid, s in _min_max(src).items():
            fused[cid] = fused.get(cid, 0.0) + w * s
    return sorted(fused.items(), key=lambda kv: (-kv[1], kv[0]))
