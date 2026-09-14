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
tf-check: ## terraform fmt/validate + tflint (no AWS calls)
	cd infrastructure/terraform && terraform fmt -check -recursive && terraform init -backend=false -input=false >/dev/null && terraform validate

docker-lint: ## hadolint Dockerfiles
	hadolint docker/*.Dockerfile

# ---------------------------------------------------------------- everything
check: lint typecheck test web-lint tf-check ## Everything CI runs (minus Playwright)

.PHONY: help up down nuke logs install api test test-integration lint fmt typecheck \
        web-install web-dev web-build web-lint web-test tf-check docker-lint check
