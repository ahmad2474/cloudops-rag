from pathlib import Path

import pytest

from cloudops_rag.ingestion.manifest import ManifestError, build_manifest

FM = """---
document_id: {id}
title: {title}
source: acme
document_type: {type}
permissions: [platform-engineer]
status: {status}
created_at: 2026-01-01
updated_at: 2026-01-02
{extra}---
# {title}

Body for {id}.
"""


def _write(root: Path, sub: str, doc_id: str, **kw: str) -> None:
    d = root / "data" / "synthetic" / sub
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{doc_id}.md").write_text(
        FM.format(
            id=doc_id,
            title=kw.get("title", doc_id.replace("-", " ").title()),
            type=kw.get("type", "runbook"),
            status=kw.get("status", "active"),
            extra=kw.get("extra", ""),
        )
    )


def test_builds_manifest_from_synthetic_docs(tmp_path: Path) -> None:
    _write(tmp_path, "runbooks", "alpha-runbook")
    _write(tmp_path, "runbooks", "beta-runbook", extra="related: [alpha-runbook]\n")
    m = build_manifest(tmp_path)
    assert m.ids() == {"alpha-runbook", "beta-runbook"}
    entry = next(d for d in m.documents if d.metadata.document_id == "alpha-runbook")
    assert entry.path == "data/synthetic/runbooks/alpha-runbook.md"
    assert entry.content_hash.startswith("sha256:")
    assert entry.word_count > 0


def test_uppercase_files_are_canon_not_corpus(tmp_path: Path) -> None:
    _write(tmp_path, "", "alpha-runbook")
    (tmp_path / "data" / "synthetic" / "WORLD.md").write_text("# canon, no frontmatter\n")
    assert build_manifest(tmp_path).ids() == {"alpha-runbook"}


def test_filename_must_match_document_id(tmp_path: Path) -> None:
    d = tmp_path / "data" / "synthetic"
    d.mkdir(parents=True)
    (d / "wrong-name.md").write_text(
        FM.format(id="alpha", title="Alpha", type="runbook", status="active", extra="")
    )
    with pytest.raises(ManifestError, match="must equal filename stem"):
        build_manifest(tmp_path)


def test_duplicate_ids_across_folders_are_rejected(tmp_path: Path) -> None:
    _write(tmp_path, "runbooks", "same-id")
    _write(tmp_path, "policies", "same-id", type="policy")
    with pytest.raises(ManifestError, match="duplicate document_id"):
        build_manifest(tmp_path)


def test_dangling_related_and_supersedes_are_rejected(tmp_path: Path) -> None:
    _write(tmp_path, "policies", "new-policy", type="policy", extra="supersedes: old-policy\n")
    with pytest.raises(ManifestError, match="supersedes unknown document"):
        build_manifest(tmp_path)


def test_superseded_document_must_be_deprecated(tmp_path: Path) -> None:
    _write(tmp_path, "policies", "old-policy", type="policy", status="active")
    _write(tmp_path, "policies", "new-policy", type="policy", extra="supersedes: old-policy\n")
    with pytest.raises(ManifestError, match="still status: active"):
        build_manifest(tmp_path)
    _write(tmp_path, "policies", "old-policy", type="policy", status="deprecated")
    assert build_manifest(tmp_path).ids() == {"old-policy", "new-policy"}


def test_incident_requires_incident_block(tmp_path: Path) -> None:
    _write(tmp_path, "incidents", "inc-0001", type="incident")
    with pytest.raises(ManifestError, match="need an `incident:` block"):
        build_manifest(tmp_path)


def test_public_registry_entries_are_unfetched_until_raw_exists(tmp_path: Path) -> None:
    _write(tmp_path, "runbooks", "alpha-runbook")
    src = tmp_path / "data" / "sources"
    src.mkdir(parents=True)
    (src / "registry.yaml").write_text(
        """sources:
  - document_id: k8s-pods
    title: Kubernetes Pods
    source: kubernetes
    source_url: https://example.invalid/pods
    document_type: technical_documentation
    permissions: [developer, platform-engineer, security-admin]
    license: CC-BY-4.0
    created_at: 2026-01-01
    updated_at: 2026-01-01
"""
    )
    m = build_manifest(tmp_path)
    pub = next(d for d in m.documents if d.metadata.document_id == "k8s-pods")
    assert pub.fetched is False
    (src / "raw").mkdir()
    (src / "raw" / "k8s-pods.md").write_text("# Pods\n\ncontent\n")
    pub = next(d for d in build_manifest(tmp_path).documents if d.metadata.source == "kubernetes")
    assert pub.fetched is True
    assert pub.path == "data/sources/raw/k8s-pods.md"


def test_comparable_strips_fetch_dependent_fields_for_public_docs_only(tmp_path: Path) -> None:
    from cloudops_rag.ingestion.manifest import comparable

    _write(tmp_path, "runbooks", "alpha-runbook")
    src = tmp_path / "data" / "sources"
    src.mkdir(parents=True)
    (src / "registry.yaml").write_text(
        """sources:
  - document_id: k8s-pods
    title: Kubernetes Pods
    source: kubernetes
    source_url: https://example.invalid/pods
    document_type: technical_documentation
    permissions: [developer]
    license: CC-BY-4.0
    created_at: 2026-01-01
    updated_at: 2026-01-01
"""
    )
    before = comparable(build_manifest(tmp_path))
    (src / "raw").mkdir()
    (src / "raw" / "k8s-pods.md").write_text("# Pods\n\ncontent\n")
    after = comparable(build_manifest(tmp_path))
    assert before == after
    synthetic = next(d for d in after if d["metadata"]["document_id"] == "alpha-runbook")
    assert "content_hash" in synthetic
