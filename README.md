# CloudOps Knowledge Assistant

Production-grade RAG for Cloud & Platform Engineering — hybrid retrieval, semantic reranking,
retrieval-time authorization, citation-grounded generation, first-class evaluation, and a
deliberately designed operations console.

> **Status:** Phases 0–9 complete — corpus, hybrid retrieval + reranking, parent/child context, grounded generation with validated citations, JWT security with retrieval-time ACL, production API, and the **Review Bench** console. Baseline metrics and the AWS deployment wait on Bedrock quota provisioning. See [`docs/PHASES.md`](docs/PHASES.md).
> See [`docs/PHASES.md`](docs/PHASES.md).

## Local development

```bash
make install        # uv sync + pre-commit
make corpus-fetch   # pull public docs (gitignored)
make up             # OpenSearch + Dashboards (Docker)
make index          # parse + chunk + embed + index the corpus (incremental)
make api            # FastAPI on :8000  → /ask, /search, /health, /ready, /docs
make ask Q="why are my EKS pods pending" ROLE=developer
make web-dev        # Next.js on :3000
make check          # lint + typecheck + tests + terraform validate
```

## Layout

| Path | Purpose |
|---|---|
| `src/cloudops_rag/` | Core library: providers, retrieval, chunking, generation, security, evaluation |
| `apps/api/` | FastAPI service — see [`docs/api.md`](docs/api.md) |
| `apps/web/` | Next.js operations console — see [`docs/ui.md`](docs/ui.md), [`DESIGN.md`](DESIGN.md) |
| `apps/ingestion/` | Ingestion jobs |
| `data/` | Synthetic Acme KB (115 docs), public-doc registry (108), manifest — see [`docs/ingestion.md`](docs/ingestion.md) |
| `infrastructure/terraform/` | AWS (Phase 10) |
| `tests/` | unit / integration / retrieval / security / adversarial |

## Results

Populated with real measurements from Phase 3 onward. No numbers here are placeholders.

| Retrieval strategy | Recall@5 | MRR | NDCG |
|---|---:|---:|---:|
| _pending Phase 3_ | | | |
