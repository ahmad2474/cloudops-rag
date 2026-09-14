from fastapi import APIRouter, Query

from app.dependencies import State, Who
from cloudops_rag.observability.records import RequestRecord

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/requests", response_model=list[RequestRecord])
async def recent_requests(
    state: State, who: Who, n: int = Query(default=50, ge=1, le=500)
) -> list[RequestRecord]:
    """Recent request records (own account only unless platform-engineer/security-admin)."""
    recs = state.ledger.recent(n)
    if "platform-engineer" in who.roles or "security-admin" in who.roles:
        return recs
    return [r for r in recs if r.user == who.username]


@router.get("/summary")
async def summary(state: State, who: Who) -> dict[str, object]:
    return {
        "ledger": state.ledger.summary(),
        "config": {
            "strategy": state.settings.retrieval_strategy,
            "rerank": state.settings.rerank_enabled,
            "context_mode": state.settings.context_mode,
            "llm": f"{state.settings.llm_provider}:{state.settings.llm_model}",
            "embedding": f"{state.settings.embedding_provider}:{state.settings.embedding_model}",
        },
    }
