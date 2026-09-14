---
document_id: secret-management
title: "Policy: Secret management"
source: acme
document_type: policy
version: "2.0"
environment: all
permissions: [developer, platform-engineer, security-admin]
status: active
created_at: 2025-02-15
updated_at: 2026-04-01
tags: [policy, secrets, secrets-manager, rotation, external-secrets, github, scanning]
related: [secret-rotation, database-security, production-credential-rotation]
---
# Policy: Secret management

Owner: SecEng. **v2.0 effective 2026-04-01.**

## Rules

1. **Single source**: all application secrets live in AWS Secrets Manager under
   `acme/<env>/<service>/<name>`. Kubernetes Secrets are projections via External Secrets
   Operator only — never created by hand or committed (even sealed).
2. **Rotation cadence** — **90 days** for database credentials and third-party API keys
   (down from 180 days in v1.x; the change was driven by the PCI 4.0 assessment). Immediate
   rotation on any suspected exposure.
3. **Automatic where possible**: RDS credentials rotate via `acme-secret-rotator`
   (alternating users). Third-party keys without rotation APIs are tracked in the
   `secret-inventory` sheet with owners and due dates; overdue = Security Hub custom finding.
4. **Consumers must tolerate rotation**: services re-read credentials on pool refresh or carry
   the Reloader annotation so ESO updates trigger a restart.
5. **No secrets in**: source code, container images, Helm values, CI logs, Slack, tickets.
   GitHub secret scanning with **push protection** is enforced org-wide (since 2026-05-15,
   after INC-1063). `trivy fs --scanners secret` runs in CI.
6. **Human access** to secret values requires a Gatekeeper session; `GetSecretValue` by humans
   is alerted in `#gatekeeper-audit`.
7. **Least privilege**: IRSA roles get `secretsmanager:GetSecretValue` on their own
   `acme/prod/<service>/*` prefix only.

## Exposure response

Treat as SEV-1; see `production-credential-rotation` (SecEng) and `incident-response`.

## Changelog

- 2.0 (2026-04-01): cadence 180 → **90 days**; push protection mandated.
- 1.2 (2025-06-30): ESO replaces the legacy `secrets-sync` CronJob.
