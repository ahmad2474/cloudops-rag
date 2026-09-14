from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from cloudops_rag.chunking.models import ParentChunk
from cloudops_rag.retrieval.models import TrailStep

AnswerStatus = Literal["answered", "abstained", "no_authorized_evidence", "blocked"]


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
    content: str = Field(default="", description="the section text as offered to the model")
    token_count: int = 0


class Conflict(BaseModel):
    """Two or more offered sources that plausibly disagree, detected from metadata."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["version", "deprecated", "stale"]
    sids: list[str]
    preferred: str
    note: str


class EvidenceStrength(BaseModel):
    """Derived from retrieval/citation signals — never the model's self-reported confidence."""

    model_config = ConfigDict(frozen=True)

    score: float
    label: Literal["high", "medium", "low", "none"]
    signals: dict[str, float]


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
    guard_reasons: list[str] = Field(default_factory=list)
    conflicts: list[Conflict] = Field(default_factory=list)
    evidence: EvidenceStrength | None = None
    query_plan: dict[str, object] = Field(default_factory=dict)
    trail: list[TrailStep]
    usage: Usage | None
    latency_ms: dict[str, float]
