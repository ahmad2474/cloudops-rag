---
document_id: postmortem-inc-1042
title: "Postmortem INC-1042: pods Pending with idle capacity (Karpenter consolidation + ENI limits)"
source: acme
document_type: postmortem
environment: production
permissions: [developer, platform-engineer, security-admin]
status: active
created_at: 2026-02-16
updated_at: 2026-02-24
tags: [postmortem, sev-2, eks, karpenter, consolidation, eni, max-pods, pending]
related: [inc-1042, karpenter-node-provisioning, eks-pod-networking, pods-pending]
---
# Postmortem: INC-1042 — pods Pending with idle capacity

**Date:** 2026-02-11 · **Severity:** SEV-2 · **Duration:** 10:31–12:05 UTC (94 min) ·
**IC:** pe-oncall · **Authors:** Platform Engineering

## Impact

`notification-worker` and `webhook-dispatcher` could not scale out for ~90 min during a
merchant webhook storm; webhook delivery p95 rose from 4 s to 6 min; 0 lost (queued).
Symptoms looked like INC-0981 (Pending pods, `failed to assign an IP address`), but subnet
IP headroom was > 40k and node CPU averaged 31%.

## Timeline (UTC)

- 2026-02-09 Karpenter `general-spot` NodePool enabled for burst (shakedown of the 2026-03 migration).
- 10:20 Webhook storm; HPA scales `webhook-dispatcher` 8 → 40.
- 10:31 22 pods Pending on nodes with free CPU/memory: `Too many pods` in scheduler events for some, `failed to assign an IP address` for others. **Page.**
- 10:40 Checked subnets (fine), ipamd (`awscni_no_available_ip_addresses` > 0 on 6 nodes — all `m6i.large`, all Karpenter-launched).
- 10:52 `kubectl get node -o jsonpath='{.status.allocatable.pods}'` → **29** on Karpenter `m6i.large` nodes vs 110 on MNG nodes.
- 11:05 Root cause identified: `EC2NodeClass` lacked `kubelet.maxPods`; Karpenter computed max-pods **without** prefix delegation (29 for `m6i.large`) while ipamd allocated prefixes assuming 110. Consolidation had packed pods onto these small nodes as `general` MNG scaled in overnight.
- 11:15 Mitigation: cordon all Karpenter `m6i.large` nodes; set NodePool minimum instance size to `xlarge`; Karpenter provisions 4 × `m6i.2xlarge`. Pending clears by 11:40.
- 12:05 Resolved after `maxPods: 110` added to the NodeClass and drift replaced the nodes.

## Root cause

Mismatch between Karpenter's max-pods calculation and the CNI's prefix-delegation mode. The
MNG bootstrap handles this automatically; the Karpenter NodeClass required an explicit value
that the migration checklist did not include.

## Contributing factors

- Consolidation policy `WhenUnderutilized` with no `consolidateAfter` moved workloads onto
  the smallest viable nodes aggressively, maximising exposure.
- Runbook `eks-pod-networking` (1.31) had no section for node-level ENI limits — the symptom
  matched the subnet-exhaustion section closely enough to cost ~20 min.

## Action items

| # | Action | Owner | Status |
|---|---|---|---|
| 1 | `maxPods` explicit in every `EC2NodeClass`; CI check compares with max-pods-calculator | PE | done |
| 2 | `consolidateAfter: 5m` + peak-hours disruption budget | PE | done |
| 3 | `eks-pod-networking` §B (ENI/prefix limits) and `karpenter-node-provisioning` runbook | PE | done 2026-03-04 |
| 4 | Alarm on `kube_node_status_allocatable{resource="pods"}` < 100 for any non-`system` node | PE | done |
