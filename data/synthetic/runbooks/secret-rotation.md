---
document_id: secret-rotation
title: "Runbook: Rotating application secrets and RDS credentials"
source: acme
document_type: runbook
environment: production
permissions: [developer, platform-engineer, security-admin]
status: active
created_at: 2025-02-10
updated_at: 2025-04-22
tags: [secrets, rotation, secrets-manager, external-secrets, rds]
related: [secret-management, rds-connection-failure]
---
# Runbook: Rotating application secrets and RDS credentials

**Owner:** Platform Engineering (mechanics) · SecEng (policy)

## Rotation cadence

RDS application credentials rotate automatically every **180 days** via the
`acme-secret-rotator` Lambda. Non-database secrets (third-party API keys) rotate manually on
the same cadence or immediately on suspected exposure.

> Note: SecEng has proposed shortening the cadence; until `secret-management` is updated,
> 180 days is the operating value.

## How automatic rotation works

1. Secrets Manager invokes `acme-secret-rotator` (`createSecret` → `setSecret` →
   `testSecret` → `finishSecret`).
2. The rotator uses the **alternating-users** strategy: `payments_app` and `payments_app_clone`
   swap; the new password is set on the *inactive* user, tested, then the secret's
   `AWSCURRENT` label moves.
3. External Secrets Operator picks up the new version within its `refreshInterval` (1h) and
   updates the Kubernetes Secret.
4. Pods **do not** reload secrets automatically. `payments-api` and `ledger-service` re-read
   credentials on connection-pool refresh; other services need
   `kubectl rollout restart` (Reloader annotation `reloader.stakater.com/auto: "true"` is
   required by `kubernetes-workload-standards`).

## Manual rotation (compromise)

```bash
# 1. Trigger rotation now
aws secretsmanager rotate-secret --secret-id acme/prod/rds/prod-payments-pg/app
# 2. Force ESO refresh
kubectl annotate externalsecret db-credentials -n payments force-sync=$(date +%s) --overwrite
# 3. Restart consumers
kubectl rollout restart deploy -n payments
```

For third-party keys (Stripe, Twilio, SendGrid): rotate in the vendor console, `put-secret-value`
in Secrets Manager, then steps 2–3. Old key revoked only after the rollout completes.

## Verification

`aws secretsmanager describe-secret --secret-id ... --query 'VersionIdsToStages'` shows the new
version as `AWSCURRENT`; app `/ready` green; no `password authentication failed` in logs.
