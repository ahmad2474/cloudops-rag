# Acme Cloud Platform — Canon

This file is the single source of truth for the synthetic enterprise knowledge base.
Every document under `data/synthetic/` must agree with it. It is **not** part of the corpus
(uppercase filename → skipped by the manifest builder). If a document needs a fact that
isn't here, add it here first.

## The company

Acme is a B2B payments company. Its product ("Acme Pay") processes card and bank transfers
for ~4,000 merchant customers. Regulated (PCI-DSS Level 1), so production access and secrets
handling are audited. ~140 engineers.

## Teams

| Team | Owns | Slack | On-call rotation |
|---|---|---|---|
| Platform Engineering (PE) | EKS, VPC, Terraform, CI/CD, observability | `#platform` | `pe-oncall` |
| Database Reliability (DBRE) | RDS fleet, backups, schema migration tooling | `#dbre` | `dbre-oncall` |
| Security Engineering (SecEng) | IAM, Gatekeeper, secrets, audit, incident forensics | `#security` | `sec-oncall` |
| Payments | `payments-api`, `webhook-dispatcher`, `fraud-scoring` | `#team-payments` | `payments-oncall` |
| Ledger | `ledger-service`, `reporting-api` | `#team-ledger` | `ledger-oncall` |
| Identity | `identity-service` | `#team-identity` | `identity-oncall` |
| Growth | `checkout-web`, `notification-worker` | `#team-growth` | `growth-oncall` |
| Data | `data-pipeline` | `#team-data` | `data-oncall` |

Roles used for document permissions: `developer` (any engineer), `platform-engineer`
(PE + DBRE), `security-admin` (SecEng). Permissions are cumulative in practice but each
document lists every role allowed to read it explicitly.

## AWS accounts (AWS Organizations, IAM Identity Center for SSO)

| Account | ID | Purpose |
|---|---|---|
| `acme-prod` | 111111111111 | Production workloads |
| `acme-staging` | 222222222222 | Pre-production, mirrors prod topology at ~25% scale |
| `acme-dev` | 333333333333 | Shared development cluster, ephemeral namespaces |
| `acme-security` | 444444444444 | CloudTrail org trail, GuardDuty, Security Hub, Gatekeeper audit log |
| `acme-shared` | 555555555555 | ECR, Terraform state buckets, ArgoCD, Atlantis, Grafana |

Primary region **us-east-1**; DR region **us-west-2**.

Permission sets: `AcmeReadOnly`, `AcmeDeveloper`, `AcmePlatformAdmin`, `AcmeSecurityAdmin`,
`AcmeBreakGlass`. Nobody has standing write access to `acme-prod`; elevation is via
**Gatekeeper** (internal privileged-access tool, see below).

## Networking

### Production VPC `vpc-prod-use1` — 10.40.0.0/16 (us-east-1)

| Tier | AZ a | AZ b | AZ c | Notes |
|---|---|---|---|---|
| public | 10.40.0.0/24 | 10.40.1.0/24 | 10.40.2.0/24 | NLB/ALB, one NAT Gateway per AZ |
| private-app | 10.40.16.0/20 | 10.40.32.0/20 | 10.40.48.0/20 | EKS nodes (primary ENIs) |
| private-data | 10.40.64.0/24 | 10.40.65.0/24 | 10.40.66.0/24 | RDS, ElastiCache |
| pod (secondary CIDR **100.64.0.0/16**) | 100.64.0.0/18 | 100.64.64.0/18 | 100.64.128.0/18 | VPC CNI custom networking, added Sep 2025 after INC-0981 |

VPC endpoints (interface unless noted): S3 (gateway), DynamoDB (gateway), ECR api+dkr, STS,
CloudWatch Logs, Secrets Manager, KMS, EC2. Flow logs → `acme-prod-vpc-flow-logs` (S3).

