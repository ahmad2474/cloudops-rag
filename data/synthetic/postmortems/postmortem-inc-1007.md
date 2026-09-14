---
document_id: postmortem-inc-1007
title: "Postmortem INC-1007: risk namespace deploys blocked after 1.31 upgrade"
source: acme
document_type: postmortem
environment: production
permissions: [developer, platform-engineer, security-admin]
status: active
created_at: 2025-11-21
updated_at: 2025-11-26
tags: [postmortem, sev-3, eks, upgrade, psp, kyverno, admission, risk]
related: [inc-1007, eks-cluster-upgrade, eks-architecture]
---
# Postmortem: INC-1007 — `risk` namespace deploys blocked after the 1.31 upgrade

**Date:** 2025-11-18 · **Severity:** SEV-3 · **Duration:** 16:10–19:45 UTC ·
**IC:** pe-oncall · **Authors:** Platform Engineering, Payments (owners of `fraud-scoring`)

## Impact

`fraud-scoring` could not be deployed or rescheduled for 3.5 h. Running replicas kept
serving; a node replacement at 18:02 evicted one replica, leaving 2/3 until resolution.
No customer impact; scoring latency +15% during the 2-replica window.

## What happened

The 1.29 → 1.31 control-plane upgrade completed at 16:04. The `risk` namespace still carried a
`PodSecurityPolicy`-derived admission configuration: a legacy `psp-risk-restricted`
ClusterRole binding plus a Kyverno policy `risk-legacy-psp-bridge` written in 2024 to mirror
PSP semantics, which validated `spec.securityContext.seccompProfile` using a field path that
became strict-validated in 1.31. Every pod create in `risk` was rejected with
`admission webhook "validate.kyverno.svc-fail" denied the request: unknown field`.

## Root cause

Pre-flight tooling (`pluto`) detects removed **API versions**, not policies that embed
assumptions about admission behaviour. `risk` was the only namespace with the bridge policy
and the only namespace excluded from the staging soak (its workloads run on isolated
`memory` nodes that staging doesn't have).

## Fix

Deleted `risk-legacy-psp-bridge`; the standard Kyverno set (`disallow-privileged`,
`restrict-hostpath`, `require-requests-limits`) already covered the intent.

## Action items

| # | Action | Owner | Status |
|---|---|---|---|
| 1 | Inventory Kyverno policies per namespace; remove all "bridge" policies | PE | done |
| 2 | Staging gets a `memory` pool (2 × r6i.xlarge) so every namespace soaks | PE | done 2025-12 |
| 3 | Add `kyverno test` to the upgrade pre-flight in `eks-cluster-upgrade` | PE | done |
| 4 | `fraud-scoring` PDB `maxUnavailable: 1` (was `minAvailable: 3`) | Payments | done |
