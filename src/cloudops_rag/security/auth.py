"""Password verification and signed session tokens.

- Users: a small in-memory store loaded from configuration (``AUTH_USERS`` JSON). Passwords are
  bcrypt hashes; plaintext never lives in code or config.
- Tokens: HS256 JWTs carrying ``sub`` and ``roles``, short-lived, signed with ``AUTH_SECRET``.
  Roles are validated against the known set on every verification so a forged or stale token
  cannot introduce an unknown role.
"""

import json
import time
from dataclasses import dataclass

import bcrypt
import jwt

from cloudops_rag.errors import CloudOpsRagError
from cloudops_rag.ingestion.documents import ROLES, Role


class AuthError(CloudOpsRagError):
    """Bad credentials, bad token, or unknown role. Never leaks which."""


@dataclass(frozen=True)
class Principal:
    username: str
    roles: tuple[Role, ...]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("ascii")


class UserStore:
    """``{"username": {"password_hash": "...", "roles": ["developer"]}}``"""

    def __init__(self, users: dict[str, dict[str, object]]) -> None:
        self._users: dict[str, tuple[str, tuple[Role, ...]]] = {}
        for name, spec in users.items():
            pw = spec.get("password_hash")
            roles = spec.get("roles")
            if not isinstance(pw, str) or not isinstance(roles, list) or not roles:
                raise AuthError(f"malformed user record for {name!r}")
            for r in roles:
                if r not in ROLES:
                    raise AuthError(f"unknown role {r!r} for user {name!r}")
            self._users[name] = (pw, tuple(roles))

    @classmethod
    def from_json(cls, raw: str) -> "UserStore":
        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError as exc:
            raise AuthError("AUTH_USERS is not valid JSON") from exc
        return cls(data)

    def __len__(self) -> int:
        return len(self._users)

    def authenticate(self, username: str, password: str) -> Principal:
        rec = self._users.get(username)
        # Constant-time-ish: always run bcrypt even for unknown users to avoid user enumeration.
        pw_hash = rec[0] if rec else _DUMMY_HASH
        ok = bcrypt.checkpw(password.encode("utf-8"), pw_hash.encode("ascii"))
        if not rec or not ok:
            raise AuthError("invalid credentials")
        return Principal(username=username, roles=rec[1])


_DUMMY_HASH = hash_password("not-a-real-password")


class TokenService:
    def __init__(
        self, secret: str, *, ttl_seconds: int = 3600, issuer: str = "cloudops-rag"
    ) -> None:
        if len(secret) < 32:
            raise AuthError("AUTH_SECRET must be at least 32 characters")
        self._secret = secret
        self._ttl = ttl_seconds
        self._issuer = issuer

    def issue(self, principal: Principal) -> str:
        now = int(time.time())
        payload = {
            "iss": self._issuer,
            "sub": principal.username,
            "roles": list(principal.roles),
            "iat": now,
            "exp": now + self._ttl,
        }
        return jwt.encode(payload, self._secret, algorithm="HS256")

    def verify(self, token: str) -> Principal:
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=["HS256"],
                issuer=self._issuer,
                options={"require": ["exp", "iat", "sub", "iss"]},
            )
        except jwt.PyJWTError as exc:
            raise AuthError("invalid token") from exc
        roles = payload.get("roles")
        if not isinstance(roles, list) or not roles or any(r not in ROLES for r in roles):
            raise AuthError("invalid token roles")
        return Principal(username=str(payload["sub"]), roles=tuple(roles))
