from pydantic import BaseModel, ConfigDict, Field

from cloudops_rag.chunking.models import ParentChunk
from cloudops_rag.providers.base import SearchHit


class TrailStep(BaseModel):
    """One stage of the retrieval pipeline, for the UI's retrieval trail and for evaluation."""

    model_config = ConfigDict(frozen=True)

    stage: str
    count: int
    latency_ms: float
    detail: dict[str, object] = Field(default_factory=dict)


class RetrievalResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    query: str
    hits: list[SearchHit] = Field(description="Top child chunks, best first")
    parents: list[ParentChunk] = Field(description="Expanded parents, ordered by best child rank")
    trail: list[TrailStep]

    @property
    def total_latency_ms(self) -> float:
        return round(sum(s.latency_ms for s in self.trail), 2)
