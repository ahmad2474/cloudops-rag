"""Baseline dense retrieval with parent expansion.

Authorization is enforced by ``SearchFilters.roles`` inside the search request; this class
never sees an unauthorized chunk and therefore cannot leak one.
"""

import time

from cloudops_rag.providers.base import EmbeddingProvider, SearchFilters, SearchProvider
from cloudops_rag.retrieval.models import RetrievalResult, TrailStep


class VectorRetriever:
    def __init__(
        self,
        embedding: EmbeddingProvider,
        search: SearchProvider,
        *,
        candidates: int = 50,
        top_k: int = 8,
    ) -> None:
        self._embedding = embedding
        self._search = search
        self._candidates = candidates
        self._top_k = top_k

    async def retrieve(self, query: str, filters: SearchFilters) -> RetrievalResult:
        trail: list[TrailStep] = []

        t0 = time.perf_counter()
        qvec = await self._embedding.embed_query(query)
        trail.append(TrailStep(stage="embed_query", count=1, latency_ms=_ms(t0)))

        t0 = time.perf_counter()
        hits = await self._search.vector_search(qvec, k=self._candidates, filters=filters)
        trail.append(
            TrailStep(
                stage="vector_search",
                count=len(hits),
                latency_ms=_ms(t0),
                detail={"k": self._candidates, "roles": list(filters.roles)},
            )
        )

        top = hits[: self._top_k]
        trail.append(TrailStep(stage="select_top_k", count=len(top), latency_ms=0.0))

        t0 = time.perf_counter()
        parent_ids: list[str] = []
        for h in top:
            if h.chunk.parent_id not in parent_ids:
                parent_ids.append(h.chunk.parent_id)
        parents = await self._search.get_parents(parent_ids)
        trail.append(
            TrailStep(
                stage="parent_expansion",
                count=len(parents),
                latency_ms=_ms(t0),
                detail={"children": len(top), "deduped_parents": len(parent_ids)},
            )
        )
        return RetrievalResult(query=query, hits=top, parents=parents, trail=trail)


def _ms(t0: float) -> float:
    return round((time.perf_counter() - t0) * 1000, 2)
