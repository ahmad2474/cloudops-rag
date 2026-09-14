# Architecture

See spec §2 (query path), §3 (ingestion), §14 (AWS). This file is expanded as phases land.

## Phase 2 shape

```
apps/web (Next.js) ──HTTP──▶ apps/api (FastAPI: /ask /search /health /ready)
                                 │
                                 ▼
                    src/cloudops_rag ── generation.AnswerService
                                         └─ retrieval.VectorRetriever ── providers.Search (OpenSearch | stub)
                                         └─ providers.Embedding (Titan V2 | stub)
                                         └─ providers.LLM (Bedrock Converse | stub)
apps/ingestion ── manifest → parsers → chunking (parent/child) → Embedding → Search.index_*
```

See `docs/ingestion.md` (corpus) and `docs/retrieval.md` (query path).

Provider selection is by name in `Settings` (`LLM_PROVIDER`, `EMBEDDING_PROVIDER`, …) and resolved
once at startup in `cloudops_rag.providers.registry.build_providers`. Bedrock providers exist from Phase 2 but refuse to construct unless `ALLOW_AWS_CALLS=true`.
