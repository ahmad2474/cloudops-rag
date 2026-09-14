---
document_id: kubernetes-crashloop
title: "Runbook: Pod in CrashLoopBackOff"
source: acme
document_type: runbook
environment: all
permissions: [developer, platform-engineer, security-admin]
status: active
created_at: 2025-03-28
updated_at: 2025-12-09
tags: [kubernetes, crashloopbackoff, oomkilled, probes, configmap, secrets]
related: [crashloopbackoff, oomkilled, kubernetes-workload-standards]
---
# Runbook: Pod in CrashLoopBackOff

**Owner:** owning team · PE assists.

`CrashLoopBackOff` means the container **started and exited**, repeatedly; kubelet backs off
(10 s → 5 min). It is *not* a scheduling or image-pull problem (those are `Pending` /
`ImagePullBackOff`).

## Step 1 — Why did the last container exit?

```bash
kubectl describe pod <pod> -n <ns> | grep -A8 "Last State"
kubectl logs <pod> -n <ns> --previous --tail=100
```

| Exit code | Meaning | Usual cause at Acme |
|---|---|---|
| 0 | ran to completion | a Job image deployed as a Deployment; `command` missing |
| 1 | app error | config/env missing, DB unreachable at startup |
| 137 | SIGKILL | **OOMKilled** (check `Reason: OOMKilled`) or liveness probe kill |
| 139 | SIGSEGV | native lib / glibc vs musl (alpine images) |
| 143 | SIGTERM | graceful shutdown then restart — usually probe failure |

## Step 2 — Map to a fix

### OOMKilled (137, `Reason: OOMKilled`)
Memory **limit** too low, or a leak. `kubectl top pod` just before the kill if you can catch it;
otherwise Grafana `container_memory_working_set_bytes` vs limit. Raise limit in the Helm
values (ArgoCD) — do not `kubectl edit` in prod; the next sync reverts it.
JVM services: ensure `-XX:MaxRAMPercentage=75` so the heap respects the cgroup.

### Liveness probe killing a slow starter (143 or 137 without OOMKilled)
Events show `Liveness probe failed`. Add a `startupProbe` (failureThreshold × period ≥ startup
time) rather than loosening liveness. `identity-service` needs ~40 s for JWKS warm-up.

### Missing config / secret (exit 1 immediately)
Logs show `KeyError`, `undefined`, `no such file`. Check:
`kubectl get configmap,secret -n <ns>` and ExternalSecret status (`SecretSynced`).
A ConfigMap renamed in the chart but not in the Deployment env is the classic.

### Dependency not ready (exit 1 after ~30 s)
App fails fast when DB/Redis unreachable at boot. Prefer retry-with-backoff in the app; as a
stopgap an `initContainer` that waits for the dependency.

### Segfault (139)
Image built on `alpine` running a glibc binary (or vice versa). Rebuild from the
`acme-base-debian` image.

## Step 3 — Stop the bleeding

- Roll back in ArgoCD if it started with a deploy.
- If the loop hammers a dependency (DB connections churn), scale to 0 while fixing:
  `kubectl scale deploy/<name> -n <ns> --replicas=0`.

## Don't

- Don't delete the pod expecting a different outcome; the Deployment recreates it identically.
- Don't set `restartPolicy: Never` on a Deployment (invalid).
