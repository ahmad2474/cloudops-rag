---
document_id: postmortem-inc-0952
title: "Postmortem INC-0952: payments database connection exhaustion"
source: acme
document_type: postmortem
environment: production
permissions: [developer, platform-engineer, security-admin]
status: active
created_at: 2025-06-30
updated_at: 2025-07-08
tags: [postmortem, sev-1, rds, connections, hpa, rds-proxy, payments]
related: [inc-0952, database-platform, rds-connection-failure]
---
# Postmortem: INC-0952 — payments database connection exhaustion

**Date:** 2025-06-24 · **Severity:** SEV-1 · **Duration:** 14:07–15:21 UTC (74 min) ·
**IC:** payments-oncall lead · **Authors:** DBRE, Payments

## Impact

`payments-api` returned 5xx for ~38% of requests for 41 min and degraded for a further 33 min.
An estimated 11,400 payment attempts failed; 9,900 were retried successfully by merchants'
clients, ~1,500 were not (merchant email sent). Availability SLO monthly budget consumed: 71%.

## Timeline (UTC)

- 13:50 Marketing campaign for a large merchant begins; traffic +180%.
- 14:02 HPA scales `payments-api` 12 → 30 replicas (max 40).
- 14:05 `prod-payments-pg` `DatabaseConnections` reaches 1000 (`max_connections`).
- 14:07 `FATAL: remaining connection slots are reserved` in app logs; readiness fails; ALB 503s. **Page.**
- 14:15 IC declared SEV-1. Initial hypothesis: database CPU. CPU was 34%.
- 14:26 DBRE: `pg_stat_activity` shows 30 × 32-connection pools = 960 + migrations + monitoring.
- 14:31 Mitigation 1: HPA `maxReplicas` 40 → 20 and `kubectl scale` to 20. Connections drop to ~700; errors fall to 12%.
- 14:48 Mitigation 2: pool size 32 → 16 via config map + rollout. Errors < 1% by 15:04.
- 15:21 Resolved. Campaign traffic sustained without errors at 24 replicas × 16.

## Root cause

Connection budget was never modelled: `replicas × pool_size` had no upper bound tied to
`max_connections`. Autoscaling made the failure mode inevitable under load; the campaign was
just the trigger. The `payments_app` role had no `CONNECTION LIMIT`, so the whole instance was
consumed, including the slots reserved for `dbre_admin`.

## Contributing factors

- Alarm `DatabaseConnections > 80%` existed but paged DBRE only, not the app team.
- The load test before the campaign ran against staging with 4 replicas.
- Readiness probe ran `SELECT 1` on the same pool, so a starved pool marked pods unready and
  the ALB dropped healthy-but-waiting pods, amplifying errors.

## What went well

Rollback of HPA settings was fast; DBRE had `pg_stat_activity` grouping ready; comms cadence held.

## Action items

| # | Action | Owner | Status |
|---|---|---|---|
| 1 | Deploy **RDS Proxy** for payments (`prod-payments-proxy`), app pools → proxy | DBRE | done 2025-07-03 |
| 2 | `CONNECTION LIMIT` per app role (payments 400, ledger 900, identity 300, reporting 200) | DBRE | done |
| 3 | `replicas × pool ≤ limit` check in Helm chart CI | PE | done |
| 4 | Readiness probe decoupled from DB pool (liveness never touches DB) | Payments | done |
| 5 | Connection alarm pages owning team too | PE | done |
| 6 | Load-test parity: staging at 25% with same HPA maxima | PE | done 2025-08 |
