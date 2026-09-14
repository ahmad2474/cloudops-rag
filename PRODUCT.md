# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary: the on-call **platform / cloud engineer** at Acme (a fictional payments company), mid-incident
or mid-investigation, asking operational questions of the company's knowledge base — runbooks,
architecture docs, policies, postmortems, 70 past incidents, and curated AWS / Kubernetes /
Terraform documentation. They are experts, time-pressed, keyboard-first, and sceptical of
unsourced answers. Three roles exist and change what they can see: `developer`,
`platform-engineer`, `security-admin`.

Secondary: reviewers of the portfolio (engineering hiring managers) watching a 4–6 minute demo or
clicking through the deployed console. They must be able to *see the pipeline working* — retrieval
stages, citations, authorization, abstention, evaluation numbers — without explanation text.
When the two conflict, the on-call engineer wins: it must read as a real product, not a demo.

## Product Purpose

An operations intelligence console over a curated CloudOps corpus. It answers questions with
evidence: hybrid retrieval (vector + BM25 + fusion + reranking), parent/child context, grounded
generation with validated citations, retrieval-time authorization, conflict detection, and an
explicit "insufficient evidence" abstention. Success = an engineer trusts an answer because they
can see exactly which sections it came from, how it was found, and what was withheld and why.

## Positioning

Not "upload PDFs and chat". The console exposes the machinery — retrieval trail with per-stage
counts, evidence strength derived from signals (never model self-confidence), version/deprecation
conflicts named in the answer, per-request cost — and enforces authorization *before* the model
ever sees a document. The evaluation dashboard shows measured Recall@K / MRR / NDCG / faithfulness
for each retrieval strategy, from recorded runs only.

## Operating Context

- Backend: FastAPI (`apps/api`) — `POST /ask`, `POST /ask/stream` (SSE), `POST /search`,
  `POST /auth/login`, `GET /auth/me`, `GET /system/requests`, `GET /system/summary`, `GET /ready`.
  Responses carry `status` (answered | abstained | no_authorized_evidence | blocked), `answer`
  (Markdown), `citations[]` (sid, document_id, title, section, version, updated_at, excerpt,
  source_url), `sources[]`, `conflicts[]`, `evidence{score,label,signals}`, `query_plan`,
  `trail[]` (stage, count, latency_ms, detail), `usage`, `latency_ms`.
- Corpus: 222 documents; document types runbook, architecture, policy, postmortem,
  troubleshooting, incident (`INC-0900…INC-1099`, severity SEV-1..4, services, root-cause
  category), technical_documentation (AWS / Kubernetes / Terraform), adversarial.
- Evaluation reports: JSON files under `evaluation/reports/` (strategy, per-category metrics,
  latency percentiles, cost). None exist yet — the dashboard must have an honest empty state.
- Identity: JWT. Demo login page offers the three demo users as one-click role choices.
- Environments: local Docker (OpenSearch), later a small AWS deployment behind CloudFront.
- Used during incidents alongside Slack, Grafana, kubectl — the console is one tab among many.

## Capabilities and Constraints

- Screens: Search / Answer (with evidence strength, sources, expandable retrieval trail,
  conflicts), Source drawer (right side, highlighted evidence, metadata), Incidents (list + detail
  with related incidents and likely root causes), Knowledge Explorer (document relationships by
  tags/related, not a graph DB), Evaluation dashboard (strategy comparison), System status & cost
  (from the request ledger and eval reports — real numbers only).
- Answers stream (SSE); the final validated answer replaces streamed text.
- Per-request pipeline overrides exist (`strategy`, `rerank`, `context_mode`) for comparison.
- Stack is fixed: Next.js (App Router) + TypeScript + Tailwind v4 + Radix primitives + Lucide +
  Framer Motion. Radix/shadcn are primitives only; the design system is ours. No additional UI
  libraries without justification. Design tokens live in `apps/web/src/styles/tokens.css`.
- Must be responsive (mobile layout), keyboard-navigable, accessible (semantic HTML, focus
  states, reduced motion), with loading / skeleton / empty / error states.
- Terminology: chunk, parent (section), citation `[S1]`, trail, strategy (vector, bm25,
  hybrid_rrf, hybrid_weighted), rerank, context mode, abstain, evidence strength, ACL, role.

## Brand Commitments

Product name in the UI: **CloudOps Intelligence** (console) for **Acme Cloud Platform**.
Binding visual constraints from the project specification: dark-first, deep graphite (not pure
black), subtle technical grid texture, one restrained accent, high-contrast typography, dense
information layout, soft borders, minimal shadows, purposeful motion that communicates pipeline
state (Searching → Retrieving → Reranking → Synthesizing). Monospace for commands, errors,
Kubernetes resources, AWS identifiers, Terraform, metrics, request ids. Explicitly *not*: a
sidebar-plus-"New Chat"-plus-centered-textbox chat clone, purple gradients, three feature cards,
component-library default aesthetic.

## Evidence on Hand

- Real corpus and real API responses (see `data/`, `docs/api.md`).
- No evaluation reports yet (Bedrock quotas pending) — never fabricate numbers; show "no runs".
- No customer logos, testimonials, or screenshots exist and must not be invented.

## Product Principles

1. Evidence before prose: every claim traceable to a section; withheld evidence is stated.
2. The pipeline is visible: stages, counts, latencies, cost — the machinery is the product.
3. Authorization is structural and shown as such (what you *can't* see is acknowledged, not hidden).
4. Density with hierarchy: operators scan; nothing decorative competes with signal.
5. Honest states: abstention, blocked, degraded, "no runs yet" are first-class, not error toasts.

## Accessibility & Inclusion

Keyboard-first operation (global search focus, list navigation, drawer open/close), visible focus
rings, WCAG AA contrast on the dark palette, `prefers-reduced-motion` respected, semantic landmarks.
