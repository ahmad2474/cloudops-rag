from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from cloudops_rag.config import Settings
from cloudops_rag.providers.stub import StubSearchProvider
from cloudops_rag.testing import seed_search, test_users_json

_USERS = test_users_json()  # bcrypt once per session


@pytest.fixture
def settings() -> Settings:
    return Settings(app_env="test", log_level="WARNING", auth_users=_USERS)


@pytest.fixture
async def client(settings: Settings) -> AsyncIterator[AsyncClient]:
    app = create_app(settings, use_stub_search=True)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


@pytest.fixture
async def seeded_client(settings: Settings) -> AsyncIterator[AsyncClient]:
    app = create_app(settings, use_stub_search=True)
    async with app.router.lifespan_context(app):
        state = app.state.ctx
        search = state.raw_providers.search
        assert isinstance(search, StubSearchProvider)
        await seed_search(search, state.providers.embedding)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c
