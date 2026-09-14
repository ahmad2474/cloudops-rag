from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from cloudops_rag.config import Settings
from cloudops_rag.generation import AnswerService
from cloudops_rag.ingestion.documents import ROLES, Role
from cloudops_rag.providers.registry import Providers
from cloudops_rag.retrieval import VectorRetriever


@dataclass(frozen=True)
class AppState:
    settings: Settings
    providers: Providers
    retriever: VectorRetriever
    answers: AnswerService


def get_state(request: Request) -> AppState:
    state: AppState = request.app.state.ctx
    return state


ROLE_HEADER = "X-Acme-Role"


def get_roles(
    x_acme_role: Annotated[str | None, Header(alias=ROLE_HEADER)] = None,
) -> list[Role]:
    """DEV-ONLY identity: the caller asserts its role in a header.

    Phase 7 replaces this with real authentication (session/JWT → roles). Everything downstream
    already treats roles as the authorization boundary, so only this function changes.
    """
    if not x_acme_role:
        return ["developer"]
    roles: list[Role] = []
    for raw in x_acme_role.split(","):
        r = raw.strip()
        if r not in ROLES:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, f"unknown role {r!r}; expected one of {list(ROLES)}"
            )
        roles.append(r)
    return roles


Roles = Annotated[list[Role], Depends(get_roles)]
State = Annotated[AppState, Depends(get_state)]