Staging `vpc-staging-use1` 10.41.0.0/16 (same layout). Dev `vpc-dev-use1` 10.42.0.0/16.
DR `vpc-prod-usw2` 10.50.0.0/16, peered to prod via Transit Gateway `tgw-acme-core`.

### DNS

Route 53 private zone `acme.internal`. Service names: `<service>.<ns>.svc.cluster.local`
in-cluster; `ledger-pg.prod.acme.internal` etc. for RDS (CNAMEs to RDS endpoints).

## Kubernetes (EKS)

| Cluster | Version | VPC | Purpose |
|---|---|---|---|
| `prod-use1-a` | 1.31 (upgraded from 1.29 on 2025-11-18, from 1.28 on 2025-05-06) | vpc-prod-use1 | production |
| `prod-usw2-a` | 1.31 | vpc-prod-usw2 | DR, warm standby, scaled to 30% |
| `staging-use1-a` | 1.31 | vpc-staging-use1 | staging |
| `dev-use1-a` | 1.32 | vpc-dev-use1 | dev (canary for upgrades) |

Node groups (managed): `system` (m6i.large ×3, taint `CriticalAddonsOnly=true:NoSchedule`),
`general` (m6i.xlarge, min 6 / max 40), `memory` (r6i.2xlarge, min 2 / max 12, taint
`workload=memory:NoSchedule`). **Karpenter** (v1.1) provisions burst capacity via NodePool
`general-spot` since 2026-03 (INC-1042 was the shakedown).

Add-ons: VPC CNI (prefix delegation **enabled** since 2025-09 + custom networking on the
100.64/16 CIDR), CoreDNS (autoscaled, 2 → 8 replicas), kube-proxy, EBS CSI, AWS Load Balancer
Controller, ExternalDNS, cert-manager, External Secrets Operator (→ Secrets Manager),
ArgoCD (in `acme-shared`, app-of-apps), kube-prometheus-stack, Fluent Bit → CloudWatch Logs
(`/acme/prod/eks/<namespace>`), CloudWatch Container Insights.

Namespaces = teams: `payments`, `ledger`, `identity`, `notifications`, `web`, `data`,
`reporting`, `risk`, `platform`, `monitoring`, `argocd` (shared only).

Standards: every workload sets requests **and** limits; PodDisruptionBudgets required for
anything with > 1 replica; readiness probes required; images from `acme-shared` ECR only
(enforced by Kyverno policy `require-acme-ecr`); no `:latest`.

## Databases (RDS PostgreSQL 16, Multi-AZ, private-data subnets)

| Instance | Class | Owner | Notes |
|---|---|---|---|
| `prod-ledger-pg` | db.r6g.2xlarge | Ledger | 4 TB gp3, read replica `prod-ledger-pg-ro-1` |
| `prod-payments-pg` | db.r6g.xlarge | Payments | fronted by **RDS Proxy** `prod-payments-proxy` since INC-0952 (2025-06) |
| `prod-identity-pg` | db.r6g.large | Identity | |
| `prod-reporting-pg` | db.r6g.large | Ledger | fed by logical replication from ledger |

Parameter group `acme-pg16-prod`: `max_connections=2000` (ledger) / `1000` (others),
`log_min_duration_statement=500ms`, `idle_in_transaction_session_timeout=60s`.
Backups: automated 14-day retention, cross-region snapshot copy to us-west-2 nightly 03:00 UTC.
Credentials in Secrets Manager `acme/prod/rds/<instance>/app`, rotated every **90 days**
by Lambda `acme-secret-rotator` (SecEng policy; the older runbook that said 180 days is stale).

## Storage & state

