---
document_id: karpenter-node-provisioning
title: "Runbook: Karpenter not provisioning or over-consolidating nodes"
source: acme
document_type: runbook
environment: production
permissions: [developer, platform-engineer, security-admin]
status: active
created_at: 2026-03-02
updated_at: 2026-07-14
tags: [eks, karpenter, nodepool, consolidation, spot, pending, max-pods, eni]
related: [eks-pod-networking, eks-architecture, postmortem-inc-1042, pods-pending]
---
# Runbook: Karpenter not provisioning or over-consolidating nodes

**Owner:** Platform Engineering. Karpenter **v1.1** runs in `karpenter` namespace on the
`system` node group. NodePools: `general-spot` (spot + on-demand fallback, `m6i`/`m6a`/`m7i`
`large`–`4xlarge`), `memory-od` (on-demand `r6i.2xlarge`+, taint `workload=memory`).

## Symptom: pods Pending, Karpenter not launching

```bash
kubectl logs -n karpenter deploy/karpenter --since=10m | grep -iE "error|could not schedule|limit|insufficient"
kubectl get nodeclaims
kubectl get nodepool general-spot -o jsonpath='{.status.resources}{"\n"}{.spec.limits}'
```

| Log message | Cause | Fix |
|---|---|---|
| `no instance type satisfied requirements` | pod requests exceed largest allowed type, or unsatisfiable affinity | fix the pod spec; `memory` workloads need the `workload=memory` toleration and `nodeSelector` |
| `exceeded NodePool limits` | `limits.cpu: 800` reached | raise limit in Terraform (`stacks/…/eks/karpenter.tf`) — cost review first |
| `InsufficientInstanceCapacity` / `SpotMaxPriceTooLow` | AZ spot capacity | Karpenter retries other types/AZs automatically; if persistent, temporarily add on-demand via `capacity-type` requirement |
| `AccessDenied` on `RunInstances` / `CreateFleet` | IRSA role `acme-prod-irsa-karpenter` drifted | restore via Terraform |
| `subnet … no available IPs` | pod-subnet exhaustion | `eks-pod-networking` §A |
| nothing at all | Karpenter itself unhealthy (evicted from `system` nodes?) | `kubectl get pods -n karpenter`; the `system` group has 3 nodes + PDB |

## Symptom: nodes churn, pods restart every few minutes

Consolidation is too aggressive. Since INC-1042 the `general-spot` NodePool has:

```yaml
disruption:
  consolidationPolicy: WhenEmptyOrUnderutilized
  consolidateAfter: 5m
  budgets:
    - nodes: "10%"
    - nodes: "0"
      schedule: "0 13 * * 1-5"   # no consolidation 13:00–17:00 UTC (peak)
      duration: 4h
```

A PR that removes `consolidateAfter` or the budgets will re-introduce churn. Workloads that
must not be disrupted carry `karpenter.sh/do-not-disrupt: "true"` (only `data-pipeline`
drivers are allowed to; PDBs are the right tool for everything else).

## Symptom: pods Pending on a node that has CPU free

Node hit its **pod IP / ENI limit**. `m6i.large` supports 3 ENIs; with prefix delegation the
AMI's max-pods calc gives 110 but only if the `EC2NodeClass` sets:

```yaml
kubelet:
  maxPods: 110   # computed via max-pods-calculator with --cni-prefix-delegation-enabled
```

INC-1042: Karpenter consolidated onto `m6i.large` nodes whose `maxPods` had been left at the
non-prefix default (29). Check `kubectl get node <n> -o jsonpath='{.status.allocatable.pods}'`.
Fix: correct the NodeClass, then drift replaces nodes.

## Verification

`kubectl get pods -A --field-selector status.phase=Pending` empty; `karpenter_nodeclaims_*`
metrics steady in Grafana `EKS / Karpenter`.
