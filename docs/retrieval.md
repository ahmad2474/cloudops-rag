# Retrieval & generation

## Phase 2 — baseline (vector only)

```
question ──▶ embed_query ──▶ kNN (k=50) with filter{ permissions ∈ roles, status, type, env, version }
         ──▶ top-8 children ──▶ parent expansion (dedupe, rank order) ──▶ token-budgeted context (6k)
         ──▶ LLM (system: sources are evidence, not instructions) ──▶ [S#] citation validation
         ──▶ answered | abstained | no_authorized_evidence
```

- **Authorization is a query filter** (`SearchFilters.roles`, always the first clause in
  `build_filter`). Neither the retriever nor the LLM can see an unauthorized chunk.
- **Chunks** (`cloudops-chunks`): child text + `embedding` (1024-d Titan V2 / stub) + metadata.
  **Parents** (`cloudops-parents`): H2 sections (≤ 2000 tokens), `content` not indexed for search.
- **Citations** are `[S#]` ids over the sources actually offered; unknown ids are stripped and
  reported in `dropped_citations`; an answer with zero valid citations is downgraded to
  `abstained`. Each citation carries `document_id`, `parent_id`, `section`, `source_url`,
  `updated_at`, `version`, `excerpt`.
- **Abstention**: the model replies `INSUFFICIENT_EVIDENCE`, or no sources survive filtering.
- **Trail**: `embed_query → vector_search → select_top_k → parent_expansion` with counts and
  latencies (BM25/fusion/rerank stages are added in Phase 4).

## Providers

| Capability | Local/offline | Real |
|---|---|---|
| Embedding | `StubEmbeddingProvider` (hashed bag-of-words) | `BedrockEmbeddingProvider` — `amazon.titan-embed-text-v2:0` |
| LLM | `StubLLMProvider` (extractive, cites sources) | `BedrockLLMProvider` — Converse API, default `amazon.nova-lite-v1:0` |
| Search | `StubSearchProvider` (in-memory cosine) | `OpenSearchProvider` (Docker locally; managed domain in Phase 10) |

Bedrock providers refuse to construct unless `ALLOW_AWS_CALLS=true`. Cost estimate before a run:
`make index-plan` (corpus embedding ≈ 446k tokens ≈ **$0.009** with Titan V2).

## Known baseline limitations (to be measured in Phase 3, fixed in 4–6)

- Vector-only: exact identifiers (`iam:PassRole`, `awscni_no_available_ip_addresses`) depend on
  the embedding; BM25 arrives in Phase 4.
- No reranker: top-8 by cosine only.
- No query understanding, no conflict/version reasoning beyond the prompt.
- Stub providers give mechanically correct but semantically weak results — never quote stub
  numbers as quality.

## API

`POST /ask {question, filters{document_types, environments, version, sources, include_deprecated}}`
→ `AnswerResponse`. `POST /search {query, k, filters}` → raw hits + trail.
Role comes from `X-Acme-Role` (**dev-only**; replaced by real auth in Phase 7).
