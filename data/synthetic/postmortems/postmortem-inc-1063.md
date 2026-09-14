---
document_id: postmortem-inc-1063
title: "Postmortem INC-1063: leaked CI token used against customer-documents bucket"
source: acme
document_type: postmortem
environment: production
permissions: [security-admin]
status: active
created_at: 2026-05-14
updated_at: 2026-05-29
tags: [postmortem, sev-1, security, credential-leak, s3, kms, github, secret-scanning, restricted]
related: [inc-1063, production-credential-rotation, secret-management, security-account-layout]
---
# Postmortem: INC-1063 — leaked CI token used against `acme-prod-customer-documents`

**RESTRICTED — SecEng.** Summary for the wider org is in the SEV-1 comms doc; this page holds
the full analysis.

**Date:** 2026-05-07 · **Severity:** SEV-1 · **Duration:** exposure 2026-05-05 22:14 → containment 2026-05-07 09:58 UTC (~36 h) · **IC:** sec-oncall

## Impact

An attacker used a GitHub personal access token (PAT) committed to a fork of `acme-infra`
to run a workflow that assumed a **legacy** IAM role `acme-prod-ci-legacy` (long-lived access
key stored as a repository secret; scheduled for removal, ticket `SEC-441`). With it they
attempted 1,912 `s3:GetObject` calls against `acme-prod-customer-documents`. **All were
denied** — the KMS key policy for `alias/acme-prod-customer-docs` allows only
`acme-prod-irsa-identity-service` and `AcmeSecurityAdmin`, and the bucket policy requires
`aws:sourceVpce`. 3 `s3:ListBucket` calls succeeded (object keys only, no content; keys are
opaque UUIDs). The attacker also ran `iam:ListRoles` (allowed) and `sts:GetCallerIdentity`.

No customer document contents were accessed. Regulator notification not required
(assessed with Legal 2026-05-09); customers not affected.

## Timeline (UTC)

- 05-05 22:14 Engineer pushes a debugging commit with a PAT in `scripts/local-atlantis.sh` to a personal fork (public).
- 05-06 03:40 Token harvested (GitHub secret-scanning partner alert delivered to the engineer's email; unread).
- 05-07 08:12 GuardDuty `Discovery:S3/AnomalousBehavior` + `Policy:S3/BucketBlockPublicAccessDisabled` attempt (denied by SCP) → `sec-oncall` page.
- 08:20 SEV-1 declared. CloudTrail Lake: source IP outside Acme ranges; access key `AKIA…LEGACY`.
- 08:31 `AcmeDenyAll` attached to `acme-prod-ci-legacy`; access key deactivated; PAT revoked with GitHub support.
- 09:10 Full rotation per `production-credential-rotation` §1 (all RDS app secrets, third-party keys, GitHub deploy OIDC trust).
- 09:58 Containment confirmed; forensic export saved to `acme-security-forensics/INC-1063/`.
- 05-08 Persistence check (§2) clean.

## Root cause

A legacy long-lived key existed in a repository secret because the OIDC migration (`SEC-441`)
left one workflow behind. Exposure vector was a committed PAT in a public fork; push
protection was enabled on `acme-infra` but forks inherit the setting only when org-enforced,
which it wasn't.

## Why it didn't become a breach

Defence in depth worked exactly as designed: KMS key policy + `aws:sourceVpce` bucket
condition + SCP on Block Public Access. Worth saying plainly in the org-wide summary.

## Action items

| # | Action | Owner | Status |
|---|---|---|---|
| 1 | Delete `acme-prod-ci-legacy`; no IAM users/keys remain in `acme-prod` (verified by Config rule) | SecEng | done 2026-05-08 |
| 2 | Org-wide push protection enforced (covers forks) | SecEng | done 2026-05-15 |
| 3 | `secret-management` v2.0 published (90-day rotation, push protection) | SecEng | done |
| 4 | GuardDuty findings for `Discovery:*` set to page (were ticket-only) | SecEng | done |
| 5 | Secret-scanning alerts routed to `#security` not personal email | SecEng | done |
| 6 | Engineer follow-up: blameless; training module updated | Eng Mgmt | done |
