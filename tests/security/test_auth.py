import time

import jwt
import pytest
from httpx import AsyncClient

from cloudops_rag.config import Settings
from cloudops_rag.security import AuthError, TokenService, UserStore, hash_password
from cloudops_rag.security.auth import Principal
from tests.security.conftest import SECRET, login

RESTRICTED_Q = {"question": "What are the break-glass user names and envelope holders?"}


async def test_login_issues_token_with_roles_and_me_reflects_it(client: AsyncClient) -> None:
    h = await login(client, "sec")
    me = await client.get("/auth/me", headers=h)
    assert me.json() == {"username": "sec", "roles": ["security-admin"]}


async def test_wrong_password_and_unknown_user_are_indistinguishable(client: AsyncClient) -> None:
    a = await client.post("/auth/login", json={"username": "dev", "password": "nope"})
    b = await client.post("/auth/login", json={"username": "ghost", "password": "nope"})
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


async def test_token_roles_drive_authorization(client: AsyncClient) -> None:
    dev = await client.post("/ask", json=RESTRICTED_Q, headers=await login(client, "dev"))
    sec = await client.post("/ask", json=RESTRICTED_Q, headers=await login(client, "sec"))
    assert all(s["document_id"] != "break-glass-procedure" for s in dev.json()["sources"])
    assert any(s["document_id"] == "break-glass-procedure" for s in sec.json()["sources"])


async def test_tampered_token_is_rejected(client: AsyncClient) -> None:
    h = await login(client, "dev")
    token = h["Authorization"].split()[1]
    payload = jwt.decode(token, options={"verify_signature": False})
    payload["roles"] = ["security-admin"]
    forged = jwt.encode(payload, "attacker-key-attacker-key-attacker-key-00", algorithm="HS256")
    r = await client.post("/ask", json=RESTRICTED_Q, headers={"Authorization": f"Bearer {forged}"})
    assert r.status_code == 401
    unsigned = jwt.encode(payload, "", algorithm="none")  # alg=none attack
    r2 = await client.post(
        "/ask", json=RESTRICTED_Q, headers={"Authorization": f"Bearer {unsigned}"}
    )
    assert r2.status_code == 401


async def test_token_with_unknown_role_is_rejected_even_if_correctly_signed() -> None:
    ts = TokenService(SECRET)
    now = int(time.time())
    bad = jwt.encode(
        {"iss": "cloudops-rag", "sub": "x", "roles": ["root"], "iat": now, "exp": now + 60},
        SECRET,
        algorithm="HS256",
    )
    with pytest.raises(AuthError):
        ts.verify(bad)
    expired = jwt.encode(
        {
            "iss": "cloudops-rag",
            "sub": "x",
            "roles": ["developer"],
            "iat": now - 100,
            "exp": now - 1,
        },
        SECRET,
        algorithm="HS256",
    )
    with pytest.raises(AuthError):
        ts.verify(expired)
    ok = ts.verify(ts.issue(Principal("x", ("developer",))))
    assert ok.roles == ("developer",)


async def test_bearer_token_beats_role_header(client: AsyncClient) -> None:
    """A developer token + a spoofed security-admin header must not escalate."""
    h = {**await login(client, "dev"), "X-Acme-Role": "security-admin"}
    r = await client.post("/ask", json=RESTRICTED_Q, headers=h)
    assert r.status_code == 200
    assert all(s["document_id"] != "break-glass-procedure" for s in r.json()["sources"])


async def test_role_header_is_refused_outside_local_and_test() -> None:
    s = Settings(
        app_env="aws",
        auth_users='{"a": {"password_hash": "$2b$12$x", "roles": ["developer"]}}',
        auth_secret=SECRET,
    )
    assert s.role_header_enabled is False
    assert s.validate_for_environment() == []
    bad = Settings(app_env="aws", auth_users="")
    assert "AUTH_USERS is empty" in "; ".join(bad.validate_for_environment())
    assert "dev default" in "; ".join(bad.validate_for_environment())


def test_user_store_rejects_unknown_roles_and_bad_records() -> None:
    with pytest.raises(AuthError):
        UserStore({"a": {"password_hash": hash_password("x"), "roles": ["root"]}})
    with pytest.raises(AuthError):
        UserStore({"a": {"roles": ["developer"]}})
    with pytest.raises(AuthError):
        UserStore.from_json("{not json")
