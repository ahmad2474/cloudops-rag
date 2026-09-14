from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.dependencies import Roles, State
from cloudops_rag.chunking.models import Chunk
from cloudops_rag.generation.models import AnswerResponse
from cloudops_rag.ingestion.documents import Role
from cloudops_rag.providers.base import SearchFilters
from cloudops_rag.retrieval import Strategy
from cloudops_rag.retrieval.models import TrailStep

router = APIRouter(tags=["query"])


class QueryFilters(BaseModel):
    document_types: list[str] | None = None
    environments: list[str] | None = None
    version: str | None = None
    sources: list[str] | None = None
    include_deprecated: bool = False


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    filters: QueryFilters = Field(default_factory=QueryFilters)
    strategy: Strategy | None = Field(default=None, description="override configured strategy")
    rerank: bool | None = Field(default=None, description="override configured reranking")


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    k: int = Field(default=10, ge=1, le=50)
    filters: QueryFilters = Field(default_factory=QueryFilters)
    strategy: Strategy | None = None
    rerank: bool | None = None


class SearchHitOut(BaseModel):
    score: float
    chunk: Chunk


class SearchResponse(BaseModel):
    query: str
    hits: list[SearchHitOut]
    trail: list[TrailStep]


def _filters(roles: list[Role], f: QueryFilters) -> SearchFilters:
    return SearchFilters(
        roles=roles,
        document_types=f.document_types,
        environments=f.environments,
        version=f.version,
        sources=f.sources,
        statuses=None if f.include_deprecated else ["active"],
    )


@router.post("/ask", response_model=AnswerResponse)
async def ask(body: AskRequest, roles: Roles, state: State) -> AnswerResponse:
    """Grounded answer with validated citations, or an explicit abstention."""
    svc = state.answers(body.strategy, body.rerank)
    return await svc.ask(body.question, _filters(roles, body.filters))


@router.post("/search", response_model=SearchResponse)
async def search(body: SearchRequest, roles: Roles, state: State) -> SearchResponse:
    """Raw retrieval (no generation) — for the UI's explorer and for evaluation."""
    retriever = state.retriever(body.strategy, body.rerank)
    res = await retriever.retrieve(body.query, _filters(roles, body.filters))
    return SearchResponse(
        query=body.query,
        hits=[SearchHitOut(score=h.score, chunk=h.chunk) for h in res.hits[: body.k]],
        trail=res.trail,
    )
