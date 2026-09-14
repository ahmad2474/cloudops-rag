# Phase tracker

Spec: `RAG_Project_Master_Implementation_Plan_v1.0.md` §41–51, §65.
Work stops at the end of each phase for review. Do not auto-advance.

| # | Phase | Status | Exit criteria |
|---|---|---|---|
| 0 | Foundation | **done** | monorepo, Docker Compose (OpenSearch), FastAPI + Next.js skeletons, provider abstraction, lint/test/CI green, no AWS |
| 1 | Corpus | **done** | curated AWS/K8s/Terraform docs, synthetic Acme KB, 50–100 incidents, manifest + hashes + versions |
| 2 | Baseline RAG | **done** (stub-verified; real Bedrock run pending credentials + cost approval) | ingestion → chunking → embedding → OpenSearch → vector retrieval → LLM → citation |
| 3 | Evaluation | **tooling done; baseline run pending Bedrock entitlement** | 300+ questions, baseline Recall@K/MRR/NDCG/faithfulness/citation/latency/cost recorded |
| 4 | Retrieval engineering | **done** (benchmarks pending Bedrock) | BM25 + hybrid fusion (RRF & weighted) + metadata filters + reranking, each benchmarked |
| 5 | Parent-child | **done** (context modes measurable; generation comparison pending Bedrock) | child retrieval → parent expansion → context assembly, benchmarked |
| 6 | Generation | **done** | query understanding, citation enforcement, abstention, conflict detection |
| 7 | Security | **done** | auth, roles, ACL filtering at search time, injection defense, adversarial tests |
| 8 | Production API | **next** | request IDs, structured logs, timeouts, retries, rate limiting, streaming, health |
| 9 | UI | pending | Search/Answer, Sources, Incidents, Explorer, Evaluation, System status |
| 10 | AWS (Terraform) | pending | S3, OpenSearch t3.small, EC2, IAM, CloudWatch, Bedrock perms — plan → cost → approve → apply |
| 11 | AWS demo | pending | ingest, benchmark, security + load tests, metrics, demo video, **destroy** |
