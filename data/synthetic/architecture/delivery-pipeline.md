---
document_id: delivery-pipeline
title: "Architecture: Build and deployment pipeline (GitHub Actions → ECR → ArgoCD)"
source: acme
document_type: architecture
environment: all
permissions: [developer, platform-engineer, security-admin]
status: active
created_at: 2025-04-10
updated_at: 2026-05-22
tags: [ci, cd, github-actions, ecr, argocd, argo-rollouts, atlantis, terraform, canary, rollback]
related: [eks-architecture, terraform-state-lock-recovery, kubernetes-workload-standards]
---
# Architecture: Delivery pipeline

## Application path

1. PR → GitHub Actions: lint, unit tests, `trivy fs`, SBOM (syft), build image
   (multi-arch), `trivy image` gate (no CRITICAL), push to ECR in `acme-shared`
   `555555555555.dkr.ecr.us-east-1.amazonaws.com/<service>:<git-sha>`. Image signed with cosign
   (Kyverno `verify-images` policy enforces in prod since 2026-05).
2. Merge to `main` → the `deploy` workflow bumps the image tag in the `acme-deploy` repo
   (`envs/staging/<service>/values.yaml`) via a bot PR that auto-merges.
3. ArgoCD (`acme-shared`) auto-syncs **staging**. Smoke tests run post-sync (Argo hook).
4. Promotion to prod = PR from `envs/staging` → `envs/prod` values, requires CODEOWNERS review
   from the owning team; ArgoCD prod apps are `manual` sync → engineer clicks Sync (or
   `argocd app sync`) inside the deploy window.
5. `payments-api` and `checkout-web` use Argo Rollouts canary: 10% → 50% → 100%, 10 min per
   step, analysis on error rate (< 0.5%) and p99 (< 400 ms) from Prometheus; auto-abort.

AuthN from GitHub to AWS is OIDC (`acme-prod-github-deploy` role, `sub` restricted to
`repo:acme/acme-deploy:environment:prod`) — no long-lived keys (INC-1063 was a PAT in a
different repo, not this path).

## Infrastructure path

`acme-infra` PR → Atlantis `plan` comment (per stack, `-lock-timeout=5m`) → reviewer approves →
`atlantis apply`. Prod stacks require `AcmePlatformAdmin` approval label. Checkov + tflint
run in CI before Atlantis. Drift detection job nightly (`terraform plan -detailed-exitcode`)
posts to `#platform-drift`.

## Deploy windows & freezes

Prod deploys Mon–Thu 08:00–18:00 UTC, Fri until 14:00 UTC. Frozen during declared SEV-1/2
and the last 3 business days of each month (ledger close). Exceptions: IC approval.

## Rollback

ArgoCD `History and Rollback` to the previous revision (≤ 2 min). Rollouts: `kubectl argo
rollouts abort` promotes stable. Database migrations are expand/contract so app rollback never
needs a schema rollback.
