---
document_id: rds-connection-failure
title: "Runbook: Application cannot connect to RDS PostgreSQL"
source: acme
document_type: runbook
environment: production
permissions: [developer, platform-engineer, security-admin]
status: active
created_at: 2025-05-11
updated_at: 2026-04-15
tags: [rds, postgresql, connections, rds-proxy, security-group, dns, max-connections, failover]
related: [database-platform, database-security, postmortem-inc-0952, rds-connection-troubleshooting]
---
# Runbook: Application cannot connect to RDS PostgreSQL

**Owner:** DBRE · **Page:** `dbre-oncall` (app symptoms: owning team first)

## Symptoms

- App logs: `connection refused`, `timeout expired`, `FATAL: remaining connection slots are
  reserved`, `FATAL: too many connections for role "payments_app"`, `SSL SYSCALL error: EOF`
- CloudWatch `DatabaseConnections` at ceiling, or `RDS / Connections` dashboard flat-lining to 0
- `payments-api` readiness failing (`/ready` checks a DB `SELECT 1`)

## Checklist — work top to bottom

### 1. Is the instance up?

```bash
aws rds describe-db-instances --db-instance-identifier prod-payments-pg \
  --query 'DBInstances[0].{status:DBInstanceStatus,az:AvailabilityZone,multiAZ:MultiAZ}'
aws rds describe-events --source-identifier prod-payments-pg --duration 120
```

`status` = `available` but a recent event `Multi-AZ instance failover completed` means the
**endpoint's IP changed**. Java/Node apps with cached DNS keep dialling the old primary.
Fix: restart pods (`kubectl rollout restart deploy/<svc> -n <ns>`); ensure JVM
`networkaddress.cache.ttl=30`. Since 2025-06 `payments-api` goes through **RDS Proxy**
(`prod-payments-proxy.proxy-xxxx.us-east-1.rds.amazonaws.com`), which absorbs failover —
if payments is failing on failover, someone bypassed the proxy.

### 2. Connection limits

```sql
-- as dbre_admin via Gatekeeper session
SELECT usename, state, count(*) FROM pg_stat_activity GROUP BY 1,2 ORDER BY 3 DESC;
SELECT count(*) AS idle_in_tx FROM pg_stat_activity WHERE state = 'idle in transaction';
```

- `max_connections` is 1000 (payments/identity/reporting) and 2000 (ledger); superuser
  reserves 3. If `pg_stat_activity` ≈ ceiling: find the leaking service (`application_name`),
  and terminate idle-in-transaction sessions older than 5 min:
  `SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state='idle in transaction' AND xact_start < now() - interval '5 min';`
- Pool sizing rule: `replicas × pool_size` per service must stay under the per-role
  `CONNECTION LIMIT` (payments_app = 400, ledger_app = 900). HPA scale-out without proxy is
  how INC-0952 happened.

### 3. Network path

```bash
# From a debug pod in the app namespace
kubectl run -n payments dbg --rm -it --image=555555555555.dkr.ecr.us-east-1.amazonaws.com/tools/netshoot -- \
  bash -c 'getent hosts payments-pg.prod.acme.internal; nc -zv -w3 payments-pg.prod.acme.internal 5432'
```

- DNS fails → Route 53 private zone / CoreDNS (`coredns-failure`).
- DNS ok, TCP times out → security group. RDS SG `sg-prod-rds-payments` must allow 5432
  from the EKS **node** SG *and* the **pod** SG if the workload uses SG-for-pods (`risk` ns).
  Terraform: `stacks/acme-prod/us-east-1/data/rds-payments.tf`, `ingress_sg_ids`.
- TCP ok, auth fails → §4.

### 4. Credentials

Secrets Manager `acme/prod/rds/prod-payments-pg/app` is rotated every 90 days by
`acme-secret-rotator`. External Secrets Operator syncs it into `payments/db-credentials`
(refresh interval 1h). A pod started with a stale secret fails after rotation until restarted.
Check: `kubectl get externalsecret -n payments db-credentials` → `SecretSynced` condition.

### 5. Storage / IOPS

`FreeStorageSpace` < 10% or `DiskQueueDepth` > 20 → instance may accept connections but
queries hang. Storage autoscaling is on (max 6 TB for ledger); IOPS on gp3 need a manual bump
(Terraform `iops`, `storage_throughput`).

## Verification

`DatabaseConnections` back under 70% of ceiling, app `/ready` green, no `FATAL` in logs for 10 min.
