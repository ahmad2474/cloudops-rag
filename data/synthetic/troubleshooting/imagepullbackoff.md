---
document_id: imagepullbackoff
title: "Troubleshooting: ImagePullBackOff / ErrImagePull"
source: acme
document_type: troubleshooting
environment: all
permissions: [developer, platform-engineer, security-admin]
status: active
created_at: 2025-05-22
updated_at: 2026-05-20
tags: [kubernetes, ecr, imagepullbackoff, kyverno, cosign, vpc-endpoint]
related: [delivery-pipeline, kubernetes-workload-standards, s3-access-denied]
---
# Troubleshooting: ImagePullBackOff / ErrImagePull

```bash
kubectl describe pod <pod> -n <ns> | grep -A3 -iE "failed to pull|pull image"
```

| Message | Cause | Fix |
|---|---|---|
| `manifest unknown` / `not found` | tag doesn't exist in ECR (build didn't push, or typo in values) | check the GitHub Actions run; `aws ecr describe-images --repository-name <svc> --image-ids imageTag=<sha>` |
| `denied: User: … is not authorized to perform: ecr:BatchGetImage` | node role lost ECR pull permission, or image is in the wrong account (`acme-prod` ECR doesn't exist — images live in `acme-shared` 555555555555) | fix the registry host in values |
| `dial tcp … i/o timeout` on `*.dkr.ecr.us-east-1.amazonaws.com` | ECR interface endpoints or NAT path broken for that AZ | `production-vpc` endpoints; `#platform` |
| `context deadline exceeded` on very large images | image > 4 GB (ML models baked in) | move models to S3 + init container; `data-pipeline` pattern |
| Pod rejected before pull: `admission webhook "validate.kyverno.svc-fail" denied … require-acme-ecr` | image not from Acme ECR, or `:latest`, or unsigned (prod, since 2026-05) | build through the pipeline; no `docker push` from laptops |
| `toomanyrequests` from a public registry | someone referenced `docker.io` directly | mirror through ECR pull-through cache `555555555555.dkr.ecr.us-east-1.amazonaws.com/dockerhub/<image>` |

Staging and prod pull with the **node** role (`AmazonEC2ContainerRegistryReadOnly`); no
`imagePullSecrets` needed or allowed.
