---
document_id: production-vpc
title: "Architecture: Production VPC (vpc-prod-use1)"
source: acme
document_type: architecture
environment: production
permissions: [developer, platform-engineer, security-admin]
status: active
created_at: 2025-03-05
updated_at: 2025-10-01
tags: [vpc, subnets, cidr, nat-gateway, vpc-endpoints, flow-logs, custom-networking]
related: [eks-architecture, multi-region-dr, eks-pod-networking, postmortem-inc-0981]
---
# Architecture: Production VPC (`vpc-prod-use1`)

Region us-east-1, CIDR **10.40.0.0/16** plus secondary CIDR **100.64.0.0/16** (added
2025-09-09 for EKS pod networking). Managed by `modules/acme-vpc`, stack
`stacks/acme-prod/us-east-1/network`.

## Subnet plan

| Tier | us-east-1a | us-east-1b | us-east-1c | Route table |
|---|---|---|---|---|
| public | 10.40.0.0/24 | 10.40.1.0/24 | 10.40.2.0/24 | IGW default; hosts ALB/NLB, NAT GW per AZ |
| private-app | 10.40.16.0/20 | 10.40.32.0/20 | 10.40.48.0/20 | NAT GW of the same AZ; S3/DynamoDB gateway endpoints |
| private-data | 10.40.64.0/24 | 10.40.65.0/24 | 10.40.66.0/24 | **no** default route (no internet) |
| pod | 100.64.0.0/18 | 100.64.64.0/18 | 100.64.128.0/18 | same as private-app |

Private-app subnets hold EKS node primary ENIs (~4k addresses each). Pod ENIs live in the
pod subnets (~16k each) via VPC CNI custom networking. Before Sep 2025 pods took IPs from
private-app, which exhausted at ~3,600 pods (INC-0981).

Tags: `acme:tier` = `public|private-app|private-data|pod`; `kubernetes.io/role/elb=1` on public,
`kubernetes.io/role/internal-elb=1` on private-app (AWS Load Balancer Controller discovery).

## Egress

One NAT Gateway per AZ (`nat-prod-use1-{a,b,c}`); AZ-local routing avoids cross-AZ charges and
survives a single-AZ NAT failure for the other AZs. Monthly NAT data processing is the largest
network cost line; VPC endpoints exist to keep AWS API traffic off NAT:

`s3` (gateway), `dynamodb` (gateway), `ecr.api`, `ecr.dkr`, `sts`, `logs`, `secretsmanager`,
`kms`, `ec2`, `monitoring`, `elasticloadbalancing`, `autoscaling`. Interface endpoints use SG
`sg-prod-vpce` allowing 443 from the VPC CIDRs. Private DNS enabled.

## Security groups (core)

| SG | Purpose | Ingress |
|---|---|---|
| `sg-prod-eks-cluster` | EKS control plane ENIs | 443 from node SG |
| `sg-prod-eks-node` | all nodes | all from self + cluster SG; 443/10250 from cluster SG |
| `sg-prod-rds-<inst>` | each RDS instance | 5432 from node SG (+ pod SGs for `risk`) |
| `sg-prod-alb-public` | internet ALB | 443 from 0.0.0.0/0 (WAF in front) |
| `sg-prod-vpce` | interface endpoints | 443 from 10.40.0.0/16, 100.64.0.0/16 |

NACLs are default-allow; enforcement is at SG and NetworkPolicy level.

## Connectivity

- Transit Gateway `tgw-acme-core` attaches prod, staging (read-only routes), DR (`10.50.0.0/16`),
  and the `acme-shared` VPC (ArgoCD/Atlantis reach the cluster API over private endpoints).
- EKS API endpoint: **private only** (public access disabled since 2025-02).
- No VPC peering; no Direct Connect; office access via Tailscale subnet router in `acme-shared`.

## Observability

Flow logs (ALL, 1-min) → `acme-prod-vpc-flow-logs` (S3, Athena table `vpc_flow_logs`).
Reachability Analyzer paths saved for `alb→payments-api`, `payments-api→prod-payments-pg`.

## Known limits / gotchas

- Interface endpoints are **per-AZ**; a workload pinned to an AZ without an endpoint ENI takes
  the NAT path and may hit the `aws:sourceVpce` bucket policy denies (`s3-access-denied` §2).
- Private-data subnets are /24 — 251 usable each; fine for RDS + ElastiCache, not for anything
  that scales horizontally.
