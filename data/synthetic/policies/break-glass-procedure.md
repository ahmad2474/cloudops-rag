---
document_id: break-glass-procedure
title: "Procedure: Break-glass access when Gatekeeper or Identity Center is unavailable"
source: acme
document_type: policy
version: "1.2"
environment: production
permissions: [security-admin]
status: active
created_at: 2025-02-01
updated_at: 2026-02-20
tags: [security, break-glass, emergency-access, mfa, audit, restricted]
related: [production-access, security-account-layout, production-credential-rotation]
---
# Procedure: Break-glass access

**RESTRICTED — SecEng only.** Existence of this procedure may be referenced; contents may not
be shared outside Security Engineering.

## When

Only when *both* are true: (a) a SEV-1 is declared, and (b) Gatekeeper **or** IAM Identity
Center cannot issue a session (verified by `sec-oncall`, not assumed). Not for "Gatekeeper is
slow" or "approver unavailable" — those use the escalation path in `production-access`.

## Credentials

Two IAM users in `acme-security`: `acme-breakglass-1`, `acme-breakglass-2`. Console
passwords in sealed, numbered envelopes held by the CTO and the Head of SecEng (backup:
VP Engineering). Hardware MFA tokens in the office safe (combination known to `sec-oncall`
leads). Each user may assume `AcmeBreakGlass` in `acme-prod` (AdministratorAccess with an
SCP-enforced **1-hour** session limit).

## Steps

1. `sec-oncall` records in `#inc-<id>`: "Break-glass invoked, user N, envelope opened by <name>".
2. Sign in, assume `AcmeBreakGlass`, perform **only** the actions listed by the IC in the channel.
3. Every CLI call is run with `--profile breakglass` so CloudTrail attribution is clean.
4. Within 1 h of the incident's mitigation: reset the user's password and MFA
   (`production-credential-rotation` §1), reseal a new envelope, update the envelope log.
5. GuardDuty custom finding `BreakGlassUsed` and the CloudTrail Lake query for the session
   are attached to the postmortem.

## Detection

Any `ConsoleLogin` or `AssumeRole` by these users triggers a `sec-oncall` page and a
Security Hub CRITICAL finding — even when legitimate. Silence is a bug.

## Review

Every use is reviewed by the Head of SecEng within 2 business days; envelope integrity is
audited quarterly.
