---
document_id: incident-response
title: "Policy: Incident response and severity definitions"
source: acme
document_type: policy
version: "3.0"
environment: all
permissions: [developer, platform-engineer, security-admin]
status: active
created_at: 2025-03-01
updated_at: 2026-01-12
tags: [policy, incident, severity, sev-1, postmortem, on-call, communication, statuspage]
related: [production-access, multi-region-dr]
---
# Policy: Incident response

## Severity

| Sev | Definition | Response | Comms |
|---|---|---|---|
| **SEV-1** | Customer-facing outage of a core flow (payments, checkout, login), data loss/exposure risk, or PCI control failure | Page IC + owning team + PE within 5 min; exec notified; all-hands until mitigated | Statuspage within 15 min; updates every 30 min; merchant email post-resolution |
| **SEV-2** | Major degradation (SLO fast-burn), single non-core service down, DR capability lost | Page owning team + PE; IC assigned | Statuspage if customer-visible; updates hourly |
| **SEV-3** | Minor degradation, internal tooling down, elevated errors without SLO impact | Owning team, business hours OK | Internal Slack |
| **SEV-4** | No impact; near-miss or risk found | Ticket | none |

Anyone can declare an incident (`/incident declare` in Slack → creates `#inc-<id>`,
PagerDuty incident, and the timeline doc). Down-grading requires IC agreement.

## Roles

- **Incident Commander (IC)** — owns decisions, keeps the timeline, declares mitigation and
  resolution. Not hands-on-keyboard.
- **Ops lead** — executes; may self-approve `namespace-admin` PAW sessions (see `production-access`).
- **Comms** — statuspage, merchant email, exec updates.

## During the incident

- Deploy freeze for the affected services (ArgoCD sync blocked by the `incident` label).
- Prefer rollback over forward-fix for deploy-triggered incidents.
- Record every action with a timestamp in the channel — the postmortem is built from it.

## After

- SEV-1/2: blameless postmortem within **5 business days** using the template
  (`postmortems/` in this KB), reviewed in the weekly ops review. Action items tracked with
  owners and due dates; overdue items are reported monthly.
- SEV-3: short write-up in the ticket.
- Every postmortem links the incident record (`INC-####`) and related runbooks; runbooks are
  updated as part of the action items.

## Security incidents

Suspected compromise is **always SEV-1** until SecEng downgrades it. Follow
`production-credential-rotation` (SecEng) and preserve evidence before remediation.
