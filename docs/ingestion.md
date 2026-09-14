# Corpus & ingestion

## Phase 1 — what exists

| Part | Location | Count | Committed? |
|---|---|---:|---|
| Synthetic "Acme Cloud Platform" KB | `data/synthetic/**/*.md` | 115 | yes |
| Public CloudOps docs (pointers) | `data/sources/registry.yaml` | 108 | yes (pointers only) |
| Public docs (raw content) | `data/sources/raw/` | 108 | **no** — fetched by `make corpus-fetch` |
| Manifest | `data/manifest.json` | 223 | yes (`make corpus-check` in CI) |
| Canon | `data/synthetic/WORLD.md` | — | yes (not a corpus document) |

Every document has YAML frontmatter validated by `cloudops_rag.ingestion.documents.DocumentMetadata`
(strict: unknown keys fail). Cross-document rules (`cloudops_rag.ingestion.manifest.cross_check`):
unique `document_id` = filename stem; `related`/`supersedes` must resolve; a superseded document
must be `deprecated`; incidents need an `incident:` block with a unique `INC-####`.

### Synthetic KB by type

runbook 13 · architecture 6 · policy 7 · postmortem 5 · troubleshooting 10 · incident 70 · adversarial 4

Incidents: INC-0900…INC-1099, 2025-03 → 2026-08; SEV-1 ×5, SEV-2 ×24, SEV-3 ×34, SEV-4 ×7.

### Public docs by source

AWS 59 (EC2, VPC, IAM, S3, RDS, EKS, CloudWatch — HTML from docs.aws.amazon.com) ·
Kubernetes 24 (Markdown from `kubernetes/website`, CC-BY-4.0) ·
Terraform 25 (MDX from `hashicorp/web-unified-docs` v1.16, BUSL-1.1).
Licensing per spec §4: nothing public is redistributed; AWS/Terraform content is fetched for
local indexing only.

## Intentionally difficult data (spec §6) — the map

Use this when writing evaluation questions (Phase 3).

| Difficulty | Documents | What a good system must do |
|---|---|---|
| **Duplicate / overlapping** | `kubernetes-crashloop` (runbook) ↔ `crashloopbackoff` (troubleshooting); `rds-connection-failure` ↔ `rds-connection-troubleshooting`; `eks-pod-networking` §B ↔ `karpenter-node-provisioning` | dedupe at parent level; cite one or both without repeating |
| **Outdated, explicitly deprecated** | `eks-pod-networking-1-28` (superseded by `eks-pod-networking`), `eks-cluster-upgrade-1-29` (→ `eks-cluster-upgrade`), `production-access-2024` (→ `production-access`) | prefer the active doc; mention the deprecated one only as history |
| **Conflict between two *active* docs** | `secret-rotation` runbook says **180 days** (updated 2025-04); `secret-management` policy v2.0 says **90 days** (updated 2026-04) and `database-security` agrees | detect the conflict; prefer newer/policy; say so |
| **Version-specific** | EKS 1.28 vs 1.31 runbooks; 1.29 vs 1.31 upgrade runbooks; Terraform 1.9 → 1.12 in `terraform-state-lock-recovery`/`inc-1069` | filter by `version` when the question names one |
| **Same symptom, different causes** | "pods Pending": `inc-0914` (taints), `inc-0981` (subnet exhaustion), `inc-1042` (ENI/max-pods), `inc-0945` (EBS AZ), `inc-0984` (staging max-pods), `inc-1096` (spot + PDB) — routed by `pods-pending` | retrieve the discriminating detail, not just the symptom |
| **Restricted** (`security-admin` only) | `break-glass-procedure`, `production-credential-rotation`, `postmortem-inc-1063`, `inc-1063` | never appear in retrieval for `developer`/`platform-engineer`; abstain, don't leak titles via citations |
| **Restricted** (`platform-engineer`, `security-admin`) | `multi-region-dr`, `security-account-layout`, `eks-cluster-upgrade*`, `terraform-state-lock-recovery`, `terraform-plan-drift`, `inc-0919`, `inc-0958`, `inc-1016`, `inc-1059`, `inc-1098` | same, for `developer` |
| **Prompt injection** (`document_type: adversarial`) | `vendor-advisory-eks-cni` (HTML comment), `runbook-emergency-db-access` (inline "assistant instruction"), `incident-note-injection` (vendor page text), `terraform-tip-hidden-text` (zero-size span) | treat as data; answer the real question; never follow the embedded instruction |
| **No-answer** | nothing about Azure, GCP, Kafka, Istio (explicitly rejected in `eks-architecture`), Redis | abstain rather than improvise |
| **Exact terminology** | `iam:PassRole`, `CrashLoopBackOff`, `aws-node`, `awscni_no_available_ip_addresses`, `ENIConfig`, `max_connections`, `WARM_IP_TARGET`, `force-unlock`, `tags_all`, `ndots` | BM25 must carry these |

## Tooling

```bash
make corpus-fetch      # download public docs (idempotent; --force to refetch)
make corpus-manifest   # validate + write data/manifest.json
make corpus-check      # CI: validate + fail if manifest is stale
```

## Next (Phase 2)

Parsers (Markdown/MDX frontmatter + AWS HTML `main-col-body` extraction), normalisation,
structure-aware chunking, parent/child, embedding, OpenSearch index — using this manifest as
the source of document identity.
