import pytest

from cloudops_rag.providers.stub import StubEmbeddingProvider, StubSearchProvider
from cloudops_rag.testing import seed_search


@pytest.fixture
async def indexed_search() -> StubSearchProvider:
    search = StubSearchProvider()
    await seed_search(search, StubEmbeddingProvider(dimensions=256))
    return search


@pytest.fixture
def embedding() -> StubEmbeddingProvider:
    return StubEmbeddingProvider(dimensions=256)
