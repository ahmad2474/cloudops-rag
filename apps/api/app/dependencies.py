from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from cloudops_rag.config import Settings
from cloudops_rag.generation import AnswerService
from cloudops_rag.ingestion.documents import ROLES, Role
from cloudops_rag.logging import get_logger
from cloudops_rag.providers.registry import Providers
from cloudops_rag.retrieval import HybridRetriever, Strategy
from cloudops_rag.retrieval.context_units import ContextMode
from cloudops_rag.retrieval.factory import make_retriever
from cloudops_rag.security import AuthError, Principal, TokenService, UserStore

log = get_logger("api.auth")


@dataclass(frozen=True)
class AppState:
    settings: Settings
    providers: Providers
    users: UserStore
    tokens: TokenService

    def retriever(
        self,
        strategy: Strategy | None = None,
        rerank: bool | None = None,
        context_mode: ContextMode | None = None,
    ) -> HybridRetriever:
        return make_retriever(
            self.providers,
            self.settings,
            strategy=strategy,
            rerank=rerank,
            context_mode=context_mode,
        )

    def answers(
        self,
        strategy: Strategy | None = None,
        rerank: bool | None = None,
        context_mode: ContextMode | None = None,
    ) -> AnswerService:
        return AnswerService(
            self.retriever(strategy, rerank, context_mode),
            self.providers.llm,
            context_token_budget=self.settings.context_token_budget,
            max_tokens=self.settings.llm_max_tokens,
            query_understanding=self.settings.query_understanding,
        )


def get_state(request: Request) -> AppState:
    state: AppState = request.app.state.ctx
    return state


ROLE_HEADER = "X-Acme-Role"


def get_principal(
    state: Annotated[AppState, Depends(get_state)],
    authorization: Annotated[str | None, Header()] = None,
    x_acme_role: Annotated[str | None, Header(alias=ROLE_HEADER)] = None,
) -> Principal:
    """Identity for the request.

    Order: Bearer token (always) → X-Acme-Role header (local runs only) → 401.
    Roles from either path are validated against the known set; the token path is the real one.
    """
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "malformed Authorization header")
        try:
            return state.tokens.verify(token)
        except AuthError as exc:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid or expired token") from exc

    if x_acme_role is not None:
        if not state.settings.role_header_enabled:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "authentication required")
        roles: list[Role] = []
        for raw in x_acme_role.split(","):
            r = raw.strip()
            if r not in ROLES:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"unknown role {r!r}; expected one of {list(ROLES)}",
                )
            roles.append(r)
        log.debug("dev_role_header", roles=roles)
        return Principal(username=f"dev:{'+'.join(roles)}", roles=tuple(roles))

    if state.settings.role_header_enabled:
        return Principal(username="dev:developer", roles=("developer",))
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "authentication required")


def get_roles(principal: Annotated[Principal, Depends(get_principal)]) -> list[Role]:
    return list(principal.roles)


Roles = Annotated[list[Role], Depends(get_roles)]
Who = Annotated[Principal, Depends(get_principal)]
State = Annotated[AppState, Depends(get_state)]
