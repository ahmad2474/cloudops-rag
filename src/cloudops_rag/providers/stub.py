"""Deterministic, dependency-free providers for local development and tests.

They exist so the whole pipeline can be exercised without AWS or Docker. They are *not* meant
to produce good results — only stable, inspectable ones.
"""

import hashlib
import math
import re
from collections.abc import Sequence
from typing import Any

from cloudops_rag.chunking.models import Chunk, ParentChunk
from cloudops_rag.providers.base import LLMResult, RerankedItem, SearchFilters, SearchHit


class StubEmbeddingProvider:
    """Bag-of-words hashing embeddings: shared terms → similar vectors. Deterministic."""

    def __init__(self, dimensions: int = 256) -> None:
        self._dimensions = dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def _embed(self, text: str) -> list[float]:
        vec = [0.0] * self._dimensions
        for term in re.findall(r"[a-z0-9:_\-./]+", text.lower()):
            h = int.from_bytes(hashlib.blake2b(term.encode(), digest_size=8).digest(), "big")
            vec[h % self._dimensions] += 1.0 if (h >> 63) else -1.0
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    async def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


_SOURCE_BLOCK = re.compile(r"\[S(\d+)\]\s*(.*?)(?=\n\[S\d+\]|\Z)", re.S)


class StubLLMProvider:
    """Extractive answerer: quotes the first sentence of each source with a citation.

    Exercises the citation parser/validator end to end without a model. If the user block
    contains no sources it abstains with the canonical phrase.
    """

    def __init__(self, model: str = "stub-model") -> None:
        self._model = model

    @property
    def model(self) -> str:
        return self._model

    async def generate(self, system: str, user: str, *, max_tokens: int = 1024) -> LLMResult:
        blocks = _SOURCE_BLOCK.findall(user)
        if not blocks:
            text = "INSUFFICIENT_EVIDENCE"
        else:
            lines = []
            for idx, body in blocks[:3]:
                first = re.split(
                    r"(?<=[.!?])\s", body.strip().split("\n\n")[-1].strip(), maxsplit=1
                )[0]
                lines.append(f"{first[:200]} [S{idx}]")
            text = "\n".join(lines)
        return LLMResult(
            text=text,
            input_tokens=len(user.split()) + len(system.split()),
            output_tokens=len(text.split()),
            model=self._model,
        )


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


def _matches(chunk: Chunk | ParentChunk, f: SearchFilters) -> bool:
    if not set(chunk.permissions) & set(f.roles):
        return False
    if f.document_types and chunk.document_type not in f.document_types:
        return False
    if f.environments and chunk.environment not in [*f.environments, "all"]:
        return False
    if f.version and chunk.version != f.version:
        return False
    if f.sources and chunk.source not in f.sources:
        return False
    if f.statuses and chunk.status not in f.statuses:
        return False
    return not (f.exclude_adversarial and chunk.document_type == "adversarial")


class StubSearchProvider:
    """In-memory store with brute-force cosine search. Same filter semantics as OpenSearch."""

    def __init__(self) -> None:
        self._chunks: dict[str, tuple[Chunk, list[float]]] = {}
        self._parents: dict[str, ParentChunk] = {}

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        return None

    async def ensure_indices(self, dimensions: int) -> None:
        return None

    async def indexed_document_hashes(self) -> dict[str, str]:
        return {p.document_id: p.content_hash for p in self._parents.values()}

    async def delete_document(self, document_id: str) -> None:
        self._chunks = {k: v for k, v in self._chunks.items() if v[0].document_id != document_id}
        self._parents = {k: v for k, v in self._parents.items() if v.document_id != document_id}

    async def index_chunks(
        self, chunks: Sequence[Chunk], embeddings: Sequence[Sequence[float]]
    ) -> None:
        for c, e in zip(chunks, embeddings, strict=True):
            self._chunks[c.chunk_id] = (c, list(e))

    async def index_parents(self, parents: Sequence[ParentChunk]) -> None:
        for p in parents:
            self._parents[p.parent_id] = p

    async def vector_search(
        self, embedding: Sequence[float], *, k: int, filters: SearchFilters
    ) -> list[SearchHit]:
        q = list(embedding)
        scored = [
            SearchHit(chunk=c, score=sum(a * b for a, b in zip(q, e, strict=False)))
            for c, e in self._chunks.values()
            if _matches(c, filters)
        ]
        scored.sort(key=lambda h: (-h.score, h.chunk.chunk_id))
        return scored[:k]

    async def bm25_search(self, query: str, *, k: int, filters: SearchFilters) -> list[SearchHit]:
        """Term-overlap scoring with a rough IDF; exact tokens (iam:PassRole) count double."""
        q_terms = [t for t in re.findall(r"[a-z0-9:_\-./]+", query.lower()) if len(t) > 1]
        if not q_terms:
            return []
        docs = [c for c, _ in self._chunks.values() if _matches(c, filters)]
        n = len(docs) or 1
        tokenised = {
            c.chunk_id: set(re.findall(r"[a-z0-9:_\-./]+", c.content.lower())) for c in docs
        }
        df = {t: sum(1 for toks in tokenised.values() if t in toks) for t in set(q_terms)}
        scored: list[SearchHit] = []
        for c in docs:
            toks = tokenised[c.chunk_id]
            s = 0.0
            for t in q_terms:
                if t in toks:
                    idf = math.log(1 + n / (1 + df[t]))
                    s += idf * (2.0 if any(ch in t for ch in ":_-./") else 1.0)
            if s > 0:
                scored.append(SearchHit(chunk=c, score=s))
        scored.sort(key=lambda h: (-h.score, h.chunk.chunk_id))
        return scored[:k]

    async def get_parents(self, parent_ids: Sequence[str]) -> list[ParentChunk]:
        return [self._parents[p] for p in parent_ids if p in self._parents]

    async def refresh(self) -> None:
        return None

    async def stats(self) -> dict[str, Any]:
        return {"chunks": len(self._chunks), "parents": len(self._parents)}
