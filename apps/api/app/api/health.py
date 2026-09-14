from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel

from app.dependencies import AppState, get_state
from cloudops_rag import __version__

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok"]
    version: str


class ReadyResponse(BaseModel):
    status: Literal["ready", "degraded"]
    search: bool
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
    if not search_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    s = state.settings
    return ReadyResponse(
        status="ready" if search_ok else "degraded",
        search=search_ok,
        providers={
            "llm": f"{s.llm_provider}:{s.llm_model}",
            "embedding": f"{s.embedding_provider}:{s.embedding_model}",
            "reranker": s.reranker_provider,
            "search": s.search_provider,
        },
    )
