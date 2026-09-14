---
document_id: production-access-2024
title: "Policy: Production access (2024)"
source: acme
document_type: policy
version: "1.3"
environment: production
permissions: [developer, platform-engineer, security-admin]
status: deprecated
created_at: 2024-03-15
updated_at: 2024-11-20
tags: [policy, access, ssh, bastion, manager-approval]
related: [production-access]
---
# Policy: Production access (2024)

> **WITHDRAWN 2025-02-01.** Replaced by `production-access` v2.0 (Gatekeeper PAW). This page
> is retained for audit only and must not be followed.

## Access model

Engineers may access production directly when needed to resolve an issue:

1. Request approval from your engineering manager in `#prod-access` (Slack), stating the reason.
2. Once approved, connect through the bastion host `bastion.prod.acme.internal` with your
   personal SSH key, then SSH or `kubectl` from there.
3. Post a summary of what you changed in `#prod-access` when done.

Standing `kubectl` cluster-admin is granted to Platform Engineering and to team leads.

## Console access

Engineers with the `Developer` IAM group may make console changes to their own team's
resources. Terraform should be updated afterwards to match.

## Break-glass

If the manager is unreachable, another manager or the on-call engineer may approve.
