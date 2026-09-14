---
document_id: database-platform
title: "Architecture: Database platform (RDS PostgreSQL)"
source: acme
document_type: architecture
environment: production
permissions: [developer, platform-engineer, security-admin]
status: active
created_at: 2025-03-05
updated_at: 2026-04-16
tags: [rds, postgresql, multi-az, rds-proxy, read-replica, backups, parameter-group, pgbouncer]
related: [rds-connection-failure, database-security, postmortem-inc-0952, multi-region-dr]
---
# Architecture: Database platform (RDS PostgreSQL 16)

Owned by DBRE. Terraform `modules/acme-rds`, stack `stacks/acme-prod/us-east-1/data`.
All instances: Multi-AZ, private-data subnets, encrypted (KMS `alias/acme-prod-rds`),
gp3 storage with autoscaling, Performance Insights (7 d), Enhanced Monitoring 15 s.

## Fleet

| Instance | Class | Storage | Connections cap | Extras |
|---|---|---|---|---|
| `prod-ledger-pg` | db.r6g.2xlarge | 4 TB → 6 TB max | 2000 | replica `prod-ledger-pg-ro-1` (reporting reads), logical replication → `prod-reporting-pg` |
| `prod-payments-pg` | db.r6g.xlarge | 1 TB | 1000 | **RDS Proxy** `prod-payments-proxy` (pinning avoided: no session-level `SET`) |
| `prod-identity-pg` | db.r6g.large | 500 GB | 1000 | |
| `prod-reporting-pg` | db.r6g.large | 2 TB | 1000 | subscriber only; writes rejected |

## Connection strategy

- **Payments**: app → RDS Proxy → primary. Proxy `MaxConnectionsPercent=90`,
  `MaxIdleConnectionsPercent=50`, `ConnectionBorrowTimeout=120`. Adopted after INC-0952.
- **Ledger / Identity / Reporting**: app-side pools (HikariCP / pgxpool) sized so
  `replicas × pool ≤ role CONNECTION LIMIT`. Roles: `ledger_app` 900, `identity_app` 300,
  `reporting_app` 200. PgBouncer was evaluated and rejected in favour of RDS Proxy for
  payments; may return for ledger in 2026-H2.
- DNS: `<name>-pg.prod.acme.internal` CNAME → RDS endpoint (TTL 30 s). Clients must honour TTL.

## Parameters (`acme-pg16-prod`)

`max_connections` per table above; `shared_buffers` 25% RAM; `work_mem` 16 MB;
`log_min_duration_statement` 500 ms; `idle_in_transaction_session_timeout` 60 s;
`statement_timeout` 30 s (app roles) / 0 (dbre_admin); `rds.force_ssl` 1.

## Backups & DR

Automated backups 14 d; manual snapshot before every schema migration (`dbre-migrate` tool);
nightly cross-region snapshot copy to us-west-2 (03:00 UTC); PITR tested quarterly
(last: 2026-06-03, RTO 38 min for ledger). See `multi-region-dr` for failover.

## Schema migrations

Flyway via `dbre-migrate` Job in the owning namespace, run from ArgoCD pre-sync hook,
`lock_timeout=5s`, expand/contract pattern mandatory (no `ALTER TABLE … NOT NULL` without
default on big tables — INC-0938).

## Monitoring

Dashboard `RDS / Connections`; alarms: `DatabaseConnections > 80% cap`, `CPUUtilization > 80% 10m`,
`FreeStorageSpace < 15%`, `ReplicaLag > 60s`, `DiskQueueDepth > 20`, `Deadlocks > 0`.
