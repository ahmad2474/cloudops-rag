import math

from cloudops_rag.providers import (
    EmbeddingProvider,
    LLMProvider,
    RerankerProvider,
    SearchProvider,
)
from cloudops_rag.providers.stub import (
    StubEmbeddingProvider,
    StubLLMProvider,
    StubRerankerProvider,
    StubSearchProvider,
)


def test_stubs_satisfy_protocols() -> None:
    assert isinstance(StubEmbeddingProvider(), EmbeddingProvider)
    assert isinstance(StubLLMProvider(), LLMProvider)
    assert isinstance(StubRerankerProvider(), RerankerProvider)
    assert isinstance(StubSearchProvider(), SearchProvider)


async def test_embedding_is_deterministic_unit_vector() -> None:
    p = StubEmbeddingProvider(dimensions=64)
    a = await p.embed_query("EKS pods Pending")
    b = await p.embed_query("EKS pods Pending")
    c = await p.embed_query("something else")
    assert a == b
    assert a != c
    assert len(a) == 64
    assert math.isclose(math.sqrt(sum(x * x for x in a)), 1.0, rel_tol=1e-6)


async def test_embed_documents_matches_embed_query() -> None:
    p = StubEmbeddingProvider(dimensions=32)
    docs = await p.embed_documents(["x", "y"])
    assert docs[0] == await p.embed_query("x")
    assert docs[1] == await p.embed_query("y")


async def test_reranker_orders_by_overlap_then_index() -> None:
    p = StubRerankerProvider()
    out = await p.rerank(
        "subnet ip exhaustion",
        ["unrelated text", "subnet ip exhaustion causes pending pods", "ip subnet"],
        top_n=2,
    )
    assert [i.index for i in out] == [1, 2]
    assert out[0].score == 1.0


async def test_llm_stub_labels_output() -> None:
    p = StubLLMProvider(model="m")
    assert (await p.generate("sys", "hello")).startswith("[stub:m]")
