"""A seeded API client with real auth. Shared by tests/security and tests/adversarial."""

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from cloudops_rag.config import Settings
from cloudops_rag.providers.stub import StubSearchProvider
from cloudops_rag.testing import TEST_PASSWORD, seed_search, test_users_json

_USERS = test_users_json()
SECRET = "unit-test-secret-that-is-at-least-32-characters-long"


@pytest.fixture
def settings() -> Settings:
    return Settings(app_env="test", log_level="WARNING", auth_users=_USERS, auth_secret=SECRET)


@pytest.fixture
async def client(settings: Settings) -> AsyncIterator[AsyncClient]:
    app = create_app(settings, use_stub_search=True)
    async with app.router.lifespan_context(app):
        state = app.state.ctx
        assert isinstance(state.providers.search, StubSearchProvider)
        await seed_search(state.providers.search, state.providers.embedding)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c


async def login(client: AsyncClient, user: str) -> dict[str, str]:
    r = await client.post("/auth/login", json={"username": user, "password": TEST_PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