| Bucket | Purpose |
|---|---|
| `acme-prod-terraform-state` (+ DynamoDB `acme-prod-terraform-locks`) | Terraform state, one key per stack |
| `acme-prod-artifacts` | build artifacts, Helm charts |
| `acme-prod-app-logs` | Fluent Bit long-term archive (CloudWatch → S3 after 30 days) |
| `acme-prod-ledger-exports` | nightly ledger exports for reporting; SSE-KMS `alias/acme-prod-ledger` |
| `acme-prod-customer-documents` | KYC documents; SSE-KMS `alias/acme-prod-customer-docs`; Object Lock; **security-admin only** access path |
| `acme-prod-vpc-flow-logs` | VPC flow logs |

All buckets: Block Public Access on, bucket policy denies non-TLS, versioning on.

## Infrastructure as code

Repo `acme-infra` (Terraform **1.12** since 2026-05; was 1.9), provider `aws ~> 5.80`.
Stacks per account/region under `stacks/<account>/<region>/<stack>`. Shared modules
`modules/acme-vpc`, `modules/acme-eks`, `modules/acme-rds`, `modules/acme-s3-secure`.
Plan/apply via **Atlantis** on PR (`atlantis plan` / `atlantis apply`), never from laptops
for prod. State locking via DynamoDB; force-unlock requires PE on-call approval.

## Delivery

GitHub Actions builds → ECR (`555555555555.dkr.ecr.us-east-1.amazonaws.com/<service>`) →
ArgoCD sync (auto-sync staging, manual sync prod). Prod deploy freeze: Fridays after 14:00 UTC
and during declared incidents. Rollback = ArgoCD "rollback to previous revision".
Canary via Argo Rollouts for `payments-api` and `checkout-web` (10% → 50% → 100%, 10 min steps).

## Observability & on-call

Prometheus/Grafana (`grafana.acme.internal`), CloudWatch (alarms → PagerDuty), Fluent Bit logs,
AWS X-Ray for `payments-api`. Dashboards: `EKS / Cluster Overview`, `RDS / Connections`,
`Payments / Golden Signals`.

SLOs: `payments-api` availability 99.95% / p99 < 400 ms; `checkout-web` availability 99.9%;
`ledger-service` p99 < 800 ms; `identity-service` token issuance p99 < 250 ms.

## Incident process

Severities: **SEV-1** customer-facing outage or data risk (page IC + exec), **SEV-2** major
degradation or single-service outage, **SEV-3** minor degradation / internal impact,
**SEV-4** no impact, near miss. Channel `#inc-<id>`; roles: Incident Commander (IC), Comms,
Ops lead. Postmortem within 5 business days for SEV-1/2, blameless. Incident IDs are
`INC-0900`…; the corpus covers **2025-03 → 2026-08**.

## Gatekeeper (privileged access)

Internal tool. Engineer requests a **Privileged Access Workflow (PAW)** session: role
(`AcmePlatformAdmin` / `AcmeSecurityAdmin` / `AcmeBreakGlass`), reason, ticket/incident ID,
duration (max **4 h**, break-glass max **1 h**). Approver: on-call lead of the owning team
(SecEng for break-glass). All sessions recorded to `acme-security` CloudTrail + Slack
`#gatekeeper-audit`. Introduced 2025-02, replacing the 2024 policy that allowed direct
prod SSH with manager approval.

## Landmark incidents referenced across documents

| ID | Date | Sev | Short name |
|---|---|---|---|
| INC-0914 | 2025-04-09 | SEV-2 | pods Pending after node group rotation (taint mismatch) |
| INC-0952 | 2025-06-24 | SEV-1 | payments-pg connection exhaustion → RDS Proxy adopted |
| INC-0981 | 2025-08-19 | SEV-1 | private-app subnet IP exhaustion → custom networking + prefix delegation |
| INC-1007 | 2025-11-18 | SEV-3 | 1.29→1.31 upgrade: PSP removal broke `risk` namespace deploys |
| INC-1042 | 2026-02-11 | SEV-2 | pods Pending, normal CPU/nodes — Karpenter consolidation + ENI limits |
| INC-1063 | 2026-05-07 | SEV-1 | leaked CI token used against `acme-prod-customer-documents` (restricted doc) |
