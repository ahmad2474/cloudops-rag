"""Deterministic, dependency-free providers for local development and tests.

They exist so the whole pipeline can be exercised without AWS or Docker. They are *not* meant
to produce good results — only stable, inspectable ones.
"""

import hashlib
import math
from collections.abc import Sequence

from cloudops_rag.providers.base import RerankedItem


class StubEmbeddingProvider:
    """Hash-based pseudo-embeddings: same text → same unit vector."""

    def __init__(self, dimensions: int = 256) -> None:
        self._dimensions = dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def _embed(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        raw = [(digest[i % len(digest)] - 128) / 128.0 for i in range(self._dimensions)]
        norm = math.sqrt(sum(x * x for x in raw)) or 1.0
        return [x / norm for x in raw]

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    async def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


class StubLLMProvider:
    """Echoes a fixed, clearly-labelled response so tests can assert on plumbing."""

    def __init__(self, model: str = "stub-model") -> None:
        self._model = model

    @property
    def model(self) -> str:
        return self._model

    async def generate(self, system: str, user: str, *, max_tokens: int = 1024) -> str:
        return f"[stub:{self._model}] {user[:max_tokens]}"


class StubRerankerProvider:
    """Ranks by naive term overlap. Deterministic; good enough to test ordering logic."""

    async def rerank(
        self, query: str, documents: Sequence[str], *, top_n: int
    ) -> list[RerankedItem]:
        q_terms = set(query.lower().split())
        scored = [
            RerankedItem(
                index=i, score=len(q_terms & set(doc.lower().split())) / (len(q_terms) or 1)
            )
            for i, doc in enumerate(documents)
        ]
        scored.sort(key=lambda item: (-item.score, item.index))
        return scored[:top_n]


class StubSearchProvider:
    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        return None
