---
document_id: cpu-throttling
title: "Troubleshooting: CPU throttling (CFS) and latency spikes"
source: acme
document_type: troubleshooting
environment: all
permissions: [developer, platform-engineer, security-admin]
status: active
created_at: 2025-06-12
updated_at: 2026-04-08
tags: [kubernetes, cpu, throttling, cfs, limits, latency, p99]
related: [high-cpu-incident, kubernetes-workload-standards]
---
# Troubleshooting: CPU throttling and latency spikes

## The symptom that fools people

Service p99 latency is bad, but `kubectl top` shows the pod using **less** CPU than its limit.
That is CFS throttling: the container burns its quota inside a 100 ms period and then waits.
Multi-threaded runtimes (JVM, Go with many goroutines, Node cluster mode) hit it hardest.

## Confirm

```promql
rate(container_cpu_cfs_throttled_periods_total{namespace="payments",container="payments-api"}[5m])
  / rate(container_cpu_cfs_periods_total{namespace="payments",container="payments-api"}[5m])
```

Anything above **25%** throttled periods correlates with visible p99 impact at Acme. Grafana
panel: `EKS / Workload Detail → CPU throttling`.

## Fix

1. Preferred for latency-sensitive services: **remove the CPU limit** (keep the request).
   Kubernetes guarantees the request; without a limit the container can use idle node CPU.
   `kubernetes-workload-standards` §2 already exempts `payments-api`, `identity-service`,
   `checkout-web`.
2. If a limit is required (batch, multi-tenant nodes): set it ≥ 2× request and ensure the
   runtime knows the quota (`-XX:ActiveProcessorCount`, `GOMAXPROCS` via `automaxprocs`).
3. Do **not** "fix" throttling by adding replicas — each replica is throttled the same way.

## History

INC-0930 (2025-05): `identity-service` p99 3× after a limit of `500m` was added "for safety".
INC-1019 (2025-12): `checkout-web` Node.js — limit `1` with 4 worker threads.
