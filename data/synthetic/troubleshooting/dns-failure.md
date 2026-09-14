---
document_id: dns-failure
title: "Troubleshooting: DNS resolution failures from pods"
source: acme
document_type: troubleshooting
environment: all
permissions: [developer, platform-engineer, security-admin]
status: active
created_at: 2025-08-01
updated_at: 2025-09-10
tags: [dns, coredns, ndots, resolv-conf, route53, eai_again]
related: [coredns-failure, production-vpc]
---
# Troubleshooting: DNS resolution failures from pods

Quick reference for developers. Platform-level diagnosis is in `coredns-failure`.

## Errors and what they usually mean

| Error | Meaning |
|---|---|
| `EAI_AGAIN` / `Temporary failure in name resolution` | resolver timed out (CoreDNS/NodeLocal unreachable or overloaded) |
| `NXDOMAIN` for a service | wrong namespace or Service name; remember `<svc>.<ns>.svc.cluster.local` |
| `NXDOMAIN` for `*.prod.acme.internal` | the Route 53 private zone isn't associated with this VPC (staging/dev use `*.staging.acme.internal`) |
| Works with FQDN + trailing dot, fails without | `ndots:5` search-path amplification; set `ndots:2` |
| Slow (≈5 s) then succeeds | one UDP timeout before retry; conntrack or a single unhealthy CoreDNS pod |

## Check from inside the pod

```bash
cat /etc/resolv.conf                       # nameserver should be 169.254.20.10 (NodeLocal)
nslookup ledger-service.ledger.svc.cluster.local
nslookup ledger-pg.prod.acme.internal
nslookup api.stripe.com.
```

## Things developers can fix themselves

- Use the full service name across namespaces.
- Add to the pod spec for external-heavy services:
  ```yaml
  dnsConfig:
    options: [{ name: ndots, value: "2" }]
  ```
- Don't hard-code RDS endpoints; use `<name>-pg.prod.acme.internal` (TTL 30 s) so failover works.

Anything else → `#platform` with the pod name and the exact error.
