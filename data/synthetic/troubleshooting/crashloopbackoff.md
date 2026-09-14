---
document_id: crashloopbackoff
title: "Troubleshooting: CrashLoopBackOff"
source: acme
document_type: troubleshooting
environment: all
permissions: [developer, platform-engineer, security-admin]
status: active
created_at: 2025-05-19
updated_at: 2025-08-03
tags: [kubernetes, crashloopbackoff, exit-codes, oomkilled, probes]
related: [kubernetes-crashloop, oomkilled]
---
# Troubleshooting: CrashLoopBackOff

A pod shows `CrashLoopBackOff` when its container keeps exiting and kubelet is backing off
before the next restart (delay doubles from 10 s up to 5 minutes). The pod *was scheduled*
and the image *was pulled* — the problem is inside the container or its configuration.

## Find the exit reason

```bash
kubectl get pod <pod> -n <ns> -o jsonpath='{.status.containerStatuses[0].lastState.terminated}'
kubectl logs <pod> -n <ns> --previous
kubectl describe pod <pod> -n <ns> | grep -iE "reason|exit code|probe"
```

## Exit codes seen at Acme

- **1** — application error at startup. Nine times out of ten: a missing environment variable
  or ConfigMap key after a chart refactor, or a database that isn't reachable yet.
- **137** — killed. If `Reason: OOMKilled`, the memory limit is too low or there is a leak.
  If not OOMKilled, the liveness probe killed it (look for `Liveness probe failed` events).
- **139** — segmentation fault; almost always a musl/glibc mismatch from an alpine base image.
- **143** — SIGTERM; the container is being restarted deliberately (probe or eviction).
- **0** — the process finished. Deployments must run a long-lived process; a CLI job belongs in a
  `Job`/`CronJob`.

## Fixes

| Cause | Fix |
|---|---|
| OOMKilled | raise `resources.limits.memory` in the Helm values; for JVM set `-XX:MaxRAMPercentage=75` |
| Liveness kill during slow start | add `startupProbe`; keep liveness independent of downstream services |
| Missing config | compare `envFrom`/`volumeMounts` in the Deployment against the ConfigMap/Secret keys; check ExternalSecret status |
| Dependency not ready | retry with backoff in the app; `initContainer` wait as a stopgap |
| Segfault | rebuild from `acme-base-debian` |

## Stop the loop while you fix it

Roll back the deploy in ArgoCD, or scale the Deployment to zero if the restarts are hurting a
shared dependency (each restart of `ledger-service` opens 40 DB connections).
