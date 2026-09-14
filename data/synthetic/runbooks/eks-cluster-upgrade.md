---
document_id: eks-cluster-upgrade
title: "Runbook: EKS cluster version upgrade (to 1.31)"
source: acme
document_type: runbook
version: "1.31"
environment: production
permissions: [platform-engineer, security-admin]
status: active
supersedes: eks-cluster-upgrade-1-29
created_at: 2025-11-03
updated_at: 2026-06-10
tags: [eks, upgrade, kubernetes-versions, add-ons, deprecation, karpenter]
related: [eks-architecture, postmortem-inc-1007, eks-cluster-upgrade-1-29]
---
# Runbook: EKS cluster version upgrade (to 1.31)

**Owner:** Platform Engineering · Requires a Gatekeeper `AcmePlatformAdmin` session (4 h).
Order: `dev-use1-a` → `staging-use1-a` (soak 1 week) → `prod-usw2-a` → `prod-use1-a`.

## Pre-flight (T-1 week)

1. **Deprecated API scan**: `kubectl-convert`/`pluto detect-all-in-cluster` must be clean.
   1.29→1.31 removed `flowcontrol.apiserver.k8s.io/v1beta2` and the PSP admission we still had
   in `risk` (INC-1007). Check Kyverno policies replace every PSP intent.
2. **Add-on compatibility matrix** (`aws eks describe-addon-versions --kubernetes-version 1.31`):
   VPC CNI ≥ 1.18.3, CoreDNS ≥ 1.11.3-eksbuild.2, kube-proxy 1.31.x, EBS CSI ≥ 1.35.
3. **Karpenter**: NodeClass AMI selector must resolve a 1.31 AL2023 AMI
   (`alias: al2023@v20251110`); Karpenter ≥ 1.0 required for 1.31 (`karpenter-node-provisioning`).
4. **Insights**: `aws eks list-insights --cluster-name prod-use1-a` must show no `ERROR`.
5. Announce in `#platform` and `#eng-announce`; freeze prod deploys for the window.

## Upgrade day

```bash
# Control plane (~10–15 min, no data-plane disruption)
aws eks update-cluster-version --name prod-use1-a --kubernetes-version 1.31
aws eks describe-update --name prod-use1-a --update-id <id>

# Add-ons, in this order
for a in kube-proxy vpc-cni coredns aws-ebs-csi-driver; do
  aws eks update-addon --cluster-name prod-use1-a --addon-name $a --addon-version <ver> --resolve-conflicts PRESERVE
done

# Managed node groups (rolling; respects PDBs; ~25 min for `general`)
aws eks update-nodegroup-version --cluster-name prod-use1-a --nodegroup-name system
aws eks update-nodegroup-version --cluster-name prod-use1-a --nodegroup-name general
aws eks update-nodegroup-version --cluster-name prod-use1-a --nodegroup-name memory
```

Karpenter nodes: bump the `EC2NodeClass` AMI alias in Terraform → Karpenter **drift**
replaces nodes gradually (budget `nodes: 10%`).

## Watch during

- `kubectl get nodes -o wide` — kubelet version mix is expected; no `NotReady` > 5 min.
- PDB violations: `kubectl get events -A | grep -i "Cannot evict"` — a PDB with
  `minAvailable == replicas` blocks the rollout (found in `reporting-api` in 2025-11; fixed).
- `payments-api` p99 dashboard; canary error rate.

## Rollback

Control-plane upgrades **cannot** be rolled back. Node groups can: re-run
`update-nodegroup-version` with `--release-version <previous>`. Add-ons: `update-addon` to the
previous version. Hence the staging soak.

## Post

Update `WORLD`-facing docs (cluster table), close the change ticket, remove the deploy freeze.
