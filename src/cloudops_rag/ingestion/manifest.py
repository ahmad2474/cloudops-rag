"""Build the corpus manifest: every document's identity, location, and content hash.

Two inputs:
- ``data/synthetic/**/*.md`` — Acme documents with YAML frontmatter (committed).
- ``data/sources/registry.yaml`` — curated public pages; raw content lives in
  ``data/sources/raw/`` (gitignored, populated by the fetcher).

Cross-document rules are enforced here (unique ids, dangling ``supersedes``/``related``),
because they can't be checked one file at a time.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from cloudops_rag.errors import CloudOpsRagError
from cloudops_rag.ingestion.documents import (
    DocumentMetadata,
    Manifest,
    ManifestEntry,
    content_hash,
)
from cloudops_rag.ingestion.frontmatter import split_frontmatter


class ManifestError(CloudOpsRagError):
    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        super().__init__("\n".join(problems))


def load_synthetic(root: Path, repo_root: Path) -> tuple[list[ManifestEntry], list[str]]:
    entries: list[ManifestEntry] = []
    problems: list[str] = []
    for path in sorted(root.rglob("*.md")):
        if path.stem.isupper():  # WORLD.md, README.md — canon/notes, not corpus
            continue
        rel = str(path.relative_to(repo_root))
        try:
            raw_meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
            meta = DocumentMetadata.model_validate(raw_meta)
        except (CloudOpsRagError, ValidationError) as exc:
            problems.append(f"{rel}: {exc}")
            continue
        if meta.source != "acme":
            problems.append(f"{rel}: synthetic documents must have source: acme")
        if meta.document_type == "incident" and meta.incident is None:
            problems.append(f"{rel}: incident documents need an `incident:` block")
        if meta.document_type != "incident" and meta.incident is not None:
            problems.append(f"{rel}: only incident documents may carry `incident:`")
        if meta.document_id != path.stem:
            problems.append(f"{rel}: document_id '{meta.document_id}' must equal filename stem")
        entries.append(
            ManifestEntry(
                metadata=meta,
                path=rel,
                content_hash=content_hash(body),
                word_count=len(body.split()),
            )
        )
    return entries, problems


def load_registry(
    registry_path: Path, raw_dir: Path, repo_root: Path
) -> tuple[list[ManifestEntry], list[str]]:
    entries: list[ManifestEntry] = []
    problems: list[str] = []
    if not registry_path.exists():
        return entries, problems
    loaded: Any = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    for item in loaded.get("sources", []):
        try:
            meta = DocumentMetadata.model_validate(item)
        except ValidationError as exc:
            problems.append(f"registry:{item.get('document_id', '?')}: {exc}")
            continue
        if meta.source == "acme":
            problems.append(f"registry:{meta.document_id}: public sources cannot be 'acme'")
        if not meta.source_url:
            problems.append(f"registry:{meta.document_id}: source_url is required")
        if not meta.license:
            problems.append(f"registry:{meta.document_id}: license is required for public docs")
        raw_files = list(raw_dir.glob(f"{meta.document_id}.*")) if raw_dir.exists() else []
        raw_files = [p for p in raw_files if not p.name.endswith(".meta.json")]
        if raw_files:
            body = raw_files[0].read_text(encoding="utf-8", errors="replace")
            entries.append(
                ManifestEntry(
                    metadata=meta,
                    path=str(raw_files[0].relative_to(repo_root)),
                    content_hash=content_hash(body),
                    word_count=len(body.split()),
                    fetched=True,
                )
            )
        else:
            entries.append(
                ManifestEntry(
                    metadata=meta,
                    path=str((raw_dir / f"{meta.document_id}.html").relative_to(repo_root)),
                    content_hash="",
                    word_count=0,
                    fetched=False,
                )
            )
    return entries, problems


def cross_check(entries: list[ManifestEntry]) -> list[str]:
    problems: list[str] = []
    seen: dict[str, str] = {}
    for e in entries:
        did = e.metadata.document_id
        if did in seen:
            problems.append(f"{e.path}: duplicate document_id '{did}' (also {seen[did]})")
        seen[did] = e.path
    ids = set(seen)
    incident_ids: dict[str, str] = {}
    for e in entries:
        m = e.metadata
        if m.supersedes and m.supersedes not in ids:
            problems.append(f"{e.path}: supersedes unknown document '{m.supersedes}'")
        if m.supersedes == m.document_id:
            problems.append(f"{e.path}: document cannot supersede itself")
        for r in m.related:
            if r not in ids:
                problems.append(f"{e.path}: related unknown document '{r}'")
        if m.incident:
            iid = m.incident.incident_id
            if iid in incident_ids:
                problems.append(f"{e.path}: duplicate incident_id {iid} (also {incident_ids[iid]})")
            incident_ids[iid] = e.path
    # A superseded document should not still be active — the conflict must be *detectable*.
    superseded = {e.metadata.supersedes for e in entries if e.metadata.supersedes}
    for e in entries:
        if e.metadata.document_id in superseded and e.metadata.status == "active":
            problems.append(f"{e.path}: is superseded but still status: active (mark deprecated)")
    return problems


def build_manifest(repo_root: Path) -> Manifest:
    synthetic, p1 = load_synthetic(repo_root / "data" / "synthetic", repo_root)
    public, p2 = load_registry(
        repo_root / "data" / "sources" / "registry.yaml",
        repo_root / "data" / "sources" / "raw",
        repo_root,
    )
    entries = synthetic + public
    problems = p1 + p2 + cross_check(entries)
    if problems:
        raise ManifestError(problems)
    return Manifest(
        generated_at=datetime.now(UTC).isoformat(timespec="seconds"),
        documents=sorted(entries, key=lambda e: e.metadata.document_id),
    )


def comparable(manifest: Manifest) -> list[dict[str, Any]]:
    """Manifest entries with fetch-dependent fields stripped from public docs.

    Public content is fetched, not committed, so ``content_hash``/``word_count``/``fetched``
    for those entries differ between a developer machine and CI. Staleness checks compare
    this view; synthetic documents are compared in full.
    """
    out: list[dict[str, Any]] = []
    for e in manifest.documents:
        d = e.model_dump(mode="json")
        if e.metadata.source != "acme":
            for k in ("content_hash", "word_count", "fetched", "path"):
                d.pop(k, None)
        out.append(d)
    return out
