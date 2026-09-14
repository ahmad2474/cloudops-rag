---
name: rag-retrieval
description: Use when implementing or modifying any retrieval code — dense/vector search, BM25, hybrid fusion, reranking, parent-child expansion, metadata/ACL filtering, or OpenSearch index mappings.
---

# RAG Retrieval

## Non-negotiables
- Final architecture = dense + BM25 + hybrid fusion + metadata filters + reranker + parent-child expansion. Vector-only is a *baseline*, never the end state.
- Authorization filter (`permissions` terms query) is applied **inside** the search request, for both the BM25 and the kNN branch. Never filter after retrieval.
- Every retrieval change is benchmarked with `evaluation/runner.py` before it is merged. Report Recall@5/10, MRR, NDCG vs. the previous run.

## OpenSearch conventions
- One index for chunks (`{prefix}-chunks`), one for parents (`{prefix}-parents`). Chunk docs carry `parent_id`, `document_id`, `permissions[]`, `document_type`, `environment`, `version`, `section_path[]`, `source_url`, `content_hash`.
- kNN field: `embedding` (`knn_vector`, dimension from `EMBEDDING_DIMENSIONS`, `hnsw`, cosine). Text field: `content` with the `english` analyzer, plus `content.exact` (`keyword`-ish or `standard` analyzer) so terms like `CrashLoopBackOff`, `iam:PassRole`, `aws-node` match exactly.
- Candidate budget: ~50–100 per branch → fuse → top 20 → rerank → top 5–8.

## Fusion
- Implement **Reciprocal Rank Fusion** (`k=60` default) and **weighted score fusion** (min-max normalised). Both are selectable via config; both get evaluated; the README table shows the numbers.
- Never average raw BM25 and cosine scores — they are on different scales.

## Parent-child
- Retrieve children (precise), expand to parents (context), dedupe parents, then token-budget the context window. Preserve rank order from the reranker when assembling.

## Interfaces
Code against `SearchProvider`, `EmbeddingProvider`, `RerankerProvider` Protocols in `src/cloudops_rag/providers/`. Tests use the in-memory/stub providers; integration tests use Docker OpenSearch.

## Query understanding
Rewrite/decompose is a separate step before retrieval, logged in the retrieval trail. Keep it cheap; don't hide it.
