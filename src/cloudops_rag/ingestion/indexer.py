"""Manifest → parse → chunk → embed → index, incrementally by content hash."""

import time
from dataclasses import dataclass, field
from pathlib import Path

from cloudops_rag.chunking import ChunkingConfig, chunk_document
from cloudops_rag.ingestion.documents import Manifest, ManifestEntry
from cloudops_rag.ingestion.parsers import parse_entry
from cloudops_rag.logging import get_logger
from cloudops_rag.observability.pricing import estimate_cost_usd
from cloudops_rag.providers.base import EmbeddingProvider, SearchProvider

log = get_logger(__name__)


@dataclass
class IndexReport:
    indexed: list[str] = field(default_factory=list)
    skipped_unchanged: list[str] = field(default_factory=list)
    skipped_unfetched: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)
    chunks: int = 0
    parents: int = 0
    embed_tokens: int = 0
    seconds: float = 0.0

    def cost_usd(self, embedding_model: str) -> float:
        return estimate_cost_usd(embedding_model, self.embed_tokens)


class Indexer:
    def __init__(
        self,
        embedding: EmbeddingProvider,
        search: SearchProvider,
        *,
        repo_root: Path,
        chunking: ChunkingConfig | None = None,
        batch_size: int = 32,
    ) -> None:
        self._embedding = embedding
        self._search = search
        self._root = repo_root
        self._cfg = chunking or ChunkingConfig()
        self._batch = batch_size

    async def plan(self, manifest: Manifest) -> tuple[list[ManifestEntry], list[str]]:
        """Return (entries to (re)index, document_ids to remove). Pure read; no embedding."""
        current = await self._search.indexed_document_hashes()
        wanted = {e.metadata.document_id: e for e in manifest.documents if e.fetched}
        todo = [e for did, e in wanted.items() if current.get(did) != e.content_hash]
        removed = [did for did in current if did not in wanted]
        return todo, removed

    async def run(
        self, manifest: Manifest, *, full: bool = False, dry_run: bool = False
    ) -> IndexReport:
        t0 = time.perf_counter()
        report = IndexReport()
        await self._search.ensure_indices(self._embedding.dimensions)

        if full:
            todo = [e for e in manifest.documents if e.fetched]
            removed: list[str] = []
        else:
            todo, removed = await self.plan(manifest)
        report.skipped_unfetched = [
            e.metadata.document_id for e in manifest.documents if not e.fetched
        ]
        wanted_ids = {e.metadata.document_id for e in todo}
        report.skipped_unchanged = [
            e.metadata.document_id
            for e in manifest.documents
            if e.fetched and e.metadata.document_id not in wanted_ids
        ]

        for did in removed:
            if not dry_run:
                await self._search.delete_document(did)
            report.removed.append(did)

        for entry in todo:
            did = entry.metadata.document_id
            try:
                chunked = chunk_document(parse_entry(entry, self._root), self._cfg)
            except Exception as exc:
                report.failed[did] = f"parse/chunk: {exc}"
                continue
            if not chunked.chunks:
                report.failed[did] = "empty document after parsing (bad fetch?)"
                continue
            report.chunks += len(chunked.chunks)
            report.parents += len(chunked.parents)
            texts = [c.embedding_text for c in chunked.chunks]
            report.embed_tokens += sum(c.token_count + 20 for c in chunked.chunks)
            if dry_run:
                report.indexed.append(did)
                continue
            try:
                vectors: list[list[float]] = []
                for i in range(0, len(texts), self._batch):
                    vectors.extend(
                        await self._embedding.embed_documents(texts[i : i + self._batch])
                    )
                await self._search.delete_document(did)
                await self._search.index_chunks(chunked.chunks, vectors)
                await self._search.index_parents(chunked.parents)
                report.indexed.append(did)
                log.info("indexed", document_id=did, chunks=len(chunked.chunks))
            except Exception as exc:
                report.failed[did] = f"embed/index: {exc}"
                log.error("index_failed", document_id=did, error=str(exc))
        if not dry_run:
            await self._search.refresh()
        report.seconds = round(time.perf_counter() - t0, 2)
        return report
