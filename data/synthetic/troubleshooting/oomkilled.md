---
document_id: oomkilled
title: "Troubleshooting: OOMKilled containers"
source: acme
document_type: troubleshooting
environment: all
permissions: [developer, platform-engineer, security-admin]
status: active
created_at: 2025-07-20
updated_at: 2026-02-27
tags: [kubernetes, oomkilled, memory, limits, jvm, node, leak, vpa]
related: [crashloopbackoff, kubernetes-crashloop, kubernetes-workload-standards]
---
# Troubleshooting: OOMKilled containers

`Reason: OOMKilled`, exit code 137. The cgroup memory limit was hit and the kernel killed
the process. Requests don't matter here — only `resources.limits.memory`.

## Is it undersized or leaking?

Grafana `EKS / Workload Detail → Memory`: `container_memory_working_set_bytes` vs limit.

- Flat line just under the limit from startup → **undersized**; raise the limit.
- Slow climb over hours/days then kill → **leak**; raise the limit as a stopgap and profile.
- Spike during a specific job (report, cache warm) → size for the peak or move the work to the
  `memory` pool.

## Runtime notes

- **JVM**: heap defaults to 25% of the container limit; set `-XX:MaxRAMPercentage=75`. Leave
  ~25% for metaspace, threads, direct buffers. Native memory tracking `-XX:NativeMemoryTracking=summary`.
- **Node.js**: `--max-old-space-size` should be ~75% of the limit; V8 will otherwise happily
  grow past the cgroup.
- **Python workers** (gunicorn): memory is per worker; limit = workers × per-worker peak + headroom.
- **Go**: set `GOMEMLIMIT` to ~90% of the limit (Go 1.19+).

## Page cache is not a leak

Writing lots of files inflates `container_memory_usage_bytes` but `working_set` (what the OOM
killer uses) excludes reclaimable cache. Alert on working set.

## Data point

`ledger-service` at 2026-02: 2 Gi limit, working set 1.95 Gi at startup after a dependency
added an in-memory cache. Fixed by 3 Gi limit + cache TTL. See INC-1044.
