from cloudops_rag.chunking import ChunkingConfig, chunk_document
from cloudops_rag.providers.base import SearchFilters
from cloudops_rag.providers.stub import StubEmbeddingProvider, StubSearchProvider
from cloudops_rag.retrieval import HybridRetriever
from cloudops_rag.retrieval.context_units import build_units
from cloudops_rag.testing import make_doc

ALL = ["developer", "platform-engineer", "security-admin"]


async def _seeded() -> tuple[StubSearchProvider, StubEmbeddingProvider]:
    """One long section → several children under a single parent."""
    paras = [f"Paragraph {i} about topic{i} " + "filler " * 40 for i in range(8)]
    doc = make_doc(
        "long-runbook", "Long runbook", "## Big section\n\n" + "\n\n".join(paras), permissions=ALL
    )
    cd = chunk_document(
        doc, ChunkingConfig(target_tokens=80, max_tokens=120, parent_max_tokens=2000)
    )
    assert len(cd.parents) == 1 and len(cd.chunks) >= 4
    search, emb = StubSearchProvider(), StubEmbeddingProvider(dimensions=256)
    await search.index_chunks(
        cd.chunks, await emb.embed_documents([c.embedding_text for c in cd.chunks])
    )
    await search.index_parents(cd.parents)
    return search, emb


async def test_parent_mode_returns_full_section_once() -> None:
    search, emb = await _seeded()
    r = HybridRetriever(emb, search, strategy="bm25", candidates=10, top_k=3, context_mode="parent")
    res = await r.retrieve("topic3 topic5", SearchFilters(roles=ALL))
    assert len(res.parents) == 1
    assert res.parents[0].parent_id == "long-runbook#000"
    assert "Paragraph 0" in res.parents[0].content and "Paragraph 7" in res.parents[0].content


async def test_child_mode_returns_only_retrieved_chunks() -> None:
    search, emb = await _seeded()
    r = HybridRetriever(emb, search, strategy="bm25", candidates=10, top_k=1, context_mode="child")
    res = await r.retrieve("topic5", SearchFilters(roles=ALL))
    unit = res.parents[0]
    assert "topic5" in unit.content
    assert unit.token_count < 200
    assert unit.parent_id == "long-runbook#000" and len(unit.child_ids) == 1
    assert r.label == "bm25+child"


async def test_child_window_adds_siblings_in_order() -> None:
    search, _ = await _seeded()
    hits = await search.bm25_search("topic5", k=1, filters=SearchFilters(roles=ALL))
    only = await build_units(hits, search, mode="child", window=1)
    win = await build_units(hits, search, mode="child_window", window=1)
    assert len(win) == 1 and len(win[0].child_ids) == 3
    assert win[0].token_count > only[0].token_count
    parent = (await search.get_parents(["long-runbook#000"]))[0]
    idx = [parent.child_ids.index(c) for c in win[0].child_ids]
    assert idx == sorted(idx) and idx[1] - idx[0] == 1


async def test_trail_reports_context_tokens_per_mode() -> None:
    search, emb = await _seeded()
    tokens = {}
    for mode in ("child", "child_window", "parent"):
        r = HybridRetriever(emb, search, strategy="bm25", candidates=10, top_k=1, context_mode=mode)  # type: ignore[arg-type]
        res = await r.retrieve("topic5", SearchFilters(roles=ALL))
        step = next(s for s in res.trail if s.stage == "parent_expansion")
        tokens[mode] = step.detail["context_tokens"]
    assert tokens["child"] < tokens["child_window"] < tokens["parent"]
