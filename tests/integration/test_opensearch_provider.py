"""Requires `make up`. Uses its own index prefix so it never touches the real corpus indices."""

from collections.abc import AsyncIterator

import httpx
import pytest

from cloudops_rag.config import Settings
from cloudops_rag.providers.base import SearchFilters
from cloudops_rag.providers.opensearch import OpenSearchProvider
from cloudops_rag.providers.stub import StubEmbeddingProvider
from cloudops_rag.retrieval import VectorRetriever
from cloudops_rag.testing import seed_search

pytestmark = pytest.mark.integration


def _up(url: str) -> bool:
    try:
        return httpx.get(f"{url}/_cluster/health", timeout=2.0).status_code == 200
    except httpx.HTTPError:
        return False


@pytest.fixture
async def provider(settings: Settings) -> AsyncIterator[OpenSearchProvider]:
    if not _up(settings.opensearch_url):
        pytest.skip("OpenSearch not running (make up)")
    p = OpenSearchProvider(settings.opensearch_url, "cloudops-test")
    await p.drop_indices()
    await p.ensure_indices(256)
    await seed_search(p, StubEmbeddingProvider(dimensions=256))
    try:
        yield p
    finally:
        await p.drop_indices()
        await p.close()


async def test_knn_search_applies_acl_filter_inside_query(provider: OpenSearchProvider) -> None:
    emb = StubEmbeddingProvider(dimensions=256)
    q = await emb.embed_query("break-glass sealed envelope acme-breakglass-1")
    dev = await provider.vector_search(q, k=20, filters=SearchFilters(roles=["developer"]))
    sec = await provider.vector_search(q, k=20, filters=SearchFilters(roles=["security-admin"]))
    assert dev and all(h.chunk.document_id != "break-glass-procedure" for h in dev)
    assert any(h.chunk.document_id == "break-glass-procedure" for h in sec)
    assert all("embedding" not in h.chunk.model_dump() for h in dev)


async def test_parent_expansion_and_hashes_and_delete(provider: OpenSearchProvider) -> None:
    hashes = await provider.indexed_document_hashes()
    assert hashes["eks-pod-networking"] == "sha256:eks-pod-networking"
    r = VectorRetriever(StubEmbeddingProvider(dimensions=256), provider, candidates=10, top_k=3)
    res = await r.retrieve(
        "pods Pending failed to assign an IP address", SearchFilters(roles=["developer"])
    )
    assert res.parents and res.parents[0].document_id == "eks-pod-networking"
    assert res.parents[0].child_ids

    before = await provider.stats()
    eks_parents = len({p.parent_id for p in res.parents if p.document_id == "eks-pod-networking"})
    await provider.delete_document("eks-pod-networking")
    await provider.refresh()
    assert "eks-pod-networking" not in await provider.indexed_document_hashes()
    after = await provider.stats()
    assert after["parents"] == before["parents"] - eks_parents
    assert after["chunks"] < before["chunks"]


async def test_metadata_filters_in_opensearch(provider: OpenSearchProvider) -> None:
    emb = StubEmbeddingProvider(dimensions=256)
    q = await emb.embed_query("anything")
    all_roles: list = ["developer", "platform-engineer", "security-admin"]
    pol = await provider.vector_search(
        q, k=20, filters=SearchFilters(roles=all_roles, document_types=["policy"])
    )
    assert {h.chunk.document_type for h in pol} == {"policy"}
    v = await provider.vector_search(
        q, k=20, filters=SearchFilters(roles=all_roles, version="1.31")
    )
    assert {h.chunk.document_id for h in v} == {"eks-pod-networking"}


async def test_bm25_exact_terms_and_hybrid_in_opensearch(provider: OpenSearchProvider) -> None:
    all_roles: list = ["developer", "platform-engineer", "security-admin"]
    hits = await provider.bm25_search(
        "max_connections", k=5, filters=SearchFilters(roles=all_roles)
    )
    assert hits and hits[0].chunk.document_id == "rds-connection-failure"
    dev = await provider.bm25_search(
        "acme-breakglass-1", k=5, filters=SearchFilters(roles=["developer"])
    )
    assert dev == []
    from cloudops_rag.retrieval import HybridRetriever

    r = HybridRetriever(
        StubEmbeddingProvider(dimensions=256),
        provider,
        strategy="hybrid_rrf",
        candidates=10,
        top_k=3,
    )
    res = await r.retrieve("awscni_no_available_ip_addresses", SearchFilters(roles=all_roles))
    assert res.parents and res.parents[0].document_id == "eks-pod-networking"
    assert any(s.stage == "fusion" for s in res.trail)
