from cloudops_rag.providers.base import SearchFilters
from cloudops_rag.providers.stub import StubEmbeddingProvider, StubSearchProvider
from cloudops_rag.retrieval import VectorRetriever

ALL = ["developer", "platform-engineer", "security-admin"]


async def test_vector_retrieval_finds_relevant_parent_and_records_trail(
    indexed_search: StubSearchProvider, embedding: StubEmbeddingProvider
) -> None:
    r = VectorRetriever(embedding, indexed_search, candidates=10, top_k=3)
    res = await r.retrieve(
        "pods Pending failed to assign an IP address", SearchFilters(roles=["developer"])
    )
    assert res.parents
    assert res.parents[0].document_id == "eks-pod-networking"
    assert [s.stage for s in res.trail] == [
        "embed_query",
        "vector_search",
        "select_top_k",
        "parent_expansion",
    ]
    assert res.trail[1].detail["roles"] == ["developer"]


async def test_authorization_is_enforced_at_search_time(
    indexed_search: StubSearchProvider, embedding: StubEmbeddingProvider
) -> None:
    r = VectorRetriever(embedding, indexed_search, candidates=50, top_k=50)
    q = "break-glass sealed envelope passwords acme-breakglass-1"
    dev = await r.retrieve(q, SearchFilters(roles=["developer"]))
    sec = await r.retrieve(q, SearchFilters(roles=["security-admin"]))
    assert all(h.chunk.document_id != "break-glass-procedure" for h in dev.hits)
    assert all(p.document_id != "break-glass-procedure" for p in dev.parents)
    assert any(p.document_id == "break-glass-procedure" for p in sec.parents)


async def test_metadata_filters_narrow_results(
    indexed_search: StubSearchProvider, embedding: StubEmbeddingProvider
) -> None:
    r = VectorRetriever(embedding, indexed_search, candidates=50, top_k=50)
    only_policy = await r.retrieve("anything", SearchFilters(roles=ALL, document_types=["policy"]))
    assert {p.document_type for p in only_policy.parents} == {"policy"}
    v = await r.retrieve("anything", SearchFilters(roles=ALL, version="1.31"))
    assert {p.document_id for p in v.parents} == {"eks-pod-networking"}


async def test_parents_are_deduped_and_ordered_by_best_child(
    indexed_search: StubSearchProvider, embedding: StubEmbeddingProvider
) -> None:
    r = VectorRetriever(embedding, indexed_search, candidates=50, top_k=50)
    res = await r.retrieve("pods Pending IP address subnet", SearchFilters(roles=ALL))
    ids = [p.parent_id for p in res.parents]
    assert len(ids) == len(set(ids))
    assert res.hits[0].chunk.parent_id == ids[0]
