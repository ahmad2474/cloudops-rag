---
document_id: terraform-plan-drift
title: "Troubleshooting: Unexpected changes in terraform plan (drift)"
source: acme
document_type: troubleshooting
environment: all
permissions: [platform-engineer, security-admin]
status: active
created_at: 2025-09-05
updated_at: 2026-05-20
tags: [terraform, drift, plan, atlantis, provider-upgrade, tags, console-changes]
related: [terraform-state-lock-recovery, delivery-pipeline, production-access]
---
# Troubleshooting: Unexpected changes in `terraform plan`

The nightly drift job posts to `#platform-drift`. Plans on PRs should only show what the PR
changes. Anything else falls into one of these:

## 1. Someone changed it in the console

`~ update in-place` on a resource nobody touched in HCL. Find who: CloudTrail
`lookup-events --lookup-attributes AttributeKey=ResourceName,AttributeValue=<id>`. Decide:
**revert** (apply the plan) or **adopt** (edit HCL to match). Console edits in prod violate
`production-access`; note it in the ticket — no blame, but the drift job exists for a reason.

Classic: security group rules added during an incident, RDS parameter tweaks, IAM policy
edits. Adopt them properly via PR.

## 2. Provider upgrade changed defaults or attribute names

After `aws ~> 5.80` some resources show `~ tags_all` churn or new computed attributes. Check
the provider CHANGELOG; usually fixed by `ignore_changes` on a computed attribute or by
setting the new default explicitly.

## 3. `default_tags` vs resource `tags`

Duplicated tags between `provider.default_tags` and resource `tags` produce perpetual diffs on
some resource types (known provider issue). Keep `acme:*` tags only in `default_tags`.

## 4. Replacement (`-/+`) on something that must not be replaced

`prevent_destroy = true` will fail the plan for RDS/S3/KMS — that's the guardrail working.
Typical trigger: renaming an EKS node group (forces replacement), changing `availability_zone`,
changing a KMS key alias. Use `moved` blocks for renames and stage replacements
(create-before-destroy) explicitly.

## 5. Data source now resolves differently

`data.aws_ami` with `most_recent = true` → plan wants to replace launch templates every time a
new AMI appears. Pin the AMI alias/version (Karpenter `EC2NodeClass` uses `alias: al2023@v…`).

## 6. Lock file mismatch

`Error: Inconsistent dependency lock file` — run `terraform providers lock -platform=linux_amd64
-platform=darwin_arm64` and commit `.terraform.lock.hcl`. Atlantis runs on linux.

## Don't

`terraform apply -refresh-only` and `terraform state rm` in prod to "make the diff go away".
The diff is information.
