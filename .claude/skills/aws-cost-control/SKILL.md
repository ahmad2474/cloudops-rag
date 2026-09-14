---
name: aws-cost-control
description: Use before ANY AWS-related action — writing Terraform, running terraform plan/apply, calling Bedrock/OpenSearch/EC2/S3, or estimating cost. Enforces the $150 hard ceiling.
---

# AWS Cost Control

## Hard ceiling: $150 total AWS credits. $0 personal cash.

Budget envelopes (targets, not promises):

| Category | Target |
|---|---:|
| S3 | <$2 |
| Embeddings (Titan V2) | <$5 |
| LLM inference | $10–30 |
| Reranking | $5–15 |
| OpenSearch (managed, t3.small.search) | $25–50 |
| Compute (t3.small EC2) | $10–20 |
| CloudWatch | <$5 |
| Networking | <$5 |
| Safety reserve | $30+ |

## Rules
- **Never** create paid AWS resources without explicit user approval in the current conversation.
- **Never** deploy a NAT Gateway. **Never** use OpenSearch Serverless as always-on. **Never** EKS, ALB+NLB+APIGW combos, Lambda sprawl.
- Required flow: `terraform plan` → written cost estimate (hourly + expected-run-hours) → user approval → `terraform apply` → demo/benchmark → `terraform destroy` in the same session.
- Phases 0–9 make **zero** AWS API calls. Any `boto3` client creation must be behind the provider abstraction and gated by `LLM_PROVIDER=bedrock` etc.
- Before Phase 10: AWS Budgets alert at $50/$100/$130; `scripts/aws-cost-check.sh` prints month-to-date spend via Cost Explorer.
- Embedding the corpus and running evaluation call Bedrock — estimate tokens × price *before* running, log actual cost after.
- Dev loop stays local (Docker OpenSearch, stub providers). Bedrock is used for real embedding/generation only when the pipeline is otherwise verified.

## Before any AWS action, state:
1. Resources created, instance types, hourly cost.
2. How long they'll run.
3. Total expected cost and running total vs. $150.
4. The destroy command.
