from cloudops_rag.chunking.models import ParentChunk
from cloudops_rag.generation.citations import to_citation
from cloudops_rag.generation.conflicts import conflict_note, detect_conflicts
from cloudops_rag.generation.evidence import evidence_strength
from cloudops_rag.generation.models import ContextSource
from cloudops_rag.providers.base import SearchHit
from cloudops_rag.retrieval.models import RetrievalResult


def _src(
    sid: str,
    doc: str,
    title: str,
    *,
    version: str | None = None,
    status: str = "active",
    updated: str = "2026-03-01",
) -> ContextSource:
    p = ParentChunk(
        document_id=doc,
        title=title,
        source="acme",
        source_url=None,
        document_type="runbook",
        version=version,
        environment="all",
        permissions=["developer"],
        status=status,
        updated_at=updated,
        content_hash="h",
        section_path=[],
        content="c",
        token_count=1,
        parent_id=f"{doc}#000",
        child_ids=[f"{doc}#000.000"],
    )
    return ContextSource(sid=sid, parent=p, content="c", token_count=1, truncated=False)


def test_version_conflict_prefers_newer() -> None:
    a = _src(
        "S1",
        "eks-pod-networking-1-28",
        "Runbook: EKS pod networking failures (EKS 1.28)",
        version="1.28",
        updated="2025-05-02",
    )
    b = _src(
        "S2",
        "eks-pod-networking",
        "Runbook: EKS pod networking failures (Pending pods)",
        version="1.31",
        updated="2026-03-04",
    )
    c = detect_conflicts([a, b])
    assert len(c) == 1 and c[0].kind == "version" and c[0].preferred == "S2"
    assert "S1" in conflict_note(c) and "prefer S2" in conflict_note(c)


def test_deprecated_source_is_flagged_with_active_replacement() -> None:
    old = _src(
        "S1",
        "production-access-2024",
        "Policy: Production access (2024)",
        status="deprecated",
        updated="2024-11-20",
    )
    new = _src("S2", "production-access", "Policy: Production access (Privileged Access Workflow)")
    c = detect_conflicts([old, new])
    kinds = {x.kind for x in c}
    assert "deprecated" in kinds
    dep = next(x for x in c if x.kind == "deprecated")
    assert dep.preferred == "S2"


def test_stale_pair_flagged_and_unrelated_docs_ignored() -> None:
    a = _src(
        "S1",
        "secret-rotation",
        "Runbook: Rotating application secrets and RDS credentials",
        updated="2025-04-22",
    )
    b = _src("S2", "secret-management", "Policy: Secret management", updated="2026-04-01")
    z = _src(
        "S3", "alb-ingress-502", "Troubleshooting: 502/503/504 from the ALB", updated="2026-06-18"
    )
    c = detect_conflicts([a, b, z], stale_days=300)
    assert [x.kind for x in c] == ["stale"] and c[0].preferred == "S2"
    assert conflict_note([]) == ""


def test_evidence_strength_from_signals() -> None:
    s1, s2 = _src("S1", "d1", "T one"), _src("S2", "d2", "T two")
    hits = [SearchHit(chunk=_chunk("d1"), score=0.9), SearchHit(chunk=_chunk("d2"), score=0.85)]
    ret = RetrievalResult(query="q", hits=hits, parents=[s1.parent, s2.parent], trail=[])
    strong = evidence_strength(
        ret, "Fact one [S1].\n\nFact two [S2].", [to_citation(s1), to_citation(s2)]
    )
    weak = evidence_strength(
        ret, "Fact one [S1].\n\nUnsupported claim.\n\nAnother.", [to_citation(s1)]
    )
    assert strong.score > weak.score and strong.label in ("high", "medium")
    assert weak.signals["citation_coverage"] < 0.5
    assert evidence_strength(ret, "", []).label == "none"


def _chunk(doc: str):  # type: ignore[no-untyped-def]
    from cloudops_rag.chunking.models import Chunk

    return Chunk(
        document_id=doc,
        title="T",
        source="acme",
        source_url=None,
        document_type="runbook",
        version=None,
        environment="all",
        permissions=["developer"],
        status="active",
        updated_at="2026-01-01",
        content_hash="h",
        section_path=[],
        content="c",
        token_count=1,
        chunk_id=f"{doc}#000.000",
        parent_id=f"{doc}#000",
        position=0,
    )
