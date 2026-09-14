"""Decorate providers with deadlines and bounded retries (spec §48: timeouts, retries).

Idempotent calls (embed, search, rerank, get_*) are retried on retryable ProviderErrors.
``generate`` is retried only if the provider failed before producing output (the error is raised
from the call itself); a completed generation is never re-run.
"""

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Any

from cloudops_rag.chunking.models import Chunk, ParentChunk
from cloudops_rag.config import Settings
from cloudops_rag.observability.resilience import retry, with_deadline
from cloudops_rag.providers.base import (
    EmbeddingProvider,
    LLMProvider,
    LLMResult,
    RerankedItem,
    RerankerProvider,
    SearchFilters,
    SearchHit,
    SearchProvider,
    StreamEvent,
)
from cloudops_rag.providers.registry import Providers


@dataclass(frozen=True)
class Budget:
    embed_s: float
    search_s: float
    rerank_s: float
    llm_s: float
    attempts: int

    @classmethod
    def from_settings(cls, s: Settings) -> "Budget":
        return cls(
            embed_s=s.timeout_embed_s,
            search_s=s.timeout_search_s,
            rerank_s=s.timeout_rerank_s,
            llm_s=s.timeout_llm_s,
            attempts=s.provider_retries,
        )


class ResilientEmbedding:
    def __init__(self, inner: EmbeddingProvider, b: Budget) -> None:
        self._inner, self._b = inner, b

    @property
    def dimensions(self) -> int:
        return self._inner.dimensions

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return await retry(
            lambda: with_deadline(
                self._inner.embed_documents(texts), self._b.embed_s * 4, what="embed_documents"
            ),
            what="embed_documents",
            attempts=self._b.attempts,
        )

    async def embed_query(self, text: str) -> list[float]:
        return await retry(
            lambda: with_deadline(
                self._inner.embed_query(text), self._b.embed_s, what="embed_query"
            ),
            what="embed_query",
            attempts=self._b.attempts,
        )


class ResilientLLM:
    def __init__(self, inner: LLMProvider, b: Budget) -> None:
        self._inner, self._b = inner, b

    @property
    def model(self) -> str:
        return self._inner.model

    async def generate(self, system: str, user: str, *, max_tokens: int = 1024) -> LLMResult:
        return await retry(
            lambda: with_deadline(
                self._inner.generate(system, user, max_tokens=max_tokens),
                self._b.llm_s,
                what="generate",
            ),
            what="generate",
            attempts=2,
        )

    async def generate_stream(
        self, system: str, user: str, *, max_tokens: int = 1024
    ) -> AsyncIterator[StreamEvent]:
        # Deadline applies per event; a stalled stream fails rather than hanging the client.
        agen = self._inner.generate_stream(system, user, max_tokens=max_tokens)
        while True:
            try:
                ev = await with_deadline(anext(agen), self._b.llm_s, what="generate_stream")
            except StopAsyncIteration:
                return
            yield ev
            if ev.done:
                return


class ResilientReranker:
    def __init__(self, inner: RerankerProvider, b: Budget) -> None:
        self._inner, self._b = inner, b

    async def rerank(
        self, query: str, documents: Sequence[str], *, top_n: int
    ) -> list[RerankedItem]:
        return await retry(
            lambda: with_deadline(
                self._inner.rerank(query, documents, top_n=top_n), self._b.rerank_s, what="rerank"
            ),
            what="rerank",
            attempts=self._b.attempts,
        )


class ResilientSearch:
    def __init__(self, inner: SearchProvider, b: Budget) -> None:
        self._inner, self._b = inner, b

    def __getattr__(self, name: str) -> Any:  # index/admin methods pass through unchanged
        return getattr(self._inner, name)

    async def ping(self) -> bool:
        return await self._inner.ping()

    async def close(self) -> None:
        await self._inner.close()

    async def vector_search(
        self, embedding: Sequence[float], *, k: int, filters: SearchFilters
    ) -> list[SearchHit]:
        return await retry(
            lambda: with_deadline(
                self._inner.vector_search(embedding, k=k, filters=filters),
                self._b.search_s,
                what="vector_search",
            ),
            what="vector_search",
            attempts=self._b.attempts,
        )

    async def bm25_search(self, query: str, *, k: int, filters: SearchFilters) -> list[SearchHit]:
        return await retry(
            lambda: with_deadline(
                self._inner.bm25_search(query, k=k, filters=filters),
                self._b.search_s,
                what="bm25_search",
            ),
            what="bm25_search",
            attempts=self._b.attempts,
        )

    async def get_parents(self, parent_ids: Sequence[str]) -> list[ParentChunk]:
        return await with_deadline(
            self._inner.get_parents(parent_ids), self._b.search_s, what="get_parents"
        )

    async def get_chunks(self, chunk_ids: Sequence[str]) -> list[Chunk]:
        return await with_deadline(
            self._inner.get_chunks(chunk_ids), self._b.search_s, what="get_chunks"
        )


def harden(providers: Providers, settings: Settings) -> Providers:
    b = Budget.from_settings(settings)
    return Providers(
        embedding=ResilientEmbedding(providers.embedding, b),
        llm=ResilientLLM(providers.llm, b),
        reranker=ResilientReranker(providers.reranker, b),
        search=ResilientSearch(providers.search, b),
    )
