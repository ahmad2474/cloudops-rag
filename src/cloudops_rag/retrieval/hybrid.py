"""HybridRetriever: vector | bm25 | hybrid (RRF or weighted) → optional rerank → parents.

Authorization is enforced by ``SearchFilters.roles`` inside every search request; this class
never sees an unauthorized chunk. Every stage is recorded in the trail with counts and latency.
"""

import asyncio
import time
from typing import Literal

from cloudops_rag.providers.base import (
    EmbeddingProvider,
    RerankerProvider,
    SearchFilters,
    SearchHit,
    SearchProvider,
)
from cloudops_rag.retrieval.context_units import ContextMode, build_units
from cloudops_rag.retrieval.fusion import rrf, weighted
from cloudops_rag.retrieval.models import RetrievalResult, TrailStep

Strategy = Literal["vector", "bm25", "hybrid_rrf", "hybrid_weighted"]


class HybridRetriever:
    def __init__(
        self,
        embedding: EmbeddingProvider,
        search: SearchProvider,
        *,
        strategy: Strategy = "vector",
        candidates: int = 50,
        top_k: int = 8,
        reranker: RerankerProvider | None = None,
        rerank_candidates: int = 20,
        rrf_k: int = 60,
        vector_weight: float = 0.5,
        context_mode: ContextMode = "parent",
        context_window: int = 1,
    ) -> None:
        self._embedding = embedding
        self._search = search
        self._strategy: Strategy = strategy
        self._candidates = candidates
        self._top_k = top_k
        self._reranker = reranker
        self._rerank_candidates = rerank_candidates
        self._rrf_k = rrf_k
        self._vector_weight = vector_weight
        self._context_mode: ContextMode = context_mode
        self._context_window = context_window

    @property
    def label(self) -> str:
        mode = "" if self._context_mode == "parent" else f"+{self._context_mode}"
        return f"{self._strategy}{'+rerank' if self._reranker else ''}{mode}"

    async def retrieve(self, query: str, filters: SearchFilters) -> RetrievalResult:
        trail: list[TrailStep] = []
        use_vec = self._strategy != "bm25"
        use_bm25 = self._strategy != "vector"

        vec_hits: list[SearchHit] = []
        bm25_hits: list[SearchHit] = []
        tasks = []
        if use_vec:
            tasks.append(self._vector(query, filters, trail))
        if use_bm25:
            tasks.append(self._bm25(query, filters, trail))
        results = await asyncio.gather(*tasks)
        if use_vec:
            vec_hits = results[0]
        if use_bm25:
            bm25_hits = results[-1]

        # --- fusion -------------------------------------------------------------------------
        t0 = time.perf_counter()
        by_id = {h.chunk.chunk_id: h for h in [*vec_hits, *bm25_hits]}
        if self._strategy == "vector":
            fused = [(h.chunk.chunk_id, h.score) for h in vec_hits]
        elif self._strategy == "bm25":
            fused = [(h.chunk.chunk_id, h.score) for h in bm25_hits]
        elif self._strategy == "hybrid_rrf":
            fused = rrf(
                [[h.chunk.chunk_id for h in vec_hits], [h.chunk.chunk_id for h in bm25_hits]],
                k=self._rrf_k,
            )
        else:
            fused = weighted(
                [
                    {h.chunk.chunk_id: h.score for h in vec_hits},
                    {h.chunk.chunk_id: h.score for h in bm25_hits},
                ],
                [self._vector_weight, 1.0 - self._vector_weight],
            )
        candidates = [SearchHit(chunk=by_id[cid].chunk, score=s) for cid, s in fused]
        if use_vec and use_bm25:
            overlap = len(
                {h.chunk.chunk_id for h in vec_hits} & {h.chunk.chunk_id for h in bm25_hits}
            )
            trail.append(
                TrailStep(
                    stage="fusion",
                    count=len(candidates),
                    latency_ms=_ms(t0),
                    detail={"method": self._strategy, "overlap": overlap},
                )
            )

        # --- rerank -------------------------------------------------------------------------
        if self._reranker is not None and candidates:
            t0 = time.perf_counter()
            pool = candidates[: self._rerank_candidates]
            ranked = await self._reranker.rerank(
                query, [h.chunk.embedding_text for h in pool], top_n=self._top_k
            )
            candidates = [SearchHit(chunk=pool[r.index].chunk, score=r.score) for r in ranked]
            trail.append(
                TrailStep(
                    stage="rerank",
                    count=len(candidates),
                    latency_ms=_ms(t0),
                    detail={"pool": len(pool)},
                )
            )

        top = candidates[: self._top_k]
        trail.append(TrailStep(stage="select_top_k", count=len(top), latency_ms=0.0))

        # --- parent expansion ---------------------------------------------------------------
        t0 = time.perf_counter()
        parents = await build_units(
            top, self._search, mode=self._context_mode, window=self._context_window
        )
        trail.append(
            TrailStep(
                stage="parent_expansion",
                count=len(parents),
                latency_ms=_ms(t0),
                detail={
                    "mode": self._context_mode,
                    "children": len(top),
                    "units": len(parents),
                    "context_tokens": sum(p.token_count for p in parents),
                },
            )
        )
        return RetrievalResult(query=query, hits=top, parents=parents, trail=trail)

    async def _vector(
        self, query: str, filters: SearchFilters, trail: list[TrailStep]
    ) -> list[SearchHit]:
        t0 = time.perf_counter()
        qvec = await self._embedding.embed_query(query)
        embed_ms = _ms(t0)
        t1 = time.perf_counter()
        hits = await self._search.vector_search(qvec, k=self._candidates, filters=filters)
        trail.append(TrailStep(stage="embed_query", count=1, latency_ms=embed_ms))
        trail.append(
            TrailStep(
                stage="vector_search",
                count=len(hits),
                latency_ms=_ms(t1),
                detail={"k": self._candidates, "roles": list(filters.roles)},
            )
        )
        return hits

    async def _bm25(
        self, query: str, filters: SearchFilters, trail: list[TrailStep]
    ) -> list[SearchHit]:
        t0 = time.perf_counter()
        hits = await self._search.bm25_search(query, k=self._candidates, filters=filters)
        trail.append(
            TrailStep(
                stage="bm25_search",
                count=len(hits),
                latency_ms=_ms(t0),
                detail={"k": self._candidates, "roles": list(filters.roles)},
            )
        )
        return hits


def _ms(t0: float) -> float:
    return round((time.perf_counter() - t0) * 1000, 2)
