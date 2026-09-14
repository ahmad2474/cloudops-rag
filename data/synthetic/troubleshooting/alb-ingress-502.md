---
document_id: alb-ingress-502
title: "Troubleshooting: 502/503/504 from the ALB in front of a service"
source: acme
document_type: troubleshooting
environment: production
permissions: [developer, platform-engineer, security-admin]
status: active
created_at: 2025-10-14
updated_at: 2026-06-18
tags: [alb, ingress, "502", "503", "504", target-group, readiness, keepalive, load-balancer-controller]
related: [eks-architecture, kubernetes-workload-standards, delivery-pipeline]
---
# Troubleshooting: 502 / 503 / 504 from the ALB

Ingress is `alb.ingress.kubernetes.io/target-type: ip` (pods registered directly).

| Code | ALB meaning | Usual Acme cause | Fix |
|---|---|---|---|
| **503** | no healthy targets | rollout replaced all pods and new ones aren't Ready; readiness probe path wrong; target group health check port differs from container port | check `kubectl get endpoints <svc>`; `aws elbv2 describe-target-health`; PDB + `maxUnavailable: 0` for zero-503 rollouts |
| **502** | target closed connection / bad response | app `keepAliveTimeout` < ALB idle timeout (60 s) → ALB reuses a connection the app already closed; pod killed mid-request (no SIGTERM drain) | set app keep-alive to **65 s+** (Node: `server.keepAliveTimeout = 65000`, `headersTimeout = 66000`); `preStop: sleep 10`; `terminationGracePeriodSeconds ≥ 30` |
| **504** | target didn't respond in time | slow downstream (DB, third party), app timeout > ALB idle timeout | app-side timeouts < 60 s; check `payments-api` X-Ray traces |
| **502 bursts during deploys** | deregistration race | pod removed from endpoints but ALB still routes for up to `deregistration_delay` | `alb.ingress.kubernetes.io/target-group-attributes: deregistration_delay.timeout_seconds=30` + preStop sleep |

## Quick look

```bash
kubectl get ingress -n <ns> <name> -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
aws elbv2 describe-target-health --target-group-arn <tg>   # from the LB controller events
kubectl logs -n kube-system deploy/aws-load-balancer-controller | grep -i <ingress-name>
```

ALB access logs → `acme-prod-alb-logs` (Athena `alb_logs`): filter `elb_status_code >= 500`
and look at `target_status_code` / `target_processing_time` to split ALB-side from app-side.

## History

`checkout-web` 502s on every deploy until 2025-10 (keep-alive 5 s default in Node). INC-0999.
