.DEFAULT_GOAL := help
SHELL := /bin/bash

WEB := apps/web

help: ## Show targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------- local stack
up: ## Start OpenSearch + Dashboards
	docker compose up -d --wait

down: ## Stop local stack (keeps data volume)
	docker compose down

nuke: ## Stop local stack and delete data volume
	docker compose down -v

logs: ## Tail local stack logs
	docker compose logs -f

# ---------------------------------------------------------------- python
install: ## Install Python deps (uv) and pre-commit hooks
	uv sync
	uv run pre-commit install

auth-demo: ## Append demo users (dev/pe/sec, password acme-demo) to .env
	uv run python apps/api/scripts/demo_users.py acme-demo >> .env

api: ## Run FastAPI with reload
	uv run uvicorn app.main:app --app-dir apps/api --reload --port 8000

test: ## Python unit + API tests (no Docker needed)
	uv run pytest -m "not integration"

test-integration: ## Integration tests (needs `make up`)
	uv run pytest -m integration

lint: ## Ruff lint + format check
	uv run ruff check .
	uv run ruff format --check .

fmt: ## Auto-format Python
	uv run ruff check --fix .
	uv run ruff format .

typecheck: ## mypy --strict
	uv run mypy

# ---------------------------------------------------------------- corpus
corpus-fetch: ## Fetch public docs into data/sources/raw (gitignored)
	uv run python apps/ingestion/fetch_sources.py

corpus-manifest: ## Validate corpus and write data/manifest.json
	uv run python apps/ingestion/build_manifest.py

corpus-check: ## Validate corpus; fail if manifest is stale (CI)
	uv run python apps/ingestion/build_manifest.py --check

index-plan: ## Show what indexing would do + embedding token/cost estimate (no writes)
	uv run python apps/ingestion/index_corpus.py --dry-run

index: ## Incrementally index the corpus into OpenSearch
	uv run python apps/ingestion/index_corpus.py

index-full: ## Drop indices and re-embed everything (schema or model change)
	uv run python apps/ingestion/index_corpus.py --drop --full

ask: ## Ask the running API: make ask Q="why are pods pending" ROLE=developer
	@curl -s localhost:8000/ask -H 'content-type: application/json' -H "X-Acme-Role: $${ROLE:-developer}" \
	  -d "{\"question\": \"$(Q)\"}" | jq '{status, answer, citations: [.citations[] | {sid, document_id, section}], trail: [.trail[] | "\(.stage)=\(.count)"], latency_ms, usage}'

# ---------------------------------------------------------------- evaluation
eval-dataset: ## Rebuild data/evaluation/dataset.json from apps/evaluation/build_dataset.py
	uv run python apps/evaluation/build_dataset.py

eval: ## Retrieval-only evaluation (cheap): make eval STRATEGY=vector
	uv run python apps/evaluation/run.py --strategy $${STRATEGY:-vector}

eval-full: ## Retrieval + generation + LLM-judge faithfulness (costs LLM tokens)
	uv run python apps/evaluation/run.py --strategy $${STRATEGY:-vector} --judge

# ---------------------------------------------------------------- web
web-install: ## Install frontend deps
	cd $(WEB) && pnpm install --frozen-lockfile

web-dev: ## Next.js dev server
	cd $(WEB) && pnpm dev

web-build: ## Production build
	cd $(WEB) && pnpm build

web-lint: ## ESLint + tsc
	cd $(WEB) && pnpm lint && pnpm typecheck

web-test: ## Playwright smoke tests
	cd $(WEB) && pnpm test

# ---------------------------------------------------------------- infra
tf-check: ## terraform fmt/validate + tflint + trivy (no AWS calls)
	cd infrastructure/terraform && terraform fmt -check -recursive && terraform init -backend=false -input=false >/dev/null && terraform validate
	cd infrastructure/terraform && tflint --init >/dev/null && tflint --recursive
	cd infrastructure/terraform && trivy config --quiet --severity HIGH,CRITICAL --exit-code 1 .

TF_DIR = infrastructure/terraform
TF_VARS = environments/demo.tfvars

aws-push: ## Build linux/amd64 images and push to ECR; prints image_tag for demo.tfvars
	scripts/aws-push.sh

aws-cost: ## Month-to-date spend by service (Cost Explorer)
	scripts/aws-cost-check.sh

tf-init: ## terraform init (local state; the demo is single-operator and short-lived)
	cd $(TF_DIR) && terraform init -input=false

tf-plan: ## terraform plan for the demo env → review with docs/aws.md cost table before apply
	cd $(TF_DIR) && terraform plan -input=false -var-file=$(TF_VARS) -out=demo.tfplan

tf-apply: ## Apply the reviewed plan (requires an explicit `yes`)
	@read -p "Apply demo.tfplan? Cost envelope in docs/aws.md. Type yes: " a && [ "$$a" = "yes" ]
	cd $(TF_DIR) && terraform apply -input=false demo.tfplan

tf-destroy: ## Destroy the demo environment — run this the same day the demo ends
	cd $(TF_DIR) && terraform destroy -var-file=$(TF_VARS)

tf-output: ## Console URL, instance id, endpoints
	cd $(TF_DIR) && terraform output

docker-lint: ## hadolint Dockerfiles
	hadolint docker/*.Dockerfile

# ---------------------------------------------------------------- everything
check: lint typecheck test corpus-check web-lint tf-check ## Everything CI runs (minus Playwright)

.PHONY: help up down nuke logs install api test test-integration lint fmt typecheck \
        auth-demo corpus-fetch corpus-manifest corpus-check index-plan index index-full ask \
        eval-dataset eval eval-full \
        web-install web-dev web-build web-lint web-test tf-check tf-init tf-plan tf-apply tf-destroy tf-output aws-push aws-cost docker-lint check
