---
document_id: pods-pending
title: "Troubleshooting: Pods stuck in Pending"
source: acme
document_type: troubleshooting
environment: all
permissions: [developer, platform-engineer, security-admin]
status: active
created_at: 2025-04-15
updated_at: 2026-03-06
tags: [kubernetes, pending, scheduling, taints, affinity, resources, pvc, ip-exhaustion, karpenter]
related: [eks-pod-networking, karpenter-node-provisioning, kubernetes-workload-standards]
---
# Troubleshooting: Pods stuck in Pending

`Pending` = the scheduler has not placed the pod, **or** it was placed but the kubelet/CNI
cannot start it. Read the events; they tell you which.

```bash
kubectl describe pod <pod> -n <ns> | sed -n '/Events/,$p'
```

| Event text | Category | What to do |
|---|---|---|
| `0/48 nodes are available: 48 Insufficient cpu` (or memory) | capacity | Karpenter should add a node within ~90 s. If not → `karpenter-node-provisioning`. Check the request isn't absurd (a 32-core request never fits `general`). |
| `… node(s) had untolerated taint {workload: memory}` / `{CriticalAddonsOnly: true}` | taints | Pod targets a tainted pool without a toleration (or the reverse: it *should* target `memory` and lacks the toleration). INC-0914 was a whole namespace with a stale toleration after a node group rename. |
| `… didn't match Pod's node affinity/selector` | affinity | A `nodeSelector` for a label that no longer exists (e.g. old node group name). |
| `… node(s) didn't match pod topology spread constraints` | spread | `maxSkew` too strict for the current node count; use `whenUnsatisfiable: ScheduleAnyway` for non-critical spreads. |
| `… node(s) had volume node affinity conflict` | storage | EBS PVC is in a different AZ than the only schedulable nodes. Delete the PVC (if data is disposable) or add capacity in that AZ. |
| `persistentvolumeclaim "x" not found` / `waiting for first consumer` | storage | PVC missing or StorageClass binding mode; check `kubectl get pvc -n <ns>`. |
| `Too many pods` | pod limit | Node hit `max-pods`; Karpenter/ENI limit (`eks-pod-networking` §B). |
| Scheduled, then `FailedCreatePodSandBox … failed to assign an IP address` | networking | Pod IP exhaustion or CNI failure → `eks-pod-networking`. |
| `exceeded quota: …` | quota | Namespace ResourceQuota; talk to PE (`platform` owns quotas). |
| `Pod's priority is lower than …` | preemption | Expected during node pressure for `priorityClassName: low`. |

## Two-minute sanity checks

```bash
kubectl get nodes                                   # any NotReady / SchedulingDisabled (cordoned)?
kubectl get nodeclaims                              # is Karpenter mid-provision?
kubectl get pods -n kube-system -l k8s-app=aws-node # CNI healthy?
kubectl get resourcequota -n <ns>
```

If the pod is Pending in **one AZ only**, think subnet/ENIConfig, not scheduler.
