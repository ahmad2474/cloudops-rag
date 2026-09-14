---
document_id: eks-architecture
title: "Architecture: EKS platform (prod-use1-a)"
source: acme
document_type: architecture
version: "1.31"
environment: production
permissions: [developer, platform-engineer, security-admin]
status: active
created_at: 2025-03-05
updated_at: 2026-06-12
tags: [eks, karpenter, node-groups, add-ons, irsa, argocd, kyverno, observability]
related: [production-vpc, delivery-pipeline, kubernetes-workload-standards, karpenter-node-provisioning]
---
# Architecture: EKS platform (`prod-use1-a`)

EKS **1.31** (control plane upgraded 2025-11-18), private API endpoint, AL2023 nodes,
Terraform `modules/acme-eks`, stack `stacks/acme-prod/us-east-1/eks`.

## Compute

| Pool | Type | Size | Taints | Runs |
|---|---|---|---|---|
| `system` (MNG) | m6i.large | 3 fixed, one per AZ | `CriticalAddonsOnly=true:NoSchedule` | CoreDNS, Karpenter, ESO, cert-manager, LB controller, Kyverno, Prometheus |
| `general` (MNG) | m6i.xlarge | 6–40 | none | baseline app capacity |
| `memory` (MNG) | r6i.2xlarge | 2–12 | `workload=memory:NoSchedule` | `data-pipeline` drivers, `fraud-scoring` |
| `general-spot` (Karpenter) | m6i/m6a/m7i large–4xlarge, spot→OD | 0–800 vCPU | none | burst; consolidation windows per `karpenter-node-provisioning` |

Cluster Autoscaler was retired 2026-03 in favour of Karpenter.

## Networking

VPC CNI 1.19 with **prefix delegation** and **custom networking** (`ENIConfig` per AZ → pod
subnets in 100.64.0.0/16). Security groups for pods only in `risk` (PCI segmentation).
NetworkPolicy via VPC CNI network policy agent; default-deny ingress in every app namespace,
allow-lists per team. NodeLocal DNSCache on every node.

Ingress: AWS Load Balancer Controller → internet ALB (`checkout-web`, `payments-api` public
edge) behind WAF + Shield; internal ALB for `*.prod.acme.internal`. gRPC between services via
ClusterIP + Envoy sidecar-less (no service mesh — evaluated Istio 2025, rejected for complexity).

## Identity & secrets

- IRSA for every workload needing AWS: roles `acme-prod-irsa-<service>`, trust scoped to
  `system:serviceaccount:<ns>:<sa>`. EKS Pod Identity migration planned 2026-Q4.
- Cluster access via **EKS access entries** mapped to Identity Center permission sets;
  `AcmeDeveloper` = view in own namespaces, `AcmePlatformAdmin` = cluster-admin (Gatekeeper only).
- External Secrets Operator syncs Secrets Manager → K8s Secrets (`refreshInterval: 1h`).

## Policy (Kyverno)

`require-acme-ecr`, `require-requests-limits`, `require-readiness-probe`, `disallow-latest-tag`,
`require-pdb-for-multi-replica`, `restrict-hostpath`, `disallow-privileged`. Audit mode in
`dev`, enforce in staging/prod. These replaced PodSecurityPolicy (removed at 1.25 upstream;
Acme's last PSP dependency died in INC-1007).

## Delivery

ArgoCD (in `acme-shared`) app-of-apps per team; prod apps `syncPolicy: manual`; Argo Rollouts
canaries for `payments-api`/`checkout-web`. See `delivery-pipeline`.

## Observability

kube-prometheus-stack (15 d local retention, remote-write to Grafana Mimir in `acme-shared`),
Fluent Bit → CloudWatch Logs `/acme/prod/eks/<ns>` (30 d) → S3 archive, Container Insights,
X-Ray for `payments-api`. Alerts → PagerDuty (`pe-oncall` for platform, team rotations for app).

## Capacity numbers (2026-06)

~1,900 pods, 48 nodes typical, 110 peak. Pod IP headroom ≈ 47k. API server p99 < 100 ms.

## DR

`prod-usw2-a` mirrors this design at 30% scale; ArgoCD targets both. See `multi-region-dr`.
