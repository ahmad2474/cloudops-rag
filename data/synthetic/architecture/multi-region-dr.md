---
document_id: multi-region-dr
title: "Architecture: Multi-region disaster recovery (us-east-1 → us-west-2)"
source: acme
document_type: architecture
environment: production
permissions: [platform-engineer, security-admin]
status: active
created_at: 2025-06-15
updated_at: 2026-06-05
tags: [dr, multi-region, failover, route53, rds, snapshots, rto, rpo]
related: [production-vpc, database-platform, eks-architecture, incident-response]
---
# Architecture: Multi-region DR (us-east-1 → us-west-2)

Strategy: **warm standby**. Targets: RTO 60 min, RPO 15 min (ledger), 24 h (reporting).
Scope is **AWS only** — there is no Azure/GCP footprint and no plan for one.

## What exists in us-west-2 (`acme-prod`)

- `vpc-prod-usw2` 10.50.0.0/16, same tiering; no NAT-heavy workloads.
- `prod-usw2-a` EKS 1.31 at 30% of prod node capacity; ArgoCD keeps app versions in lockstep;
  HPA `minReplicas` lower via a `dr` values overlay.
- RDS: nightly cross-region **snapshot copies** for all instances + **cross-region read replica**
  `prod-ledger-pg-usw2` (async, lag typically < 5 s) for ledger only. Payments/identity rely
  on snapshots (RPO up to 24 h) — accepted risk, review 2026-Q4.
- S3: CRR from `acme-prod-ledger-exports` and `acme-prod-customer-documents` to `-usw2` buckets.
- Secrets Manager replication for `acme/prod/*`.
- Route 53 health-checked failover records for `api.acmepay.com` and `checkout.acmepay.com`.

## Failover procedure (summary; full steps in `dr-failover` change template)

1. Declare SEV-1, IC confirms us-east-1 is unrecoverable within RTO.
2. Promote `prod-ledger-pg-usw2` (`aws rds promote-read-replica`) — ~10 min. Restore
   payments/identity from latest snapshot copy (~25 min each, parallel).
3. Update `*.prod.acme.internal` CNAMEs to us-west-2 endpoints (Terraform `dr=true`).
4. Scale `prod-usw2-a` node groups and Karpenter limits to 100%.
5. Flip Route 53 failover (health check already failing → automatic; manual override available).
6. Comms: statuspage + merchant email.

## Testing

Game-day twice a year (last 2026-04-22: RTO achieved 52 min; gap: ESO in usw2 pointed at
us-east-1 Secrets Manager endpoint — fixed).

## Explicit non-goals

Active-active; cross-cloud DR; per-merchant region pinning.
