---
document_id: eks-pod-networking
title: "Runbook: EKS pod networking failures (Pending pods, ENI/IP allocation, VPC CNI)"
source: acme
document_type: runbook
version: "1.31"
environment: production
permissions: [developer, platform-engineer, security-admin]
status: active
supersedes: eks-pod-networking-1-28
created_at: 2025-09-02
updated_at: 2026-03-04
tags: [eks, vpc-cni, pending, ip-exhaustion, eni, prefix-delegation, custom-networking]
related: [production-vpc, eks-architecture, pods-pending, karpenter-node-provisioning, postmortem-inc-0981, postmortem-inc-1042]
---
# Runbook: EKS pod networking failures

**Applies to:** `prod-use1-a`, `prod-usw2-a`, `staging-use1-a` on EKS **1.31** with VPC CNI ≥ 1.18,
prefix delegation enabled and custom networking on the `100.64.0.0/16` pod CIDR.
**Owner:** Platform Engineering · **Page:** `pe-oncall`

## Symptoms

- Pods stuck in `Pending` with events like
  `failed to assign an IP address to pod` or
  `add cmd: failed to assign an IP address to pod`
- `aws-node` DaemonSet pods in `CrashLoopBackOff` or `0/1 Ready`
- New nodes join but never become `Ready` (CNI never initialises)
- Cluster CPU/memory look normal; node count looks normal. **Do not assume capacity.**
- CloudWatch alarm `eks-prod-ipamd-no-available-ips` firing (metric `awscni_no_available_ip_addresses`)

## Fast triage (5 minutes)

```bash
# 1. Is it capacity or networking? Pending + "Insufficient cpu" → capacity, go to karpenter runbook.
kubectl get events -A --field-selector reason=FailedScheduling | tail -20
kubectl describe pod <pod> -n <ns> | sed -n '/Events/,$p'

# 2. CNI health
kubectl get ds aws-node -n kube-system
kubectl logs -n kube-system -l k8s-app=aws-node --tail=200 | grep -iE "error|warn|no available|prefix"

# 3. IPAM metrics on one node
kubectl exec -n kube-system <aws-node-pod> -- curl -s localhost:61678/metrics \
  | grep -E "awscni_(total_ip_addresses|assigned_ip_addresses|no_available_ip_addresses|eni_allocated)"

# 4. Subnet headroom (pod CIDR subnets)
aws ec2 describe-subnets --filters "Name=tag:acme:tier,Values=pod" \
  --query 'Subnets[].{az:AvailabilityZone,cidr:CidrBlock,free:AvailableIpAddressCount}' --output table
```

## Decision tree

| Finding | Likely cause | Go to |
|---|---|---|
| `AvailableIpAddressCount` < 256 on any pod subnet | Pod subnet exhaustion | §A |
| Free IPs fine, `awscni_no_available_ip_addresses` > 0 on a node | Node hit ENI/prefix limit | §B |
| `aws-node` CrashLoopBackOff on new nodes only | Node role / IRSA / SG for CNI | §C |
| Pods Pending only in one AZ | Subnet or AZ-specific issue | §A then §D |
| Only pods with `hostNetwork: false` in `risk` ns | NetworkPolicy / custom ENIConfig missing | §D |

### §A — Pod subnet exhaustion

Prefix delegation allocates **/28 prefixes**; a subnet fragmented by mixed workloads can report
free IPs but have no free contiguous /28. Check `awscni_no_available_ip_addresses` together with
subnet free count.

1. Confirm which AZ: `kubectl get pods -A -o wide --field-selector status.phase=Pending`.
2. Short-term: cordon nodes in the exhausted AZ so Karpenter/ASG places new pods elsewhere
   (`kubectl cordon -l topology.kubernetes.io/zone=us-east-1a`). Uncordon after.
3. Medium-term: add a new /18 from the secondary CIDR in that AZ via Terraform
   (`stacks/acme-prod/us-east-1/network`, `pod_subnets` map), then update the `ENIConfig`
   for that AZ. Atlantis plan → PE on-call approves → apply. Takes ~15 min end to end.
4. Never enable `AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG=false` in prod "to get IPs from the
   primary subnets" — that is exactly what caused INC-0981.

### §B — Node ENI / prefix limit

`m6i.xlarge` supports 4 ENIs × 15 IPs; with prefix delegation that is 4 × 14 × 16 = 896 pod IPs
(minus the primary IP per ENI). `m6i.large` supports only 3 ENIs × 10. Karpenter's
`general-spot` NodePool allows `m6i.large`; consolidation can pack pods onto small nodes
until they hit the ENI limit while CPU still looks free (INC-1042).

1. `kubectl describe node <node> | grep -A3 Allocatable` → check `pods:`; compare to running.
2. If `max-pods` is 110 but the instance can't supply that many IPs, the node is misconfigured:
   the bootstrap must compute max-pods with `--cni-prefix-delegation-enabled`. Managed node
   groups do this automatically; **custom Karpenter AMI settings must set
   `maxPods` explicitly** (see `karpenter-node-provisioning`).
3. Drain the node; Karpenter replaces it: `kubectl drain <node> --ignore-daemonsets --delete-emptydir-data`.

### §C — `aws-node` failing on new nodes

- Check IRSA: `kubectl describe sa aws-node -n kube-system` should show
  `eks.amazonaws.com/role-arn: arn:aws:iam::111111111111:role/acme-prod-irsa-vpc-cni`.
- The role needs `AmazonEKS_CNI_Policy`. If someone "cleaned up" IAM, restore via Terraform
  (`modules/acme-eks/irsa.tf`).
- Node security group must allow all traffic from the cluster SG (see
  `aws-eks-security-group-requirements` in the public docs).

### §D — Custom networking / ENIConfig

Each AZ needs an `ENIConfig` named after the AZ (`us-east-1a` …) referencing the pod subnet
and the node SG. Nodes must carry label `k8s.amazonaws.com/eniConfig` (set via
`ENI_CONFIG_LABEL_DEF=topology.kubernetes.io/zone`).

```bash
kubectl get eniconfig -o yaml | grep -E "name:|subnet:"
kubectl get node -L topology.kubernetes.io/zone
```

A missing ENIConfig for a **newly added AZ** yields pods Pending only in that AZ.

## Escalation

- After 20 min without a clear cause → page `pe-oncall` secondary, open `#inc-<id>` as SEV-2.
- If `payments-api` availability SLO burn > 2%/h → SEV-1.

## Verification

Pending count returns to 0 (`kubectl get pods -A --field-selector status.phase=Pending`),
`awscni_no_available_ip_addresses == 0` on all nodes for 10 min, alarm resolves.

## Related history

INC-0981 (2025-08, subnet exhaustion), INC-1042 (2026-02, ENI limit under Karpenter),
INC-0914 (2025-04, Pending but caused by taints — not networking).
