"""Document catalogue for the console: incidents, explorer, and source viewing.

Backed by data/manifest.json (identity + metadata) and the parsed body on demand. Every
response is filtered by the caller's roles — the same ACL rule as retrieval.
"""

import asyncio
from collections import Counter
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from app.dependencies import Who
from cloudops_rag.ingestion.documents import DocumentMetadata, Manifest, ManifestEntry
from cloudops_rag.ingestion.parsers import parse_entry

router = APIRouter(prefix="/documents", tags=["documents"])
REPO_ROOT = Path(__file__).resolve().parents[4]


@lru_cache(maxsize=1)
def _manifest() -> Manifest:
    return Manifest.model_validate_json((REPO_ROOT / "data" / "manifest.json").read_text())


def _visible(entry: ManifestEntry, roles: Sequence[str]) -> bool:
    return bool(set(entry.metadata.permissions) & set(roles))


class DocumentSummary(BaseModel):
    metadata: DocumentMetadata
    word_count: int
    fetched: bool


class DocumentDetail(DocumentSummary):
    body: str
    related_titles: dict[str, str]


class CatalogueStats(BaseModel):
    total: int
    visible: int
    by_type: dict[str, int]
    by_source: dict[str, int]
    tags: dict[str, int]


@router.get("", response_model=list[DocumentSummary])
async def list_documents(
    who: Who,
    document_type: str | None = Query(default=None),
    source: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    q: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=500, ge=1, le=1000),
) -> list[DocumentSummary]:
    roles = list(who.roles)
    out: list[DocumentSummary] = []
    ql = q.lower() if q else None
    for e in _manifest().documents:
        m = e.metadata
        if not _visible(e, roles):
            continue
        if document_type and m.document_type != document_type:
            continue
        if source and m.source != source:
            continue
        if tag and tag not in m.tags:
            continue
        if ql and ql not in f"{m.title} {m.document_id} {' '.join(m.tags)}".lower():
            continue
        out.append(DocumentSummary(metadata=m, word_count=e.word_count, fetched=e.fetched))
        if len(out) >= limit:
            break
    return out


@router.get("/stats", response_model=CatalogueStats)
async def stats(who: Who) -> CatalogueStats:
    roles = list(who.roles)
    vis = [e for e in _manifest().documents if _visible(e, roles)]
    return CatalogueStats(
        total=len(_manifest().documents),
        visible=len(vis),
        by_type=dict(Counter(e.metadata.document_type for e in vis)),
        by_source=dict(Counter(e.metadata.source for e in vis)),
        tags=dict(Counter(t for e in vis for t in e.metadata.tags).most_common(200)),
    )


@router.get("/{document_id}", response_model=DocumentDetail)
async def get_document(document_id: str, who: Who) -> DocumentDetail:
    roles = list(who.roles)
    by_id = {e.metadata.document_id: e for e in _manifest().documents}
    entry = by_id.get(document_id)
    # Unauthorized and unknown are indistinguishable: never confirm a restricted id exists.
    if entry is None or not _visible(entry, roles):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "document not found")
    if not entry.fetched:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "document content not available")
    parsed = await asyncio.to_thread(parse_entry, entry, REPO_ROOT)
    related = {
        r: by_id[r].metadata.title
        for r in entry.metadata.related
        if r in by_id and _visible(by_id[r], roles)
    }
    return DocumentDetail(
        metadata=entry.metadata,
        word_count=entry.word_count,
        fetched=entry.fetched,
        body=parsed.body,
        related_titles=related,
    )
