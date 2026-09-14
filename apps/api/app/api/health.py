from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel

from app.dependencies import AppState, get_state
from cloudops_rag import __version__
from cloudops_rag.logging import get_logger

log = get_logger("api.health")

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok"]
    version: str


class ReadyResponse(BaseModel):
    status: Literal["ready", "degraded"]
    search: bool
    index: dict[str, int | None]
    providers: dict[str, str]


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness: the process is up. Never touches dependencies."""
    return HealthResponse(status="ok", version=__version__)


@router.get("/ready", response_model=ReadyResponse)
async def ready(
    state: Annotated[AppState, Depends(get_state)], response: Response
) -> ReadyResponse:
    """Readiness: dependencies reachable. 503 if the search backend is down."""
    search_ok = await state.providers.search.ping()
    index: dict[str, int | None] = {"chunks": None, "parents": None}
    if search_ok:
        try:
            index = await state.providers.search.stats()
        except Exception as exc:  # stats are best-effort; readiness is about reachability
            log.warning("ready_stats_failed", error=str(exc))
    healthy = search_ok and bool(index.get("chunks"))
    if not search_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    s = state.settings
    return ReadyResponse(
        status="ready" if healthy else "degraded",
        search=search_ok,
        index=index,
        providers={
            "llm": f"{s.llm_provider}:{s.llm_model}",
            "embedding": f"{s.embedding_provider}:{s.embedding_model}",
            "reranker": s.reranker_provider,
            "search": s.search_provider,
        },
    )
