---
name: production-python
description: Use when writing any Python in src/ or apps/api — FastAPI routes, Pydantic models, async code, logging, configuration, error handling, tests.
---

# Production Python

## Toolchain
Python 3.12 (pinned by uv), `uv` for deps/venv, `ruff` (lint + format), `mypy --strict`, `pytest` + `pytest-asyncio`.
Run `make check` before claiming anything works.

## Structure
- `src/cloudops_rag/` is a library: no FastAPI, no I/O at import time, no global clients.
- `apps/api/app/` is thin: routers, dependency wiring, middleware. Business logic lives in the library.
- Dependencies are injected (FastAPI `Depends`, or explicit constructor args). No module-level singletons except settings.

## Typing & models
- Everything typed; `mypy --strict` passes. Use `Protocol` for provider interfaces.
- Pydantic v2 models for all request/response bodies and for data records (Document, Chunk, RetrievalResult, Citation). `frozen=True` where practical.
- Configuration via `pydantic-settings` (`Settings` class, `.env` loaded, no `os.environ` reads elsewhere).

## Async
- FastAPI handlers are `async`. Blocking SDK calls (boto3) go through `asyncio.to_thread` or an async client. Never block the event loop.
- Timeouts on every external call. Retries with backoff only for idempotent operations.

## Logging & observability
- `structlog` JSON logs. Every request gets `request_id` (from `X-Request-ID` or generated) bound to the log context.
- Never log secrets or restricted chunk content.

## Errors
- Custom exception hierarchy in `cloudops_rag.errors`; API layer maps them to RFC 7807-style JSON problems.
- Fail loudly on misconfiguration at startup, not on first request.

## Tests
- Unit tests are fast and use stub providers. Integration tests marked `@pytest.mark.integration` and need Docker OpenSearch.
- Test names describe behaviour. One assertion concept per test. No sleeps.
