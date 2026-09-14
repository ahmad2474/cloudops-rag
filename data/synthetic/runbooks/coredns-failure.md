---
document_id: coredns-failure
title: "Runbook: In-cluster DNS resolution failures (CoreDNS)"
source: acme
document_type: runbook
environment: all
permissions: [developer, platform-engineer, security-admin]
status: active
created_at: 2025-07-08
updated_at: 2026-01-30
tags: [eks, coredns, dns, ndots, conntrack, node-local-dns]
related: [dns-failure, eks-architecture]
---
# Runbook: In-cluster DNS resolution failures (CoreDNS)

**Owner:** Platform Engineering. CoreDNS runs 2–8 replicas (autoscaled by
`cluster-proportional-autoscaler`) on the `system` node group; **NodeLocal DNSCache** is
deployed on all nodes since 2025-08 (after INC-0977).

## Symptoms

- App errors `getaddrinfo EAI_AGAIN`, `Temporary failure in name resolution`,
  `dial tcp: lookup ledger-service.ledger.svc.cluster.local: i/o timeout`
- Intermittent 5 s latency spikes (one DNS timeout = 5 s default)
- CloudWatch alarm `eks-prod-coredns-errors` (`coredns_dns_responses_total{rcode="SERVFAIL"}`)

## Triage

```bash
kubectl get pods -n kube-system -l k8s-app=kube-dns -o wide     # all Running? spread across nodes?
kubectl get pods -n kube-system -l k8s-app=node-local-dns -o wide
kubectl logs -n kube-system -l k8s-app=kube-dns --tail=100 | grep -iE "error|timeout|refused"

# From a debug pod
kubectl run -n platform dbg --rm -it --image=555555555555.dkr.ecr.us-east-1.amazonaws.com/tools/netshoot -- \
  bash -c 'cat /etc/resolv.conf; dig +short ledger-service.ledger.svc.cluster.local; dig +short ledger-pg.prod.acme.internal; dig +short api.stripe.com'
```

Which lookups fail tells you where:

| Fails | Works | Where to look |
|---|---|---|
| everything | — | NodeLocal DNS on that node, or conntrack table full (`node_nf_conntrack_entries` near limit) |
| `*.svc.cluster.local` | external | CoreDNS itself (crashloop, OOM, `kubernetes` plugin API errors) |
| `*.acme.internal` | cluster + public | Route 53 resolver / VPC DHCP options; check `forward . /etc/resolv.conf` in Corefile |
| public names | internal | NAT/egress or the `.:53 forward` upstream; see VPC endpoints for AWS APIs |

## Common causes at Acme

1. **CoreDNS OOM** after a burst of lookups — limit is 170Mi; the autoscaler adds replicas by
   node count, not QPS. Bump replicas manually (`kubectl scale deploy coredns -n kube-system --replicas=8`)
   then fix the Corefile `cache` TTL.
2. **ndots:5 amplification** — a lookup for `api.stripe.com` tries 5 suffixes first. Services
   doing many external calls should set `dnsConfig.options: [{name: ndots, value: "2"}]` or
   use FQDNs with a trailing dot. Enforced by `kubernetes-workload-standards` for external callers.
3. **conntrack exhaustion on a node** — UDP DNS entries pile up; NodeLocal DNS uses TCP to
   upstream to avoid this; if a node lacks the DaemonSet pod (taint mismatch after a new node
   group), that node suffers.
4. **CoreDNS pods all on one node** — anti-affinity was removed in a chart bump once (2025-07).
   Should be `topologySpreadConstraints` across nodes/zones.

## Fix / mitigate

- Restart CoreDNS: `kubectl rollout restart deploy coredns -n kube-system` (safe; NodeLocal caches for 30 s).
- Node-specific: cordon + drain the node.

## Verification

`dig` from three pods in different AZs all < 10 ms; SERVFAIL rate 0 for 15 min.
