import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.dependencies import AppState, State, Who, rate_limited
from cloudops_rag.chunking.models import Chunk
from cloudops_rag.generation.models import AnswerResponse
from cloudops_rag.ingestion.documents import Role
from cloudops_rag.logging import get_logger
from cloudops_rag.observability.records import record_from_answer
from cloudops_rag.providers.base import SearchFilters
from cloudops_rag.retrieval import Strategy
from cloudops_rag.retrieval.context_units import ContextMode
from cloudops_rag.retrieval.models import TrailStep

router = APIRouter(tags=["query"], dependencies=[Depends(rate_limited)])
log = get_logger("api.ask")


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
    context_mode: ContextMode | None = None


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    k: int = Field(default=10, ge=1, le=50)
    filters: QueryFilters = Field(default_factory=QueryFilters)
    strategy: Strategy | None = None
    rerank: bool | None = None
    context_mode: ContextMode | None = None


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
async def ask(body: AskRequest, who: Who, state: State, request: Request) -> AnswerResponse:
    """Grounded answer with validated citations, or an explicit abstention."""
    roles = list(who.roles)
    svc = state.answers(body.strategy, body.rerank, body.context_mode)
    res = await svc.ask(body.question, _filters(roles, body.filters))
    _record(state, request, who.username, roles, body.strategy, res)
    return res


@router.post("/ask/stream")
async def ask_stream(
    body: AskRequest, who: Who, state: State, request: Request
) -> StreamingResponse:
    """Server-sent events: `retrieval` → `delta`* → `done` (validated response)."""
    roles = list(who.roles)
    svc = state.answers(body.strategy, body.rerank, body.context_mode)

    async def gen() -> AsyncIterator[str]:
        async for ev in svc.stream(body.question, _filters(roles, body.filters)):
            if ev["event"] == "done":
                res = AnswerResponse.model_validate(ev["response"])
                _record(state, request, who.username, roles, body.strategy, res)
            yield f"event: {ev['event']}\ndata: {json.dumps(ev)}\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _record(
    state: AppState,
    request: Request,
    user: str,
    roles: list[Role],
    strategy: str | None,
    res: AnswerResponse,
) -> None:
    rec = record_from_answer(
        getattr(request.state, "request_id", "unknown"),
        user,
        roles,
        strategy or state.settings.retrieval_strategy,
        res,
    )
    state.ledger.add(rec)
    log.info("request_record", **rec.model_dump(exclude={"query"}))


@router.post("/search", response_model=SearchResponse)
async def search(body: SearchRequest, who: Who, state: State) -> SearchResponse:
    """Raw retrieval (no generation) — for the UI's explorer and for evaluation."""
    roles = list(who.roles)
    retriever = state.retriever(body.strategy, body.rerank, body.context_mode)
    res = await retriever.retrieve(body.query, _filters(roles, body.filters))
    return SearchResponse(
        query=body.query,
        hits=[SearchHitOut(score=h.score, chunk=h.chunk) for h in res.hits[: body.k]],
        trail=res.trail,
    )
