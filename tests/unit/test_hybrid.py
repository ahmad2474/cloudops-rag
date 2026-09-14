from collections.abc import Sequence

from cloudops_rag.providers.base import RerankedItem, SearchFilters
from cloudops_rag.providers.stub import StubEmbeddingProvider, StubSearchProvider
from cloudops_rag.retrieval import HybridRetriever

ALL = ["developer", "platform-engineer", "security-admin"]


async def test_bm25_stub_matches_exact_technical_tokens(indexed_search: StubSearchProvider) -> None:
    hits = await indexed_search.bm25_search(
        "max_connections", k=5, filters=SearchFilters(roles=ALL)
    )
    assert hits and hits[0].chunk.document_id == "rds-connection-failure"
    none = await indexed_search.bm25_search("zzz-not-a-term", k=5, filters=SearchFilters(roles=ALL))
    assert none == []


async def test_bm25_respects_acl(indexed_search: StubSearchProvider) -> None:
    dev = await indexed_search.bm25_search(
        "acme-breakglass-1", k=5, filters=SearchFilters(roles=["developer"])
    )
    sec = await indexed_search.bm25_search(
        "acme-breakglass-1", k=5, filters=SearchFilters(roles=["security-admin"])
    )
    assert dev == []
    assert sec and sec[0].chunk.document_id == "break-glass-procedure"


async def test_hybrid_rrf_records_fusion_stage_and_merges_sources(
    indexed_search: StubSearchProvider, embedding: StubEmbeddingProvider
) -> None:
    r = HybridRetriever(embedding, indexed_search, strategy="hybrid_rrf", candidates=10, top_k=5)
    res = await r.retrieve("max_connections reserved slots", SearchFilters(roles=ALL))
    stages = [s.stage for s in res.trail]
    assert "vector_search" in stages and "bm25_search" in stages and "fusion" in stages
    fusion = next(s for s in res.trail if s.stage == "fusion")
    assert fusion.detail["method"] == "hybrid_rrf"
    assert res.hits and res.hits[0].chunk.document_id == "rds-connection-failure"
    assert r.label == "hybrid_rrf"


async def test_hybrid_weighted_and_bm25_only_strategies(
    indexed_search: StubSearchProvider, embedding: StubEmbeddingProvider
) -> None:
    w = HybridRetriever(
        embedding,
        indexed_search,
        strategy="hybrid_weighted",
        candidates=10,
        top_k=3,
        vector_weight=0.3,
    )
    res = await w.retrieve("pods Pending IP address", SearchFilters(roles=ALL))
    assert res.hits and res.hits[0].chunk.document_id == "eks-pod-networking"
    b = HybridRetriever(embedding, indexed_search, strategy="bm25", candidates=10, top_k=3)
    res_b = await b.retrieve("pods Pending IP address", SearchFilters(roles=ALL))
    assert res_b.trail[0].stage == "bm25_search"
    assert "embed_query" not in [s.stage for s in res_b.trail]


class _ReverseReranker:
    """Reverses the candidate order — proves the rerank stage actually reorders."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []

    async def rerank(
        self, query: str, documents: Sequence[str], *, top_n: int
    ) -> list[RerankedItem]:
        self.calls.append((query, len(documents)))
        n = len(documents)
        return [RerankedItem(index=i, score=1.0 - i / n) for i in reversed(range(n))][:top_n]


async def test_rerank_stage_reorders_and_limits_pool(
    indexed_search: StubSearchProvider, embedding: StubEmbeddingProvider
) -> None:
    rr = _ReverseReranker()
    base = HybridRetriever(embedding, indexed_search, strategy="vector", candidates=10, top_k=2)
    plain = await base.retrieve("pods Pending IP address", SearchFilters(roles=ALL))
    r = HybridRetriever(
        embedding,
        indexed_search,
        strategy="vector",
        candidates=10,
        top_k=2,
        reranker=rr,
        rerank_candidates=3,
    )
    res = await r.retrieve("pods Pending IP address", SearchFilters(roles=ALL))
    assert rr.calls == [("pods Pending IP address", 3)]
    assert r.label == "vector+rerank"
    assert next(s for s in res.trail if s.stage == "rerank").detail == {"pool": 3}
    assert res.hits[0].chunk.chunk_id != plain.hits[0].chunk.chunk_id
    assert len(res.hits) == 2
