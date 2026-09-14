# Evaluation

Spec §19–21, §43. **Numbers in this repo come from recorded runs in `evaluation/reports/`; nothing
is estimated or copied from elsewhere.** Stub-provider runs are never reported as quality.

## Dataset — `data/evaluation/dataset.json` (v1.0, 315 questions)

Authored by hand in `apps/evaluation/build_dataset.py` against the corpus; relevance is judged at
**document** level so results survive chunker changes. Every referenced id is validated against
`data/manifest.json`.

| Category | n | What it tests |
|---|---:|---|
| direct_lookup | 42 | a fact stated in one document (policies, architecture, public docs) |
| troubleshooting | 40 | symptom → runbook / troubleshooting page |
| multi_document | 25 | answer needs 2–5 documents |
| exact_terminology | 32 | identifiers: `iam:PassRole`, `awscni_no_available_ip_addresses`, `tags_all`… |
| version_sensitive | 20 | EKS 1.28 vs 1.31, Terraform 1.9 vs 1.12, policy versions |
| incident_retrieval | 80 | one per incident (70) + cross-incident queries (10) |
| conflicting_documents | 15 | deprecated vs active, runbook 180 d vs policy 90 d |
| no_answer | 25 | Azure, Istio, Kafka, Redis, HR… → must abstain |
| security | 24 | 12 restricted questions × {developer → abstain + never surface, authorized role → answer} |
| prompt_injection | 12 | questions that retrieve the adversarial docs; answer must not obey them |

Fields: `expected_document_ids`, `should_abstain`, `role`, `must_not_cite`, `answer_must_contain`,
`answer_must_not_contain`.

## Metrics (`cloudops_rag.evaluation.metrics`, unit-tested against hand-computed values)

- Retrieval (non-abstain items): **Recall@5, Recall@10, MRR, NDCG@10** over deduplicated document
  ranking of the top-20 children.
- **ACL violations**: any `must_not_cite` document appearing in retrieval — must be 0 always.
- Generation: **abstention accuracy** (`should_abstain` ⇔ status ≠ answered), **citation
  precision/recall** (cited docs vs expected), **citation violations**, content checks,
  **injection success rate** (answer contains a forbidden phrase), **faithfulness** (LLM-judge:
  supported claims / claims; only with a real LLM).
- System: retrieval/generation p50/p95 latency, tokens, cost per query.

## Running

```bash
make eval                     # retrieval only — query embeddings only, ≈ $0.001 with Titan
make eval-full                # + generation + judge — a few hundred Nova Lite calls
uv run python apps/evaluation/run.py --strategy hybrid --gate evaluation/reports/<baseline>.json
```

`--gate` fails (exit 2) if Recall@5 or MRR drops more than `--threshold` (0.02) vs the baseline —
this is the CI regression check for retrieval changes (Phase 4+).

## Results

_Pending the first Bedrock run (account entitlement)._ Table to be filled from
`evaluation/reports/`:

| Strategy | Recall@5 | Recall@10 | MRR | NDCG@10 | ACL viol. |
|---|---:|---:|---:|---:|---:|
| Vector (baseline) | | | | | |
