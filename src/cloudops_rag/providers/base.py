"""Protocol definitions for every external capability the system uses.

Keep these minimal. Method signatures will grow in later phases (filters, token accounting,
streaming) — extend them deliberately and update every implementation in the same change.
"""

from collections.abc import Sequence
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict


class SearchHit(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    score: float
    source: dict[str, Any]


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


@runtime_checkable
class LLMProvider(Protocol):
    @property
    def model(self) -> str: ...

    async def generate(self, system: str, user: str, *, max_tokens: int = 1024) -> str: ...


@runtime_checkable
class RerankerProvider(Protocol):
    async def rerank(
        self, query: str, documents: Sequence[str], *, top_n: int
    ) -> list[RerankedItem]: ...


@runtime_checkable
class SearchProvider(Protocol):
    async def ping(self) -> bool: ...

    async def close(self) -> None: ...
