"""OpenSearch search provider: chunk + parent indices, kNN search with mandatory ACL filter."""

from collections.abc import Sequence
from typing import Any

from opensearchpy import AsyncOpenSearch, NotFoundError
from opensearchpy.helpers import async_bulk

from cloudops_rag.chunking.models import Chunk, ParentChunk
from cloudops_rag.providers.base import SearchFilters, SearchHit

_KEYWORD = {"type": "keyword"}


def chunk_mapping(dimensions: int) -> dict[str, Any]:
    return {
        "settings": {
            "index": {"knn": True, "number_of_shards": 1, "number_of_replicas": 0},
            "analysis": {
                "analyzer": {
                    # Keeps `iam:PassRole`, `aws-node`, `CrashLoopBackOff` as single tokens for
                    # exact-term matching (BM25 uses this in Phase 4).
                    "technical": {
                        "type": "custom",
                        "tokenizer": "whitespace",
                        "filter": ["lowercase"],
                    }
                }
            },
        },
        "mappings": {
            "dynamic": "strict",
            "properties": {
                "chunk_id": _KEYWORD,
                "parent_id": _KEYWORD,
                "document_id": _KEYWORD,
                "position": {"type": "integer"},
                "title": {"type": "text", "analyzer": "english"},
                "source": _KEYWORD,
                "source_url": {"type": "keyword", "index": False},
                "document_type": _KEYWORD,
                "version": _KEYWORD,
                "environment": _KEYWORD,
                "permissions": _KEYWORD,
                "status": _KEYWORD,
                "updated_at": {"type": "date"},
                "content_hash": _KEYWORD,
                "section_path": _KEYWORD,
                "content": {
                    "type": "text",
                    "analyzer": "english",
                    "fields": {"exact": {"type": "text", "analyzer": "technical"}},
                },
                "token_count": {"type": "integer"},
                "embedding": {
                    "type": "knn_vector",
                    "dimension": dimensions,
                    "method": {
                        "name": "hnsw",
                        "space_type": "cosinesimil",
                        "engine": "lucene",
                        "parameters": {"ef_construction": 128, "m": 16},
                    },
                },
            },
        },
    }


def parent_mapping() -> dict[str, Any]:
    return {
        "settings": {"index": {"number_of_shards": 1, "number_of_replicas": 0}},
        "mappings": {
            "dynamic": "strict",
            "properties": {
                "parent_id": _KEYWORD,
                "child_ids": _KEYWORD,
                "document_id": _KEYWORD,
                "title": {"type": "text", "analyzer": "english"},
                "source": _KEYWORD,
                "source_url": {"type": "keyword", "index": False},
                "document_type": _KEYWORD,
                "version": _KEYWORD,
                "environment": _KEYWORD,
                "permissions": _KEYWORD,
                "status": _KEYWORD,
                "updated_at": {"type": "date"},
                "content_hash": _KEYWORD,
                "section_path": _KEYWORD,
                "content": {"type": "text", "index": False},
                "token_count": {"type": "integer"},
            },
        },
    }


def build_filter(filters: SearchFilters) -> list[dict[str, Any]]:
    """The ACL clause is always first and always present (spec §22)."""
    clauses: list[dict[str, Any]] = [{"terms": {"permissions": list(filters.roles)}}]
    if filters.document_types:
        clauses.append({"terms": {"document_type": filters.document_types}})
    if filters.environments:
        clauses.append({"terms": {"environment": [*filters.environments, "all"]}})
    if filters.version:
        clauses.append({"terms": {"version": [filters.version]}})
    if filters.sources:
        clauses.append({"terms": {"source": filters.sources}})
    if filters.statuses:
        clauses.append({"terms": {"status": filters.statuses}})
    if filters.exclude_adversarial:
        clauses.append({"bool": {"must_not": {"term": {"document_type": "adversarial"}}}})
    return clauses


