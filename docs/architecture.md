# Architecture

See spec §2 (query path), §3 (ingestion), §14 (AWS). This file is expanded as phases land.

## Phase 0 shape

```
apps/web (Next.js)  ──HTTP──▶  apps/api (FastAPI)  ──▶  src/cloudops_rag (library)
                                                          └─ providers/  Embedding | LLM | Reranker | Search
                                                                          stub     | stub | stub     | OpenSearch (Docker)
```

Provider selection is by name in `Settings` (`LLM_PROVIDER`, `EMBEDDING_PROVIDER`, …) and resolved
once at startup in `cloudops_rag.providers.registry.build_providers`. Requesting `bedrock` raises at
startup until Phase 2 implements it — Phases 0–9 make no AWS calls.
