"""Protocol definitions for every external capability the system uses.

Keep these minimal. Method signatures grow in later phases (BM25, hybrid, reranker inputs,
streaming) — extend them deliberately and update every implementation in the same change.
"""

from collections.abc import AsyncIterator, Sequence
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from cloudops_rag.chunking.models import Chunk, ParentChunk
from cloudops_rag.ingestion.documents import Role


class SearchHit(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk: Chunk
    score: float


class SearchFilters(BaseModel):
    """Everything that narrows a search. ``roles`` is mandatory: authorization is a filter."""

    model_config = ConfigDict(frozen=True)

    roles: list[Role] = Field(min_length=1)
    document_types: list[str] | None = None
    environments: list[str] | None = None
    version: str | None = None
    sources: list[str] | None = None
    statuses: list[str] | None = Field(default=["active"])
    exclude_adversarial: bool = False


class RerankedItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    index: int
    score: float


@runtime_checkable
class EmbeddingProvider(Protocol):
    @property
    def dimensions(self) -> int: ...

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    async def embed_query(self, text: str) -> list[float]: ...


class LLMResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""


class StreamEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    delta: str = ""
    done: bool = False
    result: LLMResult | None = None


@runtime_checkable
class LLMProvider(Protocol):
    @property
    def model(self) -> str: ...

    async def generate(self, system: str, user: str, *, max_tokens: int = 1024) -> LLMResult: ...

    def generate_stream(
        self, system: str, user: str, *, max_tokens: int = 1024
    ) -> AsyncIterator[StreamEvent]:
        """Yield text deltas, then exactly one final event carrying usage."""
        ...


@runtime_checkable
class RerankerProvider(Protocol):
    async def rerank(
        self, query: str, documents: Sequence[str], *, top_n: int
    ) -> list[RerankedItem]: ...


@runtime_checkable
class SearchProvider(Protocol):
    """Chunk/parent store + vector search. BM25 and hybrid land here in Phase 4."""

    async def ping(self) -> bool: ...

    async def close(self) -> None: ...

    async def ensure_indices(self, dimensions: int) -> None: ...

    async def indexed_document_hashes(self) -> dict[str, str]:
        """document_id -> content_hash for everything currently indexed."""
        ...

    async def delete_document(self, document_id: str) -> None: ...

    async def index_chunks(
        self, chunks: Sequence[Chunk], embeddings: Sequence[Sequence[float]]
    ) -> None: ...

    async def index_parents(self, parents: Sequence[ParentChunk]) -> None: ...

    async def vector_search(
        self, embedding: Sequence[float], *, k: int, filters: SearchFilters
    ) -> list[SearchHit]: ...

    async def bm25_search(self, query: str, *, k: int, filters: SearchFilters) -> list[SearchHit]:
        """Lexical search over content/content.exact/title with the same filter clauses."""
        ...

    async def get_parents(self, parent_ids: Sequence[str]) -> list[ParentChunk]: ...

    async def get_chunks(self, chunk_ids: Sequence[str]) -> list[Chunk]: ...

    async def refresh(self) -> None:
        """Make all prior writes visible to search (bulk loads defer this for speed)."""
        ...

    async def stats(self) -> dict[str, Any]: ...
