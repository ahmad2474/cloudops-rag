---
document_id: eks-cluster-upgrade-1-29
title: "Runbook: EKS cluster version upgrade (1.28 → 1.29)"
source: acme
document_type: runbook
version: "1.29"
environment: production
permissions: [platform-engineer, security-admin]
status: deprecated
created_at: 2025-04-20
updated_at: 2025-05-08
tags: [eks, upgrade, kubernetes-versions, add-ons]
related: [eks-architecture]
---
# Runbook: EKS cluster version upgrade (1.28 → 1.29)

> **DEPRECATED.** Superseded by `eks-cluster-upgrade` (1.31). Retained because the 1.29 upgrade
> of 2025-05-06 is referenced by audit.

## Pre-flight

1. Deprecated APIs: 1.29 removed `flowcontrol.apiserver.k8s.io/v1beta2`. Run `pluto`.
2. Add-ons: VPC CNI 1.16.x, CoreDNS 1.11.1-eksbuild.4, kube-proxy 1.29.x.
3. Node AMI: **AL2** `amazon-eks-node-1.29-v20250501`. (AL2023 is not yet approved at Acme.)
4. Karpenter is **not** in use; all capacity is managed node groups + Cluster Autoscaler
   (`cluster-autoscaler` 1.29.0).

## Procedure

Control plane via `aws eks update-cluster-version`, then add-ons, then node groups
(`system`, `general`, `memory`). Cluster Autoscaler must be scaled to 0 during node group
rollouts to avoid fighting the rolling update, then restored.

## Rollback

Node groups: `--release-version` previous. Control plane: none.
