---
document_id: database-security
title: "Policy: Database security and data access"
source: acme
document_type: policy
version: "1.4"
environment: production
permissions: [developer, platform-engineer, security-admin]
status: active
created_at: 2025-03-01
updated_at: 2026-02-05
tags: [policy, database, rds, encryption, iam-auth, pii, pci, access]
related: [database-platform, secret-management, production-access]
---
# Policy: Database security and data access

Owner: SecEng with DBRE. Applies to all RDS instances and any datastore holding cardholder
or personal data.

## Controls

1. **Network**: databases live only in private-data subnets; no public accessibility flag,
   ever. Ingress only from the EKS node SG / pod SGs listed in Terraform.
2. **Encryption**: at rest with `alias/acme-prod-rds`; in transit `rds.force_ssl=1`
   (`sslmode=verify-full` in clients, RDS CA bundle baked into base images).
3. **Identities**: one application role per service (`payments_app`, `ledger_app`, …) with a
   `CONNECTION LIMIT`; no shared roles; no superuser for applications. Human access uses
   `dbre_admin` (DBRE) or `sec_readonly` (SecEng) **only** through a Gatekeeper session; the
   session's CloudTrail ARN is set as `application_name`.
4. **Credentials**: application passwords live in Secrets Manager and rotate every 90 days
   (see `secret-management`); IAM database authentication is enabled and required for human
   access since 2026-01.
5. **Cardholder data**: PAN never stored (tokenised at the edge by the vault provider); last4
   + token only. Databases in scope for PCI: `prod-payments-pg`, `prod-ledger-pg`.
6. **Customer documents** (`acme-prod-customer-documents`): access limited to
   `identity-service` IRSA role and `AcmeSecurityAdmin`; every read logged as an S3 data event.
7. **Exports**: no `pg_dump` to laptops. Analytical access via `prod-reporting-pg`
   (masked views) or the nightly ledger export bucket.
8. **Logging**: `log_connections`, `log_disconnections`, `pgaudit` for DDL and role changes;
   logs shipped to CloudWatch `/acme/prod/rds/<instance>` (90 d) and the security archive.

## Change control

Schema changes only via `dbre-migrate` from a reviewed PR; parameter group changes via
Terraform. Emergency DDL in an incident requires a PAW session and a follow-up PR within 24 h.
