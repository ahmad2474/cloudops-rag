---
document_id: high-cpu-incident
title: "Runbook: High CPU on EKS workloads and nodes"
source: acme
document_type: runbook
environment: production
permissions: [developer, platform-engineer, security-admin]
status: active
created_at: 2025-03-20
updated_at: 2026-01-22
tags: [eks, cpu, throttling, hpa, karpenter, performance]
related: [cpu-throttling, eks-architecture, kubernetes-workload-standards]
---
# Runbook: High CPU on EKS workloads and nodes

**Owner:** Platform Engineering (nodes) / owning team (workload) · **Page:** owning team on-call first.

## Symptoms

- Grafana `EKS / Cluster Overview` → node CPU > 85% sustained 10 min (alarm `eks-prod-node-cpu-high`)
- Latency SLO burn on a service with `container_cpu_cfs_throttled_periods_total` climbing
- HPA at `maxReplicas` (`kubectl get hpa -A` shows `REPLICAS == MAXPODS`)

## Triage

```bash
# Which pods, which nodes
kubectl top pods -A --sort-by=cpu | head -20
kubectl top nodes

# Is it throttling rather than saturation? (limits too low)
kubectl get --raw /api/v1/nodes/<node>/proxy/metrics/cadvisor \
  | grep container_cpu_cfs_throttled_periods_total | grep <pod-prefix>

# HPA state
kubectl describe hpa <name> -n <ns> | sed -n '/Metrics/,/Events/p'
```

Distinguish three cases:

| Case | Signal | Action |
|---|---|---|
| Workload is genuinely busy | CPU usage ≈ request, HPA scaling | Raise `maxReplicas`; check Karpenter has headroom |
| Workload is throttled | usage ≪ limit but throttling high | Raise CPU **limit** (or remove it — see `cpu-throttling`); do not raise replicas |
| Node-level noisy neighbour | one pod at 3–4 cores, no limit set | Kyverno policy `require-requests-limits` should have blocked it; add limit and re-deploy |

## Immediate mitigations

1. **Scale out**: `kubectl scale deploy/<name> -n <ns> --replicas=<n>` only if HPA is *not*
   managing it; otherwise patch the HPA `maxReplicas` via the Helm values in ArgoCD (fast path:
   `kubectl patch hpa` then reconcile the chart within the hour).
2. **Node pressure**: Karpenter should provision within ~90 s. If not, check
   `kubectl logs -n karpenter deploy/karpenter | grep -i "insufficient\|limit"` —
   NodePool `general-spot` has a `limits.cpu: 800` guard.
3. **Runaway pod**: `kubectl delete pod` is acceptable for a single pod; for a deployment-wide
   regression, roll back in ArgoCD.

## Known culprits

- `fraud-scoring` model reload (every deploy) pins 2 cores for ~3 min — expected.
- `reporting-api` month-end aggregation (1st of month 00:00–02:00 UTC) — expected; PDB allows 1.
- `data-pipeline` Spark drivers scheduled on `general` instead of `memory` (missing toleration).

## Escalation

SEV-3 if only internal; SEV-2 if a customer-facing SLO is burning.
