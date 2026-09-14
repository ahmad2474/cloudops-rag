---
document_id: postmortem-inc-0981
title: "Postmortem INC-0981: production pod IP exhaustion"
source: acme
document_type: postmortem
environment: production
permissions: [developer, platform-engineer, security-admin]
status: active
created_at: 2025-08-25
updated_at: 2025-09-12
tags: [postmortem, sev-1, eks, vpc-cni, ip-exhaustion, subnets, custom-networking, prefix-delegation]
related: [inc-0981, production-vpc, eks-pod-networking, eks-pod-networking-1-28]
---
# Postmortem: INC-0981 — production pod IP exhaustion

**Date:** 2025-08-19 · **Severity:** SEV-1 · **Duration:** 09:12–11:40 UTC (148 min) ·
**IC:** pe-oncall · **Authors:** Platform Engineering

## Impact

New pods could not start cluster-wide for 2.5 h. Running pods were unaffected, but every
rollout, HPA scale-out, and Karpenter-less node replacement failed. `checkout-web` had a
deploy in progress and ran at 60% capacity → p99 breached; `notification-worker` backlog of
2.1 M messages drained over the following 3 h. No payment failures (payments-api not deployed
that morning).

## Timeline (UTC)

- 08:40 `checkout-web` canary starts (adds 6 pods).
- 09:05 Pods in `us-east-1a` Pending: `failed to assign an IP address to pod`.
- 09:12 Alarm `eks-prod-ipamd-no-available-ips`. **Page.** SEV-2.
- 09:20 `AvailableIpAddressCount`: 1a = 3, 1b = 41, 1c = 27 on private-app subnets.
- 09:35 Attempt: set `WARM_IP_TARGET=5` per the 1.28-era runbook. Frees ~200 IPs in 1b/1c only; 1a nodes have no unused IPs to release.
- 09:50 Karpenter not yet in use; Cluster Autoscaler adds nodes in 1a — each new node takes 1 primary IP and immediately fails to attach secondary IPs. Worse.
- 10:05 Escalated to SEV-1 when `notification-worker` Pending count passes 200.
- 10:20 Decision: add the secondary CIDR **100.64.0.0/16** (planned for Q4) now, with custom networking. Terraform PR prepared from the existing branch.
- 10:55 `atlantis apply`: secondary CIDR + 3 pod subnets + `ENIConfig`s. VPC CNI env
  `AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG=true`, `ENI_CONFIG_LABEL_DEF=topology.kubernetes.io/zone`.
- 11:05 Nodes must be **replaced** for custom networking to take effect: rolling replacement of `general` (3 nodes at a time).
- 11:40 Pending count 0. Resolved. Prefix delegation enabled the following week (2025-09-02) after AMI max-pods validation.

## Root cause

Pods drew IPs from the /20 private-app subnets shared with node ENIs. Growth (pods 1,900 →
3,600 over 6 months) plus `WARM_ENI_TARGET=1` pre-allocation exhausted 1a first (it also hosts
the `system` group and CoreDNS, skewing pod placement). The 1.28-era runbook's mitigation
(warm-pool tuning, scale node group) assumed spare capacity that no longer existed.

## Contributing factors

- No alarm on subnet `AvailableIpAddressCount`; the ipamd alarm fires only after failure.
- The secondary-CIDR project was scheduled but not prioritised; risk had been noted in `PE-1180`.
- Adding nodes made it worse — the runbook did not warn about primary-IP consumption.

## Action items

| # | Action | Owner | Status |
|---|---|---|---|
| 1 | Secondary CIDR + custom networking in prod (done during incident), staging, DR | PE | done 2025-09-09 |
| 2 | Enable **prefix delegation**; validate max-pods on AL2023 | PE | done 2025-09-02 |
| 3 | Alarm: pod-subnet `AvailableIpAddressCount` < 2048 (warning) / < 512 (page) | PE | done |
| 4 | Rewrite `eks-pod-networking` for 1.31 + custom networking; deprecate 1.28 version | PE | done 2025-09-02 |
| 5 | Capacity review quarterly: pods, IPs, ENIs per instance type | PE | recurring |
| 6 | Karpenter adoption (faster, right-sized capacity) | PE | done 2026-03 |
