from cloudops_rag.config import Settings
from cloudops_rag.providers.opensearch import OpenSearchProvider
from cloudops_rag.providers.registry import build_providers
from cloudops_rag.providers.stub import StubSearchProvider


def test_registry_builds_stub_set() -> None:
    p = build_providers(Settings(embedding_dimensions=256), use_stub_search=True)
    assert p.embedding.dimensions == 256
    assert isinstance(p.search, StubSearchProvider)


async def test_registry_builds_opensearch_search_by_default() -> None:
    p = build_providers(Settings(opensearch_index_prefix="pfx"))
    assert isinstance(p.search, OpenSearchProvider)
    assert p.search.index_prefix == "pfx"
    await p.search.close()
