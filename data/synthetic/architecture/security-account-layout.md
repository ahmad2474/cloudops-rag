---
document_id: security-account-layout
title: "Architecture: Security account, audit trails, and guardrails"
source: acme
document_type: architecture
environment: all
permissions: [platform-engineer, security-admin]
status: active
created_at: 2025-02-20
updated_at: 2026-05-15
tags: [security, cloudtrail, guardduty, scp, gatekeeper, audit, kms, organizations]
related: [production-access, break-glass-procedure, production-credential-rotation]
---
# Architecture: Security account (`acme-security`, 444444444444)

## Purpose

Immutable audit and detection, isolated from workload accounts. Only `AcmeSecurityAdmin`
(SecEng) can assume roles here; `AcmePlatformAdmin` has read-only.

## Components

- **Org CloudTrail** (all accounts, all regions, management + S3/Lambda data events for
  `acme-prod-*` data buckets) → `acme-security-cloudtrail` (S3, Object Lock compliance 400 d)
  + **CloudTrail Lake** event data store (1 y) for queries.
- **GuardDuty** delegated admin (EKS audit logs, runtime monitoring, S3 protection, malware
  scan on EBS). Findings → Security Hub → EventBridge → PagerDuty `sec-oncall` (High/Critical).
- **Security Hub** with CIS 1.4 + AWS Foundational; suppressions tracked in `acme-infra`.
- **Gatekeeper audit**: every PAW session (request, approver, duration, CloudTrail session
  ARN) written to DynamoDB `gatekeeper-audit` and mirrored to Slack `#gatekeeper-audit`.
- **Forensics bucket** `acme-security-forensics` (Object Lock, 1 y).

## Guardrails (SCPs, applied at OU level)

| SCP | Effect |
|---|---|
| `DenyLeaveOrg` | no account can leave the organisation |
| `DenyCloudTrailDisable` | `cloudtrail:StopLogging/DeleteTrail` denied |
| `RegionRestriction` | deny all actions outside us-east-1/us-west-2 (except global services) |
| `DenyRootUser` | root user actions denied except account recovery |
| `ProtectStateBuckets` | `s3:PutBucketPolicy`/`DeleteBucket` on `*terraform-state*` denied unless `aws:PrincipalArn` = Atlantis role |
| `DenyIMDSv1` | `ec2:RunInstances` denied unless `ec2:MetadataHttpTokens = required` |

## Break-glass

Two IAM users in `acme-security` (`acme-breakglass-1/2`) with hardware MFA, passwords in
sealed envelopes (CTO, Head of SecEng). Use triggers a GuardDuty custom finding and a
`sec-oncall` page. Procedure in `break-glass-procedure` (restricted).

## Key management

Prod KMS keys in `acme-prod`; key policies grant admin to `AcmeSecurityAdmin` only and usage to
specific IRSA roles. `alias/acme-prod-customer-docs` additionally requires
`kms:ViaService = s3.us-east-1.amazonaws.com`.
