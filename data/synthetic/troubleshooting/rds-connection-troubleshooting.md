---
document_id: rds-connection-troubleshooting
title: "Troubleshooting: RDS PostgreSQL connection errors (quick guide)"
source: acme
document_type: troubleshooting
environment: production
permissions: [developer, platform-engineer, security-admin]
status: active
created_at: 2025-07-01
updated_at: 2025-11-11
tags: [rds, postgresql, connections, timeout, refused, failover, secrets]
related: [rds-connection-failure, database-platform]
---
# Troubleshooting: RDS PostgreSQL connection errors

Developer-facing quick guide. The DBRE runbook `rds-connection-failure` has the full procedure;
this page repeats the parts an app engineer can act on.

## Match the error

| Error | Meaning | What to do |
|---|---|---|
| `connection refused` | reached a host, nothing listening | wrong port/host; instance rebooting; check `aws rds describe-events` |
| `timeout expired` / `i/o timeout` | packets dropped | security group; wrong subnet path; DNS pointing to old IP after failover — restart pods |
| `FATAL: remaining connection slots are reserved` | instance at `max_connections` | your service's `replicas × pool_size` is too big; payments must use RDS Proxy |
| `FATAL: too many connections for role "…"` | your role's `CONNECTION LIMIT` reached | same as above, scoped to your service |
| `password authentication failed` | stale credential | secret rotated; ESO refresh + `rollout restart` |
| `SSL SYSCALL error: EOF detected` | connection dropped mid-query | failover or `idle_in_transaction_session_timeout` (60 s) — check for long transactions |
| `canceling statement due to statement timeout` | query > 30 s | fix the query or run it via reporting replica |

## Things to check in your own deployment

- Host is `<name>-pg.prod.acme.internal` (payments: the RDS Proxy endpoint), never a raw RDS hostname.
- Pool size × replicas ≤ role limit (payments 400, ledger 900, identity 300, reporting 200).
- Readiness probe does not depend on the database (see INC-0952).
- Reloader annotation present if you don't refresh credentials on pool recycle.
- JVM: `networkaddress.cache.ttl=30` so failover DNS changes are noticed.

Anything instance-side (storage, IOPS, parameter groups, failover) → `#dbre`.
