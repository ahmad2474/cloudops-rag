from datetime import date

from cloudops_rag.chunking import ChunkingConfig, chunk_document, count_tokens
from cloudops_rag.chunking.blocks import split_blocks
from cloudops_rag.ingestion.documents import DocumentMetadata
from cloudops_rag.ingestion.parsers.models import ParsedDocument


def _doc(body: str, title: str = "EKS Pod Networking Runbook") -> ParsedDocument:
    meta = DocumentMetadata(
        document_id="eks-pod-networking",
        title=title,
        source="acme",
        document_type="runbook",
        version="1.31",
        permissions=["platform-engineer"],
        created_at=date(2026, 1, 1),
        updated_at=date(2026, 2, 1),
    )
    return ParsedDocument(metadata=meta, body=body, source_path="x.md", content_hash="sha256:abc")


def test_blocks_keep_code_fences_and_tables_atomic() -> None:
    body = (
        "# T\n\npara\n\n```bash\nkubectl get pods\n\n# not a heading\n```\n\n"
        "| a | b |\n|---|---|\n| 1 | 2 |\n"
    )
    kinds = [(b.kind, b.level) for b in split_blocks(body)]
    assert kinds == [("heading", 1), ("paragraph", 0), ("code", 0), ("table", 0)]


def test_h2_sections_become_parents_and_h1_matching_title_is_dropped_from_path() -> None:
    filler = " ".join(f"detail{i}" for i in range(60))
    body = (
        f"# EKS Pod Networking Runbook\n\nIntro text here. {filler}\n\n"
        f"## Symptoms\n\nPods pending. {filler}\n\n### Detail\n\nMore. {filler}\n\n"
        f"## Fix\n\nDo the thing. {filler}\n"
    )
    cd = chunk_document(_doc(body))
    paths = [p.section_path for p in cd.parents]
    assert paths == [[], ["Symptoms"], ["Fix"]]
    sym = cd.parents[1]
    assert "### Detail" in sym.content  # sub-heading stays inside the parent as text
    assert all(c.parent_id in {p.parent_id for p in cd.parents} for c in cd.chunks)
    assert all(cid in {c.chunk_id for c in cd.chunks} for p in cd.parents for cid in p.child_ids)


def test_children_carry_acl_version_and_hash() -> None:
    cd = chunk_document(_doc("## A\n\ntext\n"))
    c = cd.chunks[0]
    assert c.permissions == ["platform-engineer"]
    assert c.version == "1.31"
    assert c.content_hash == "sha256:abc"
    assert c.embedding_text.startswith("EKS Pod Networking Runbook — A\n\n")


def test_large_section_packs_into_multiple_children_without_splitting_code() -> None:
    para = "word " * 150  # ~150 tokens
    code = "```\n" + "\n".join(f"line {i}" for i in range(60)) + "\n```"
    body = "## Big\n\n" + "\n\n".join([para, para, code, para, para])
    cfg = ChunkingConfig(target_tokens=200, max_tokens=400)
    cd = chunk_document(_doc(body), cfg)
    assert len(cd.parents) == 1
    assert len(cd.chunks) >= 3
    code_chunks = [c for c in cd.chunks if "```" in c.content]
    assert len(code_chunks) == 1 and code_chunks[0].content.count("```") == 2
    assert all(c.token_count <= 400 for c in cd.chunks)


def test_oversized_table_is_split_with_header_repeated() -> None:
    rows = "\n".join(f"| r{i} | {'x' * 40} |" for i in range(80))
    body = "## Tbl\n\n| k | v |\n|---|---|\n" + rows + "\n"
    cfg = ChunkingConfig(target_tokens=200, max_tokens=300)
    cd = chunk_document(_doc(body), cfg)
    assert len(cd.chunks) > 1
    for c in cd.chunks:
        assert c.content.startswith("| k | v |\n|---|---|")
        assert count_tokens(c.content) <= 300


def test_document_without_headings_is_one_parent() -> None:
    cd = chunk_document(_doc("just a paragraph\n\nanother\n"))
    assert len(cd.parents) == 1 and cd.parents[0].section_path == []


def test_parent_oversize_splits_into_sequential_parents() -> None:
    body = "## Huge\n\n" + "\n\n".join("sentence " * 120 for _ in range(12))
    cfg = ChunkingConfig(target_tokens=200, max_tokens=300, parent_max_tokens=600)
    cd = chunk_document(_doc(body), cfg)
    assert len(cd.parents) >= 3
    assert all(p.token_count <= 600 + 300 for p in cd.parents)
    assert all(p.section_path == ["Huge"] for p in cd.parents)


def test_tiny_section_merges_into_predecessor() -> None:
    body = "## A\n\n" + "word " * 60 + "\n\n## See also\n\nSee X.\n"
    cd = chunk_document(_doc(body))
    assert len(cd.parents) == 1
    assert "## See also" in cd.parents[0].content
