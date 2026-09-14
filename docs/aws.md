# AWS demo environment (Phase 10–11)

Everything here is **temporary**: it exists for the demo window, then `make tf-destroy`.
Rules from `CLAUDE.md`: no NAT Gateway, no OpenSearch Serverless, t3.small class only,
`plan → cost estimate → approval → apply`, destroy the same day the demo ends.

## Topology

```
operator /32 ──HTTP:80──▶ EC2 t3.small (public subnet, IMDSv2, SSM — no SSH)
                           ├─ caddy   :80   /api/* → api:8000, /* → web:3000
                           ├─ api     :8000 FastAPI  ── SigV4 ──▶ OpenSearch t3.small.search (VPC, HTTPS)
                           └─ web     :3000 Next.js            └─▶ Bedrock (Titan V2, Nova Lite, Cohere Rerank 3.5)
images ◀── ECR (api, web)      secrets ◀── SSM Parameter Store (SecureString)
logs   ──▶ CloudWatch /cloudops-rag-demo/app     reports ──▶ S3 (private, versioned)
alarms ──▶ SNS email: EstimatedCharges > threshold
```

Why no NAT: the single instance has a public IP and reaches ECR/Bedrock/SSM/S3 through the
internet gateway. A NAT Gateway would add ~$1.10/day for nothing.

Why SigV4 instead of an OpenSearch master password: the instance role is trusted by the
domain access policy, so there is no second secret to manage (`OPENSEARCH_AUTH=sigv4`).

Why ECR instead of building on the box: a 2 GB instance cannot build Next.js; images are
built on the developer machine with `docker buildx --platform linux/amd64` (`make aws-push`).

## Cost estimate

On-demand list prices, us-east-1, checked 2026-09. **Estimates, not billing** — actual spend
is read with `make aws-cost` (Cost Explorer) and recorded in the README after the demo.

| Resource | Rate | Per day | 3-day demo |
|---|---:|---:|---:|
| OpenSearch `t3.small.search` × 1 | $0.036/h | $0.86 | $2.59 |
| OpenSearch gp3 10 GB | $0.122/GB-mo | $0.04 | $0.12 |
| EC2 `t3.small` | $0.0208/h | $0.50 | $1.50 |
| EBS gp3 20 GB | $0.08/GB-mo | $0.05 | $0.16 |
| Public IPv4 | $0.005/h | $0.12 | $0.36 |
| ECR (~0.8 GB) | $0.10/GB-mo | <$0.01 | $0.01 |
| CloudWatch logs (<1 GB) + 1 alarm | $0.50/GB, $0.10/alarm-mo | <$0.02 | $0.05 |
| S3, SSM, SNS | — | ≈ $0 | ≈ $0 |
| **Infrastructure** | | **≈ $1.60/day** | **≈ $4.80** |

Per-run Bedrock costs (from `src/cloudops_rag/observability/pricing.py`):

| Run | Volume | Estimate |
|---|---|---:|
| Full corpus embedding (Titan V2) | ~446k tokens | $0.01 |
| Evaluation, 315 questions, retrieval only | 315 embeds | <$0.01 |
| Evaluation with Cohere rerank | 315 rerank queries | $0.63 |
| Evaluation with generation (Nova Lite, ~3.3k in / 200 out per question) | ~1.1M tokens | $0.08 |
| Load test, 500 questions, full pipeline | 500 × (rerank + LLM) | ≈ $1.15 |

A complete Phase 11 (index, four strategy evals with and without rerank, generation eval,
security + load tests, two days of infrastructure) lands around **$10–15** against the $150
ceiling and the spec §52 envelopes (OpenSearch $25–50, compute $10–20, reranking $5–15).

## Operator runbook

Prerequisites: an AWS profile with permissions to create the resources above (the
`cloudops-rag-dev` user only has Bedrock + Cost Explorer; use an admin profile for Terraform),
Docker with buildx, and Bedrock quotas > 0 for Titan V2 and Nova Lite.

```sh
cp infrastructure/terraform/environments/demo.tfvars.example infrastructure/terraform/environments/demo.tfvars
# fill allowed_cidr (curl -s https://checkip.amazonaws.com), alarm_email, auth_secret
# (openssl rand -hex 32), auth_users_json (make auth-demo)

make tf-init
make tf-plan                      # 1st pass: image_tag can be any string; ECR must exist before push
make tf-apply                     # type yes — creates VPC, ECR, S3, IAM, OpenSearch (~15 min), EC2
make aws-push                     # builds + pushes; prints image_tag → put it in demo.tfvars
make tf-plan && make tf-apply     # user_data changes → instance is replaced with the real images
make tf-output                    # console_url, instance_id
```

Confirm the SNS subscription email. Then, on the instance (no SSH — SSM):

```sh
aws ssm start-session --target <instance_id>
sudo docker compose --env-file /opt/cloudops/.compose.env -f /opt/cloudops/compose.yml \
  exec api python apps/ingestion/index_corpus.py --full        # ≈ $0.01
sudo docker compose ... exec api python apps/evaluation/run.py --strategy hybrid_rrf --rerank
```

Copy `evaluation/reports/*` to S3 (`aws s3 sync … s3://<corpus_bucket>/reports/`), take the
numbers into `docs/evaluation.md` and the README, record the demo, then:

```sh
make aws-cost        # what it actually cost — goes in the README
make tf-destroy      # same day
```

Retained after destroy: nothing billable. ECR repos and the bucket are `force_destroy`;
the log group is deleted with the stack; SSM parameters are deleted; the service-linked role
for OpenSearch stays (free).

## Security posture (demo-grade, deliberately)

- Ingress: TCP 80 from one operator `/32`; no SSH; SSM Session Manager for shell.
- Plain HTTP to a raw public IP — no domain, so no TLS. Tokens travel over HTTP during the
  demo; the demo users are fictional and the environment is destroyed afterwards. A real
  deployment would front this with an ALB + ACM certificate.
- Instance role is scoped to the two ECR repos, one bucket, one log group, `/cloudops-rag-demo/*`
  parameters, three Bedrock models (+ `us.amazon.*` inference profiles), and one domain.
- IMDSv2 required, encrypted root volume, OpenSearch encrypted at rest + in transit, HTTPS-only.
- Accepted scanner findings are listed with reasons in `infrastructure/terraform/.trivyignore`.
