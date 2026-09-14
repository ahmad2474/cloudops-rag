---
name: rag-evaluation
description: Use when building or running the evaluation suite, computing retrieval/generation metrics, writing benchmark questions, or reporting quality numbers anywhere (README, dashboard, PR).
---

# RAG Evaluation

## Rules
- Evaluation is built **before** retrieval optimisation (Phase 3). Baseline first, then improve.
- Numbers reported anywhere must come from a recorded run in `evaluation/reports/`. No invented or "expected" values in tables.
- Every retrieval strategy is measured on the same dataset with the same seed: vector → BM25 → hybrid → hybrid+rerank → hybrid+rerank+parent-child.

## Dataset (`data/evaluation/dataset.json`)
300+ questions. Each item: `id`, `question`, `category`, `expected_document_ids[]`, `expected_chunk_ids[]` (optional), `expected_answer` (optional), `should_abstain: bool`, `user_role`, `notes`.
Categories: direct_lookup, troubleshooting, multi_document, exact_terminology, version_sensitive, incident_retrieval, conflicting_documents, no_answer, security (unauthorised), prompt_injection.

## Retrieval metrics (`retrieval_metrics.py`)
- Recall@K (K=5,10): fraction of expected docs present in top-K.
- MRR: 1/rank of first relevant.
- NDCG@10: binary gains unless graded relevance is provided.
Compute per-category and overall. Keep implementations pure functions with unit tests against hand-computed examples.

## Generation metrics (`generation_metrics.py`, `citation_metrics.py`)
- Faithfulness / groundedness: every claim supported by cited context (LLM-judge via the configured `LLMProvider`, plus deterministic checks where possible).
- Citation correctness: cited chunk actually contains the supporting text. Citation completeness: important claims have a citation.
- Abstention accuracy: `should_abstain` items abstain; others don't.
- System: p50/p95 latency, tokens, cost/query, error rate — from the observability record, not re-measured.

## Regression gating
CI runs the retrieval suite on retrieval-affecting changes and fails if Recall@5 or MRR drops more than the configured threshold vs. `evaluation/reports/baseline.json`.
