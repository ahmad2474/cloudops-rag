---
document_id: kubernetes-workload-standards
title: "Policy: Kubernetes workload standards (prod)"
source: acme
document_type: policy
version: "1.6"
environment: production
permissions: [developer, platform-engineer, security-admin]
status: active
created_at: 2025-04-01
updated_at: 2026-05-28
tags: [policy, kubernetes, kyverno, requests, limits, probes, pdb, ndots, images, reloader]
related: [eks-architecture, kubernetes-crashloop, cpu-throttling, high-cpu-incident]
---
# Policy: Kubernetes workload standards

Enforced by Kyverno in staging/prod (audit in dev). PRs that violate these fail at
`helm template` lint in CI before reaching a cluster.

| # | Standard | Kyverno policy | Why |
|---|---|---|---|
| 1 | CPU/memory **requests** and memory **limits** on every container. CPU limits **optional** (see 2) | `require-requests-limits` | scheduling accuracy, OOM containment |
| 2 | CPU limits, if set, ≥ 2× request; latency-sensitive services (`payments-api`, `identity-service`, `checkout-web`) **do not set CPU limits** | — (review) | CFS throttling caused INC-0930, INC-1019 |
| 3 | Readiness probe required; liveness probe must not depend on downstreams | `require-readiness-probe` | rollout safety; avoid cascading restarts |
| 4 | `startupProbe` for anything with > 20 s boot | — (review) | |
| 5 | PDB for every Deployment with > 1 replica, `maxUnavailable` ≥ 1 (never `minAvailable == replicas`) | `require-pdb-for-multi-replica` | node rollouts must not block (2025-11 upgrade) |
| 6 | Images only from `555555555555.dkr.ecr.us-east-1.amazonaws.com`, pinned by tag = git SHA, cosign-signed | `require-acme-ecr`, `disallow-latest-tag`, `verify-images` | supply chain |
| 7 | `topologySpreadConstraints` across zones for ≥ 3 replicas | — (review) | AZ resilience |
| 8 | `dnsConfig.options ndots:2` for services making external HTTP calls | — (review) | DNS amplification (see `coredns-failure`) |
| 9 | Reloader annotation `reloader.stakater.com/auto: "true"` for anything consuming ESO secrets without pool refresh | — (review) | secret rotation |
| 10 | No `hostNetwork`, `hostPath`, `privileged`; no `NET_ADMIN` | `disallow-privileged`, `restrict-hostpath` | isolation |
| 11 | `terminationGracePeriodSeconds` ≥ 30 and SIGTERM handling that drains in-flight requests | — (review) | zero-error deploys |
| 12 | Namespace default-deny NetworkPolicy with explicit allows | — (platform-managed) | PCI segmentation |
| 13 | Memory-heavy jobs (> 8 Gi) target the `memory` pool: toleration `workload=memory` + nodeSelector | — (review) | keep `general` nodes healthy |

Exceptions: PR to `acme-deploy` with label `policy-exception`, approved by PE + SecEng, expiry
date mandatory (max 90 days).
