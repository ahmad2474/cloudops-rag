# API

FastAPI service in `apps/api/`. Thin by design: routing, identity, limits, records. All logic is
in `cloudops_rag`.

## Endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/health` | none | liveness (process up) |
| GET | `/ready` | none | readiness: search reachable (503 if not) + index counts; `degraded` if the chunk index is empty |
| POST | `/auth/login` | none | username/password → HS256 JWT (`access_token`, `expires_in`, `roles`) |
| GET | `/auth/me` | bearer | who am I |
| POST | `/ask` | bearer | grounded answer: `status`, `answer`, `citations[]`, `sources[]`, `conflicts[]`, `evidence`, `query_plan`, `trail[]`, `usage`, `latency_ms` |
| POST | `/ask/stream` | bearer | SSE: `retrieval` (trail, sources, conflicts, plan) → `delta`* → `done` (validated `AnswerResponse`) |
| POST | `/search` | bearer | retrieval only: `hits[]` (score + chunk) + `trail[]` |
| GET | `/system/requests?n=` | bearer | recent request records (own; all for platform-engineer / security-admin) |
| GET | `/system/summary` | bearer | ledger totals (requests, abstained, blocked, p50/p95, cost) + active config |

Request bodies for `/ask`/`/search` accept `filters{document_types, environments, version, sources,
include_deprecated}` and per-request `strategy`, `rerank`, `context_mode` overrides.

## Production behaviour (spec §48)

- **Request ids**: `X-Request-ID` honoured or generated; echoed on every response; bound into every
  log line; included in problem responses.
- **Structured logs**: JSON (structlog). One `request_record` event per `/ask` with the spec §18
  fields (counts per stage, latencies, tokens, estimated cost, status) — never chunk content.
- **Timeouts & retries**: every provider call runs under a deadline (`TIMEOUT_*_S`); idempotent
  calls (embed, search, rerank, fetch) retry with jittered backoff on retryable errors
  (throttling/5xx/timeouts, `PROVIDER_RETRIES`); generation is retried only if it failed before
  producing output.
- **Rate limiting**: token bucket per principal (`RATE_LIMIT_RPM`, burst = rpm) → `429` with
  `Retry-After`. In-memory; per-instance.
- **Request size**: `MAX_REQUEST_BYTES` → `413`.
- **Errors**: RFC 7807 `application/problem+json` for domain errors (502 upstream, 504 timeout,
  429, 413, 500) with `request_id`.
- **Streaming**: SSE. Deltas are raw model output; the `done` event carries the validated answer
  (citations checked, guard applied) — clients render from `done`.
- **Observability record ring**: last `REQUEST_LEDGER_SIZE` records in memory for the UI's cost
  panel; durable sink is Phase 13.

## Running

```bash
make api                          # uvicorn on :8000, /docs enabled outside APP_ENV=aws
make ask Q="why are pods pending" # dev header identity
curl -N localhost:8000/ask/stream -H 'content-type: application/json' -H 'X-Acme-Role: developer' \
     -d '{"question":"why are my EKS pods pending"}'
```
