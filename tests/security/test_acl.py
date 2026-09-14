"""Authorization at retrieval time, probed through every pipeline variant and surface."""

import itertools

import pytest
from httpx import AsyncClient

from tests.security.conftest import login

RESTRICTED = "break-glass-procedure"
PROBES = [
    "break-glass sealed envelope passwords",
    "acme-breakglass-1 acme-breakglass-2",
    "Who holds the sealed envelopes?",
    "break-glass procedure",
]
STRATEGIES = ["vector", "bm25", "hybrid_rrf", "hybrid_weighted"]
MODES = ["parent", "child", "child_window"]


@pytest.mark.parametrize("strategy,mode", list(itertools.product(STRATEGIES, MODES)))
async def test_restricted_doc_never_surfaces_for_developer(
    client: AsyncClient, strategy: str, mode: str
) -> None:
    h = await login(client, "dev")
    for q in PROBES:
        ask = await client.post(
            "/ask", json={"question": q, "strategy": strategy, "context_mode": mode}, headers=h
        )
        body = ask.json()
        assert all(s["document_id"] != RESTRICTED for s in body["sources"]), (strategy, mode, q)
        assert all(c["document_id"] != RESTRICTED for c in body["citations"])
        assert "breakglass" not in body["answer"].lower()
        search = await client.post(
            "/search", json={"query": q, "k": 50, "strategy": strategy}, headers=h
        )
        assert all(hit["chunk"]["document_id"] != RESTRICTED for hit in search.json()["hits"])


async def test_platform_engineer_is_also_denied_security_admin_docs(client: AsyncClient) -> None:
    h = await login(client, "pe")
    r = await client.post("/search", json={"query": PROBES[0], "k": 50}, headers=h)
    assert all(hit["chunk"]["document_id"] != RESTRICTED for hit in r.json()["hits"])


async def test_filters_cannot_widen_access(client: AsyncClient) -> None:
    """Metadata filters narrow; they must never bypass the role clause."""
    h = await login(client, "dev")
    for filters in (
        {"document_types": ["policy"]},
        {"include_deprecated": True},
        {"sources": ["acme"]},
        {"environments": ["production", "all"]},
    ):
        r = await client.post(
            "/search", json={"query": PROBES[0], "k": 50, "filters": filters}, headers=h
        )
        assert all(hit["chunk"]["document_id"] != RESTRICTED for hit in r.json()["hits"]), filters


async def test_trail_and_plan_never_carry_restricted_content(client: AsyncClient) -> None:
    h = await login(client, "dev")
    r = await client.post("/ask", json={"question": PROBES[1]}, headers=h)
    text = r.text.lower()
    assert "envelope" not in text.replace("sealed envelope passwords", "")  # only the echoed query
    assert "breakglass-2" not in text.replace("acme-breakglass-1 acme-breakglass-2", "")


async def test_authorized_role_gets_the_document_with_citation(client: AsyncClient) -> None:
    h = await login(client, "sec")
    r = await client.post("/ask", json={"question": PROBES[0]}, headers=h)
    body = r.json()
    assert body["status"] == "answered"
    assert any(c["document_id"] == RESTRICTED for c in body["citations"])
