---
document_id: production-access
title: "Policy: Production access (Privileged Access Workflow)"
source: acme
document_type: policy
version: "2.1"
environment: production
permissions: [developer, platform-engineer, security-admin]
status: active
supersedes: production-access-2024
created_at: 2025-02-01
updated_at: 2026-03-10
tags: [policy, access, gatekeeper, paw, least-privilege, audit, pci]
related: [production-access-2024, break-glass-procedure, security-account-layout, incident-response]
---
# Policy: Production access

**Effective 2025-02-01 (v2.0); v2.1 2026-03-10.** Owner: Security Engineering. Applies to
every engineer and every system identity touching `acme-prod` or production data.

## Principles

1. **No standing privileged access.** Nobody holds write access to `acme-prod` by default.
   Read-only (`AcmeReadOnly`, EKS view in own namespaces) is the baseline for engineers.
2. **Just-in-time elevation through Gatekeeper.** Any write, exec, port-forward, or console
   change in prod requires a Gatekeeper **Privileged Access Workflow (PAW)** session.
3. **Everything is attributable.** Sessions are tied to a person, an approver, a reason, and
   a ticket or incident ID.

## Requesting a PAW session

| Field | Rule |
|---|---|
| Role | `AcmePlatformAdmin` (infra), `AcmeSecurityAdmin` (SecEng only), namespace-admin (app teams, own namespace) |
| Duration | max **4 hours**; extendable once by the approver |
| Reason | free text + **ticket/incident ID required** |
| Approver | on-call lead of the owning team; during a declared incident the IC may self-approve for `namespace-admin` only |

Gatekeeper issues short-lived Identity Center credentials; `kubectl` access is via EKS access
entries bound to the session. Sessions are recorded (CloudTrail + `#gatekeeper-audit`).

## Prohibited

- **Direct SSH/SSM shell to production nodes** except through a PAW session with
  `AcmePlatformAdmin` and only for node-level incidents (the 2024 policy that permitted SSH
  with manager approval is withdrawn).
- Console changes to resources managed by Terraform (drift is reverted and reported).
- Sharing session credentials, screen-sharing a privileged shell to non-approved persons.
- Copying production data to laptops or non-prod accounts.

## Break-glass

If Gatekeeper or Identity Center is unavailable, follow `break-glass-procedure` (SecEng only).

## Enforcement

Violations are reviewed by SecEng; repeated violations escalate to engineering management.
Quarterly access review of permission set assignments.

## Changelog

- 2.1 (2026-03-10): IC self-approval for `namespace-admin` during incidents; port-forward
  explicitly included in "write".
- 2.0 (2025-02-01): Gatekeeper PAW replaces manager-approved SSH.
