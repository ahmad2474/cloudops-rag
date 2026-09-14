# Security

Spec §22–23, §47. Threat model and tests live in `.claude/skills/security-testing/SKILL.md`,
`tests/security/`, `tests/adversarial/`.

## Identity

- `POST /auth/login` (username + password) → short-lived **HS256 JWT** (`sub`, `roles`, `iss`,
  `iat`, `exp`), signed with `AUTH_SECRET`. Users come from `AUTH_USERS` (bcrypt hashes; nothing
  in code). Unknown user and wrong password are indistinguishable (bcrypt runs either way).
- Every `/ask` and `/search` resolves a `Principal` from `Authorization: Bearer …`. Roles in the
  token are re-validated against the known set on every request; a correctly signed token with an
  unknown role is rejected, as are `alg=none` and foreign-key tokens.
- `X-Acme-Role` (dev convenience) is honoured only when `APP_ENV` is `local` or `test`, and a
  Bearer token always wins over it. `APP_ENV=aws` refuses to start with the dev secret or an empty
  user store.

## Authorization

**Happens at retrieval, as a query filter.** `SearchFilters.roles` is the first clause of every
kNN and BM25 request; the LLM, the citation validator and the UI only ever see authorized chunks.
Metadata filters can narrow but never widen. Verified across all 4 strategies × 3 context modes
(`tests/security/test_acl.py`).

## Prompt injection

Layers, outermost first:
1. **Question-level**: `plan_query` strips "ignore your instructions…" preambles (recorded as
   `stripped_injection`).
2. **Prompt framing**: retrieved documents are labelled evidence, not instructions; the model is
   told never to reveal the system prompt.
3. **Structural**: a model can only cite `[S#]` ids it was given; unknown ids are dropped. It cannot
   exfiltrate what retrieval never returned.
4. **Output guard** (`generation/guardrails.py`): answers echoing any 48-char window of the system
   prompt, or containing override markers, are replaced with a `blocked` response and logged.

The adversarial suite drives the real `/ask` path with the four injection documents from the
corpus and a **deliberately compliant model** that obeys any instruction it sees — the defences
must hold even then. Whether the *real* model obeys injections is measured separately by the
evaluation's `injection_success_rate`.

## What is not logged

Request logs carry ids, roles, counts, latencies and token usage — never chunk content, answers,
or secrets.

## Not yet

Rate limiting and request size limits (Phase 8); secrets from AWS Secrets Manager and TLS
termination (Phase 10).
