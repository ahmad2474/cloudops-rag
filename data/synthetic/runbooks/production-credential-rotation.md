---
document_id: production-credential-rotation
title: "Runbook: Emergency rotation of production credentials after exposure"
source: acme
document_type: runbook
environment: production
permissions: [security-admin]
status: active
created_at: 2025-05-30
updated_at: 2026-05-12
tags: [security, credentials, rotation, exposure, kms, iam, break-glass, forensics]
related: [break-glass-procedure, secret-management, security-account-layout, postmortem-inc-1063]
---
# Runbook: Emergency rotation of production credentials after exposure

**RESTRICTED — SecEng only.** Do not paste into incident channels. Reference by ID.

Triggers: a credential appears in a public repo, a CI log, a Slack message, GuardDuty
`UnauthorizedAccess:IAMUser/InstanceCredentialExfiltration`, or a vendor breach notice.

## 0. Contain first, rotate second (first 15 minutes)

1. Open SEV-1 (`#inc-<id>`), IC = `sec-oncall`. Comms lead informs Legal within 1 h if customer
   data may be involved (PCI requirement).
2. **Freeze the identity**:
   - IAM user/role: attach `AcmeDenyAll` policy (`arn:aws:iam::111111111111:policy/AcmeDenyAll`)
     — faster and reversible compared to deleting keys.
   - IRSA role: edit the trust policy to remove the OIDC condition (pods lose access on next
     token refresh, ≤ 1 h) **and** `kubectl scale --replicas=0` the workload if exfiltration
     is ongoing.
   - CI token (GitHub OIDC role `acme-prod-github-deploy`): remove the `sub` condition for the
     affected repo in the trust policy.
3. Snapshot evidence before rotating: CloudTrail Lake query saved to
   `s3://acme-security-forensics/<inc-id>/` (see §4).

## 1. Rotate

| Credential | How | Consumers to restart |
|---|---|---|
| RDS app users | `aws secretsmanager rotate-secret --secret-id acme/prod/rds/<inst>/app --rotate-immediately` (rotator is alternating-user; run twice to cycle both users) | ESO force-sync, `rollout restart` in the namespace |
| KMS-protected data | keys are **not** rotated on exposure (envelope keys); instead revoke the principal from the key policy `alias/acme-prod-customer-docs` and re-grant post-incident | none |
| Third-party keys | vendor console → `put-secret-value` | ESO force-sync + restart |
| GitHub deploy role | rotate the OIDC trust `sub` and re-issue environment secrets | re-run pipeline |
| Break-glass user `acme-breakglass` | reset console password + MFA device in `acme-security`; new password to the two sealed-envelope holders | none |

## 2. Verify no persistence

- IAM: `aws iam list-users`, `list-access-keys`, roles with recently modified trust policies
  (`aws iam get-role` + `RoleLastUsed`), new Lambda functions, new EventBridge rules.
- EKS: new ClusterRoleBindings (`kubectl get clusterrolebinding --sort-by=.metadata.creationTimestamp`),
  new ServiceAccounts with IRSA annotations, pods with `hostNetwork`.
- S3: bucket policies diff vs Terraform plan (drift = tampering until proven otherwise).

## 3. Un-freeze

Only after rotation and §2 are clean; remove `AcmeDenyAll`, restore trust policies from
Terraform (`atlantis apply` on the revert PR).

## 4. Forensics query (CloudTrail Lake, `acme-security`)

```sql
SELECT eventTime, eventName, sourceIPAddress, userIdentity.arn, requestParameters
FROM 6a1f…-event-data-store
WHERE userIdentity.accessKeyId = '<AKIA…>' AND eventTime > '2026-05-07 00:00:00'
ORDER BY eventTime
```

Preserve for 1 year (Object Lock on the forensics bucket).

## 5. Postmortem must include

Exposure window, actions taken by the attacker (from §4), data accessed, rotation completion
times, and the control that should have prevented exposure (INC-1063: push-protection secret
scanning was not enforced on the `acme-infra` repo).
