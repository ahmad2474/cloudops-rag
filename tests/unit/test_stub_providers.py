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


async def test_embedding_is_deterministic_unit_vector_and_term_sensitive() -> None:
    p = StubEmbeddingProvider(dimensions=64)
    a = await p.embed_query("EKS pods Pending")
    b = await p.embed_query("EKS pods Pending")
    c = await p.embed_query("something else entirely")
    near = await p.embed_query("EKS pods stuck Pending")
    assert a == b
    assert len(a) == 64
    assert math.isclose(math.sqrt(sum(x * x for x in a)), 1.0, rel_tol=1e-6)

    def dot(x: list[float], y: list[float]) -> float:
        return sum(i * j for i, j in zip(x, y, strict=True))

    assert dot(a, near) > dot(a, c)


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


async def test_llm_stub_is_extractive_with_citations() -> None:
    p = StubLLMProvider(model="m")
    user = (
        "Sources:\n\n[S1] Doc A — Sec\nFirst sentence here. Second.\n\n"
        "[S2] Doc B\nOther fact. More.\n\n---\nQuestion: q"
    )
    r = await p.generate("sys", user)
    assert "[S1]" in r.text and "[S2]" in r.text
    assert r.model == "m" and r.input_tokens > 0


async def test_llm_stub_abstains_without_sources() -> None:
    r = await StubLLMProvider().generate("sys", "Sources:\n\n(no sources)\n\nQuestion: q")
    assert r.text == "INSUFFICIENT_EVIDENCE"
