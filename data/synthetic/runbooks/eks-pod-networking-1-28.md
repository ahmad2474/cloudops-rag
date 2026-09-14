---
document_id: eks-pod-networking-1-28
title: "Runbook: EKS pod networking failures (EKS 1.28)"
source: acme
document_type: runbook
version: "1.28"
environment: production
permissions: [developer, platform-engineer, security-admin]
status: deprecated
created_at: 2025-01-14
updated_at: 2025-05-02
tags: [eks, vpc-cni, pending, ip-exhaustion, warm-ip-target]
related: [production-vpc, eks-architecture]
---
# Runbook: EKS pod networking failures (EKS 1.28)

> **DEPRECATED 2025-09-02.** `prod-use1-a` no longer runs 1.28 and no longer allocates pod IPs
> from the private-app subnets. Use `eks-pod-networking` (1.31). Kept for audit history only.

**Applies to:** `prod-use1-a` on EKS 1.28, VPC CNI 1.15, secondary IPs from the
**private-app** subnets (10.40.16.0/20, 10.40.32.0/20, 10.40.48.0/20).

## Symptoms

- Pods stuck in `Pending`, `failed to assign an IP address to pod`
- `AvailableIpAddressCount` on a private-app subnet near zero

## Procedure

1. Check free IPs per private-app subnet:
   `aws ec2 describe-subnets --filters "Name=tag:acme:tier,Values=private-app"`.
2. Reduce warm pool waste. On EKS 1.28 the CNI defaults (`WARM_ENI_TARGET=1`) pre-allocate a
   whole ENI's worth of IPs per node. Set on the `aws-node` DaemonSet:
   ```
   WARM_IP_TARGET=5
   MINIMUM_IP_TARGET=10
   ```
   This frees hundreds of IPs on a 40-node cluster within minutes.
3. If still exhausted, **scale the node group down and back up** so nodes release ENIs.
4. Longer term: request a larger private-app CIDR from the network team (a /19 per AZ) —
   ticket `PE-1180`.

## Notes

- Prefix delegation is **not enabled** on 1.28 at Acme; it was evaluated in Q1 2025 and
  deferred because the AMI's max-pods calculation needed validation.
- Custom networking (secondary CIDR) is out of scope for this cluster generation.
