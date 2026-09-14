from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.dependencies import State, Who
from cloudops_rag.security import AuthError

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105
    expires_in: int
    roles: list[str]


class MeResponse(BaseModel):
    username: str
    roles: list[str]


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, state: State) -> TokenResponse:
    try:
        principal = state.users.authenticate(body.username, body.password)
    except AuthError as exc:
        # Same status and message for unknown user / wrong password (no enumeration).
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials") from exc
    return TokenResponse(
        access_token=state.tokens.issue(principal),
        expires_in=state.settings.auth_token_ttl_seconds,
        roles=list(principal.roles),
    )


@router.get("/me", response_model=MeResponse)
async def me(who: Who) -> MeResponse:
    return MeResponse(username=who.username, roles=list(who.roles))
