from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from cloudops_rag.chunking.models import ParentChunk
from cloudops_rag.retrieval.models import TrailStep

AnswerStatus = Literal["answered", "abstained", "no_authorized_evidence"]


class ContextSource(BaseModel):
    """A numbered source as shown to the model: [S1], [S2], …"""

    model_config = ConfigDict(frozen=True)

    sid: str
    parent: ParentChunk
    content: str = Field(description="Possibly truncated to fit the token budget")
    token_count: int
    truncated: bool


class Citation(BaseModel):
    """What the UI renders and the evaluator checks (spec §24)."""

    model_config = ConfigDict(frozen=True)

    sid: str
    document_id: str
    parent_id: str
    title: str
    section: str
    source_url: str | None
    document_type: str
    version: str | None
    updated_at: str
    excerpt: str


class Usage(BaseModel):
    model_config = ConfigDict(frozen=True)

    model: str
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float


class AnswerResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    query: str
    status: AnswerStatus
    answer: str
    citations: list[Citation]
    sources: list[Citation] = Field(description="Every source offered to the model, cited or not")
    dropped_citations: list[str] = Field(default_factory=list)
    trail: list[TrailStep]
    usage: Usage | None
    latency_ms: dict[str, float]
