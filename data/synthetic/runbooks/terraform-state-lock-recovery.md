---
document_id: terraform-state-lock-recovery
title: "Runbook: Terraform state locked, drifted, or corrupted"
source: acme
document_type: runbook
environment: all
permissions: [platform-engineer, security-admin]
status: active
created_at: 2025-06-02
updated_at: 2026-05-20
tags: [terraform, state, locking, dynamodb, s3, atlantis, force-unlock, import, drift]
related: [terraform-plan-drift, delivery-pipeline]
---
# Runbook: Terraform state locked, drifted, or corrupted

**Owner:** Platform Engineering. Prod state changes require a Gatekeeper session; Atlantis is
the only sanctioned apply path for `acme-prod`.

## A. `Error acquiring the state lock`

```
Error: Error acquiring the state lock
Lock Info:
  ID:        6f1c…
  Path:      acme-prod-terraform-state/stacks/acme-prod/us-east-1/network/terraform.tfstate
  Who:       atlantis@atlantis-0
  Created:   2026-05-19 14:02:11 UTC
```

1. Is an Atlantis run still going? Check the PR comments / `#atlantis` — if a plan or apply is
   in progress, **wait**. Locks older than 30 min with no running pod are stale.
2. Confirm no running apply: `kubectl get pods -n atlantis` (in `acme-shared`), and the
   DynamoDB item: `aws dynamodb get-item --table-name acme-prod-terraform-locks --key '{"LockID":{"S":"acme-prod-terraform-state/stacks/.../terraform.tfstate-md5"}}'`.
3. Force-unlock **using the lock ID from the error**, from Atlantis (`atlantis unlock` on the PR)
   or, if Atlantis is down, from a Gatekeeper session:
   `terraform force-unlock 6f1c…`. PE on-call must approve in `#platform` first.

Never delete the DynamoDB item by hand; `force-unlock` validates the ID.

## B. Plan shows unexpected changes (drift)

See `terraform-plan-drift`. Short version: someone changed it in the console. Decide
**revert** (apply) or **adopt** (update HCL to match, then plan should be empty). Console
changes in prod are a policy violation (`production-access`); note in the ticket.

## C. Resource exists but not in state (`already exists` on apply)

Use an `import` block (Terraform ≥ 1.5):

```hcl
import {
  to = module.rds_payments.aws_db_parameter_group.this
  id = "acme-pg16-prod-payments"
}
```

Plan shows `# … will be imported`; apply; then remove the block. For bulk, `terraform plan
-generate-config-out=generated.tf`. Do not use `terraform import` CLI in prod — it writes state
outside a PR.

## D. Refactoring without destroy

Moving a resource between modules: `moved { from = …  to = … }` blocks, not `state mv`.
`state mv`/`state rm` are for local experiments only. `prevent_destroy = true` is set on RDS,
S3 data buckets, KMS keys — a plan that wants to replace them **fails on purpose**.

## E. State file corrupted / wrong version

S3 versioning is on. `aws s3api list-object-versions --bucket acme-prod-terraform-state --prefix
stacks/…/terraform.tfstate` → copy the previous version back, then `terraform refresh` via a
plan. Record in the incident.

## Verification

`atlantis plan` on the PR shows the expected diff and no lock errors.
