---
document_id: iam-access-denied
title: "Troubleshooting: IAM AccessDenied and AssumeRole failures"
source: acme
document_type: troubleshooting
environment: all
permissions: [developer, platform-engineer, security-admin]
status: active
created_at: 2025-06-05
updated_at: 2026-03-18
tags: [iam, access-denied, assumerole, irsa, passrole, scp, permission-boundary, sts]
related: [s3-access-denied, security-account-layout, eks-architecture]
---
# Troubleshooting: IAM AccessDenied and AssumeRole failures

Policy evaluation order (see the public IAM docs `aws-iam-policy-evaluation-logic`): explicit
deny anywhere wins → SCP → permission boundary → identity/resource policies → session policy.
At Acme every one of those layers exists, so read the **error message** — it names the layer.

| Error message contains | Layer | Where to look |
|---|---|---|
| `with an explicit deny in a service control policy` | SCP | `security-account-layout` table; e.g. region ≠ us-east-1/us-west-2, IMDSv1, state bucket policy |
| `with an explicit deny in a permissions boundary` | boundary | all IRSA and CI roles carry `AcmeWorkloadBoundary`; it denies IAM writes and `organizations:*` |
| `because no identity-based policy allows` | identity policy | the role simply lacks the action; add in `modules/acme-eks/irsa/<service>.tf` |
| `because no resource-based policy allows` | resource policy | bucket policy, KMS key policy, Secrets Manager resource policy (cross-account) |
| `is not authorized to perform: sts:AssumeRoleWithWebIdentity` | IRSA trust | SA annotation vs trust `sub`; namespace/SA renamed? OIDC provider thumbprint after cluster recreation? |
| `is not authorized to perform: iam:PassRole` | PassRole | the caller may create the resource but not hand it the role; add `iam:PassRole` on that role ARN with `iam:PassedToService` condition |
| `The security token included in the request is invalid` | expired/rotated creds | pod started before rotation; restart |
| `MalformedPolicyDocument` | policy syntax | Terraform `jsonencode` vs heredoc; validate with `aws iam simulate-custom-policy` |

## Simulate before you change

```bash
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::111111111111:role/acme-prod-irsa-ledger-service \
  --action-names s3:GetObject --resource-arns arn:aws:s3:::acme-prod-ledger-exports/2026/x.parquet
```

`simulate-principal-policy` does **not** evaluate SCPs or resource policies — combine with the
error text.

## IRSA quick check

```bash
kubectl get sa <sa> -n <ns> -o jsonpath='{.metadata.annotations.eks\.amazonaws\.com/role-arn}'
aws iam get-role --role-name acme-prod-irsa-<service> --query 'Role.AssumeRolePolicyDocument'
```

The trust `Condition.StringEquals` must include `oidc.eks.us-east-1.amazonaws.com/id/<ID>:sub:
system:serviceaccount:<ns>:<sa>` and `:aud: sts.amazonaws.com`. Clusters recreated in DR tests
get a new OIDC ID — Terraform derives it, hand-written trust policies don't.
