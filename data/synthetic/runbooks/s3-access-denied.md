---
document_id: s3-access-denied
title: "Runbook: S3 AccessDenied (403) from workloads"
source: acme
document_type: runbook
environment: production
permissions: [developer, platform-engineer, security-admin]
status: active
created_at: 2025-04-02
updated_at: 2026-02-19
tags: [s3, iam, irsa, access-denied, kms, bucket-policy, vpc-endpoint]
related: [iam-access-denied, security-account-layout, secret-management]
---
# Runbook: S3 AccessDenied (403) from workloads

**Owner:** Platform Engineering (IRSA/endpoints) · SecEng (bucket policies, KMS)

An S3 403 has **five** possible gates. Check them in this order; each takes a minute.

## 0. Identify the caller

```bash
# Inside the pod
aws sts get-caller-identity
# Expect arn:aws:sts::111111111111:assumed-role/acme-prod-irsa-<service>/<pod>
```

If it returns the **node** role (`acme-prod-eks-node`), IRSA is not wired: the ServiceAccount
lacks the `eks.amazonaws.com/role-arn` annotation, or the pod doesn't use that SA. That's a
deploy bug, not an IAM bug.

## 1. Identity policy (IRSA role)

`aws iam get-role-policy --role-name acme-prod-irsa-<service> --policy-name s3` — must list
the action (`s3:GetObject`, `s3:PutObject`, `s3:ListBucket` — `ListBucket` is on the **bucket**
ARN, object actions on `arn:aws:s3:::bucket/*`). Managed in `modules/acme-eks/irsa/<service>.tf`.

## 2. Bucket policy

All `acme-prod-*` buckets deny `aws:SecureTransport = false` and, for data buckets, deny
requests not from `vpce-*` in the prod VPC (`aws:sourceVpce`). A pod using the **NAT path**
instead of the S3 gateway endpoint (route table missing the endpoint) will be denied.
Check: `aws ec2 describe-route-tables --filters Name=vpc-id,Values=<vpc-prod-use1>` → route to `pl-63a5400a` via the vpce.

## 3. KMS

Buckets using SSE-KMS need `kms:Decrypt`/`kms:GenerateDataKey` on the key **and** the key
policy must allow the role. `acme-prod-customer-documents` (`alias/acme-prod-customer-docs`)
key policy allows **only** `acme-prod-irsa-identity-service` and `AcmeSecurityAdmin`. Requests
from any other role return 403 with `KMS.AccessDeniedException` in CloudTrail — this is by
design (see `database-security`, `break-glass-procedure`).

## 4. Block Public Access / ACLs

Object ACLs are disabled (`BucketOwnerEnforced`). Any request setting `x-amz-acl` fails with
`AccessControlListNotSupported`. Remove ACL flags from SDK calls.

## 5. SCP (organisation)

`acme-security` applies an SCP denying `s3:PutBucketPolicy` outside Terraform's role and
denying all S3 actions from regions other than us-east-1/us-west-2. Check CloudTrail
`errorMessage` for `explicit deny in a service control policy`.

## Diagnose with CloudTrail

```bash
aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventName,AttributeValue=GetObject \
  --start-time $(date -u -v-30M +%FT%TZ) --query 'Events[?contains(CloudTrailEvent, `AccessDenied`)]' | head -50
```

Data events for `acme-prod-customer-documents` are logged in the `acme-security` account
(org trail); ask `sec-oncall` for those.

## Verification

Retry the call from the pod; confirm no new `AccessDenied` in CloudTrail for 10 min.
