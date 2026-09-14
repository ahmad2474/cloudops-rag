# Retrieval & generation

## Phase 4 — hybrid retrieval + reranking

```
question ─┬─▶ embed_query ─▶ kNN (k=50, filtered) ──┐
          └─▶ BM25 multi_match (k=50, filtered) ──┤─▶ fusion (RRF k=60 | weighted min-max)
                                                   ─▶ rerank top-20 (Cohere Rerank 3.5) ─▶ top-8
                                                   ─▶ parent expansion ─▶ context ─▶ LLM
```

- `RETRIEVAL_STRATEGY` ∈ `vector | bm25 | hybrid_rrf | hybrid_weighted`; `RERANK_ENABLED`
  toggles the Cohere stage. Both can be overridden per request (`strategy`, `rerank` fields on
  `/ask` and `/search`) and per eval run (`--strategy`, `--rerank`).
- **BM25** queries `content` (english analyzer), `content.exact` (whitespace analyzer, boost 1.5 —
  keeps `iam:PassRole`, `aws-node`, `awscni_no_available_ip_addresses` as single tokens) and
  `title`, with the identical ACL/metadata filter clauses as kNN.
- **Fusion** (`retrieval/fusion.py`, unit-tested against hand-computed values): RRF
  `Σ 1/(k+rank)`; weighted = convex combination of per-source min-max-normalised scores. Raw
  cosine and BM25 scores are never averaged directly.
- **Rerank**: fused top-20 child texts → Cohere Rerank 3.5 → top-8. Billed per query
  ($2 / 1,000). Requires the IAM policy to allow `cohere.rerank-v3-5:0` (currently Amazon-only —
  to be added when quotas are provisioned) and a one-time Marketplace enablement by an admin.
- Trail stages: `embed_query, vector_search, bm25_search, fusion{method, overlap}, rerank{pool},
  select_top_k, parent_expansion`.

## Phase 6 — generation: query understanding, conflicts, evidence strength

```
question ─▶ plan_query (rules; optional LLM decomposition) ─▶ retrieve[_many] ─▶ context
         ─▶ detect_conflicts (metadata) ─▶ prompt (+version hint, +source notes) ─▶ LLM
         ─▶ validate citations ─▶ evidence_strength ─▶ AnswerResponse
```

- **Query plan** (`generation/query.py`): strips "ignore your instructions…" preambles from the
  *question* (recorded as `stripped_injection`), extracts a version hint (`EKS 1.31`), incident
  ids, and a document-type hint. `QUERY_UNDERSTANDING=llm` additionally asks the model to split
  multi-part questions into 2–4 subqueries; results are merged by RRF (`merge_subqueries` trail step).
- **Conflicts** (`generation/conflicts.py`): sources on the same topic (title-word containment ≥ 0.5)
  are flagged when they differ in `version`, when one is `deprecated`, or when `updated_at` differs
  by ≥ 1 year. The prompt gets a one-line "source note" naming the preferred source; the response
  carries `conflicts[]` for the UI. Detection uses metadata only — never the content.
- **Evidence strength** (`generation/evidence.py`, spec §28): `0.5·citation_coverage +
  0.35·distinct_docs/3 + 0.15·(1 − top-2 score margin)` → high / medium / low / none. Reported in
  `AnswerResponse.evidence` with its raw signals; it is not a model confidence.
- Response also includes `query_plan` so the UI can show what was actually searched.

## Phase 5 — parent-child context modes

Retrieval always ranks **children** (precision). `CONTEXT_MODE` decides what reaches the model:

| mode | unit handed to the context builder | avg tokens for top-20 children (stub run) |
|---|---|---:|
| `child` | the retrieved chunk(s) only, grouped per parent | ~5.1k |
| `child_window` | chunk ± `CONTEXT_WINDOW` siblings within the parent, in document order | ~8.3k |
| `parent` (default) | the whole H2 section, deduped, best-child order | ~10.8k |

Units keep the real `parent_id`/`child_ids`, so citations resolve identically in every mode.
Per-request override: `context_mode` on `/ask` and `/search`; per run: `--context-mode`.
The trail's `parent_expansion` step reports `mode`, `units`, `context_tokens`.

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
