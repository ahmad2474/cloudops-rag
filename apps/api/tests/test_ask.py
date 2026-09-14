from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from cloudops_rag.config import Settings
from cloudops_rag.providers.stub import StubSearchProvider
from cloudops_rag.testing import seed_search


@pytest.fixture
async def seeded_client(settings: Settings) -> AsyncIterator[AsyncClient]:
    app = create_app(settings, use_stub_search=True)
    async with app.router.lifespan_context(app):
        state = app.state.ctx
        search = state.providers.search
        assert isinstance(search, StubSearchProvider)
        await seed_search(search, state.providers.embedding)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c


async def test_ask_returns_grounded_answer_with_citations(seeded_client: AsyncClient) -> None:
    r = await seeded_client.post(
        "/ask", json={"question": "Why are pods Pending with failed to assign an IP address?"}
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "answered"
    assert body["citations"][0]["document_id"] == "eks-pod-networking"
    assert body["citations"][0]["section"]
    assert [s["stage"] for s in body["trail"]][:2] == ["embed_query", "vector_search"]
    assert body["usage"]["model"]


async def test_ask_respects_role_header_for_restricted_docs(seeded_client: AsyncClient) -> None:
    q = {"question": "What are the break-glass user names and envelope holders?"}
    dev = await seeded_client.post("/ask", json=q, headers={"X-Acme-Role": "developer"})
    sec = await seeded_client.post("/ask", json=q, headers={"X-Acme-Role": "security-admin"})
    assert all(s["document_id"] != "break-glass-procedure" for s in dev.json()["sources"])
    assert any(s["document_id"] == "break-glass-procedure" for s in sec.json()["sources"])


async def test_unknown_role_is_rejected(seeded_client: AsyncClient) -> None:
    r = await seeded_client.post(
        "/ask", json={"question": "x y z"}, headers={"X-Acme-Role": "root"}
    )
    assert r.status_code == 400


async def test_search_endpoint_returns_hits_without_generation(seeded_client: AsyncClient) -> None:
    r = await seeded_client.post("/search", json={"query": "max_connections FATAL", "k": 3})
    assert r.status_code == 200
    body = r.json()
    assert body["hits"] and "embedding" not in body["hits"][0]["chunk"]
    assert body["hits"][0]["chunk"]["document_id"] == "rds-connection-failure"


async def test_filters_produce_no_evidence_status(seeded_client: AsyncClient) -> None:
    r = await seeded_client.post(
        "/ask", json={"question": "anything at all", "filters": {"document_types": ["postmortem"]}}
    )
    assert r.json()["status"] == "no_authorized_evidence"