class OpenSearchProvider:
    def __init__(self, url: str, index_prefix: str) -> None:
        self._client = AsyncOpenSearch(hosts=[url], use_ssl=url.startswith("https"))
        self._index_prefix = index_prefix

    @property
    def index_prefix(self) -> str:
        return self._index_prefix

    @property
    def chunks_index(self) -> str:
        return f"{self._index_prefix}-chunks"

    @property
    def parents_index(self) -> str:
        return f"{self._index_prefix}-parents"

    async def ping(self) -> bool:
        try:
            return bool(await self._client.ping())
        except Exception:  # readiness probe must never raise
            return False

    async def close(self) -> None:
        await self._client.close()

    # ---------------------------------------------------------------- indices
    async def ensure_indices(self, dimensions: int) -> None:
        if not await self._client.indices.exists(index=self.chunks_index):
            await self._client.indices.create(
                index=self.chunks_index, body=chunk_mapping(dimensions)
            )
        if not await self._client.indices.exists(index=self.parents_index):
            await self._client.indices.create(index=self.parents_index, body=parent_mapping())

    async def drop_indices(self) -> None:
        for idx in (self.chunks_index, self.parents_index):
            try:
                await self._client.indices.delete(index=idx)
            except NotFoundError:
                pass

    async def indexed_document_hashes(self) -> dict[str, str]:
        if not await self._client.indices.exists(index=self.parents_index):
            return {}
        body = {
            "size": 0,
            "aggs": {
                "docs": {
                    "terms": {"field": "document_id", "size": 10000},
                    "aggs": {"hash": {"terms": {"field": "content_hash", "size": 1}}},
                }
            },
        }
        res = await self._client.search(index=self.parents_index, body=body)
        out: dict[str, str] = {}
        for b in res["aggregations"]["docs"]["buckets"]:
            hashes = b["hash"]["buckets"]
            if hashes:
                out[b["key"]] = hashes[0]["key"]
        return out

    async def delete_document(self, document_id: str) -> None:
        q = {"query": {"term": {"document_id": document_id}}}
        for idx in (self.chunks_index, self.parents_index):
            await self._client.delete_by_query(
                index=idx, body=q, refresh=False, conflicts="proceed"
            )

    async def index_chunks(
        self, chunks: Sequence[Chunk], embeddings: Sequence[Sequence[float]]
    ) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings length mismatch")
        actions = [
            {
                "_index": self.chunks_index,
                "_id": c.chunk_id,
                "_source": {**c.model_dump(mode="json"), "embedding": list(e)},
            }
            for c, e in zip(chunks, embeddings, strict=True)
        ]
        await async_bulk(self._client, actions, refresh=False, raise_on_error=True)

    async def index_parents(self, parents: Sequence[ParentChunk]) -> None:
        actions = [
            {"_index": self.parents_index, "_id": p.parent_id, "_source": p.model_dump(mode="json")}
            for p in parents
        ]
        await async_bulk(self._client, actions, refresh=False, raise_on_error=True)

    async def refresh(self) -> None:
        await self._client.indices.refresh(index=f"{self.chunks_index},{self.parents_index}")

    # ---------------------------------------------------------------- search
    async def vector_search(
        self, embedding: Sequence[float], *, k: int, filters: SearchFilters
    ) -> list[SearchHit]:
        body = {
            "size": k,
            "_source": {"excludes": ["embedding"]},
            "query": {
                "knn": {
                    "embedding": {
                        "vector": list(embedding),
                        "k": k,
                        "filter": {"bool": {"filter": build_filter(filters)}},
                    }
                }
            },
        }
        res = await self._client.search(index=self.chunks_index, body=body)
        return [
            SearchHit(chunk=Chunk.model_validate(h["_source"]), score=float(h["_score"]))
            for h in res["hits"]["hits"]
        ]

    async def bm25_search(self, query: str, *, k: int, filters: SearchFilters) -> list[SearchHit]:
        body = {
            "size": k,
            "_source": {"excludes": ["embedding"]},
            "query": {
                "bool": {
                    "must": {
                        "multi_match": {
                            "query": query,
                            "type": "best_fields",
                            "fields": ["content^1.0", "content.exact^1.5", "title^0.8"],
                            "operator": "or",
                            "tie_breaker": 0.3,
                        }
                    },
                    "filter": build_filter(filters),
                }
            },
        }
        res = await self._client.search(index=self.chunks_index, body=body)
        return [
            SearchHit(chunk=Chunk.model_validate(h["_source"]), score=float(h["_score"]))
            for h in res["hits"]["hits"]
        ]

    async def get_parents(self, parent_ids: Sequence[str]) -> list[ParentChunk]:
        if not parent_ids:
            return []
        res = await self._client.mget(index=self.parents_index, body={"ids": list(parent_ids)})
        found = {
            d["_id"]: ParentChunk.model_validate(d["_source"])
            for d in res["docs"]
            if d.get("found")
        }
        return [found[pid] for pid in parent_ids if pid in found]

    async def stats(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for name, idx in (("chunks", self.chunks_index), ("parents", self.parents_index)):
            if await self._client.indices.exists(index=idx):
                c = await self._client.count(index=idx)
                out[name] = int(c["count"])
            else:
                out[name] = None
        return out
