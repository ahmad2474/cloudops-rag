# UI — CloudOps Intelligence console

Next.js 16 (App Router) + TypeScript + Tailwind v4 + Radix primitives + Lucide + Framer Motion,
in `apps/web`. Design language: **Review Bench** — an answer is a change request. Product truth in
`PRODUCT.md`; the recorded design system in `DESIGN.md` (+ `.impeccable/design.json`); the surface
brief and direction contract in `.impeccable/surfaces/`.

## Screens

| Route | What it is |
|---|---|
| `/login` | Role switcher (three demo principals as a column-locked table) + credentials form; real JWT underneath |
| `/` | **Bench**: command bar (tabs · query · strategy/rerank chips · role); left pane = answer as numbered claim lines with `[S#]` gutter markers and conflicts pinned as review comments; right pane = the **evidence file** — the whole cited document, line-numbered, cited section as the hunk, lexically matched lines lit; CHECKS strip (stages → counts · cited n/m · evidence ramp · conflicts); source plates at one fixed scale; trail packet → sheet with the query plan and usage |
| `/incidents`, `/incidents/[id]` | column-locked incident table with severity filter; detail with services, root-cause category, related / same-cause / shared-service incidents |
| `/explorer` | corpus as a type/tag map for your role; document list; line-numbered document view with supersedes/related links |
| `/evaluation` | strategy comparison table from `evaluation/reports/*.json` with per-category breakdown; honest empty state until real runs exist |
| `/system` | readiness/index/requests/latency/cost status row from the request ledger; recent requests; active config |

Streaming: `/ask/stream` SSE — deltas render live, the `done` event replaces them with the validated
answer (citations checked, guard applied). Keyboard: `⌘K` focus query, `j`/`k` claims, `[`/`]` sources.
Non-answers (`abstained`, `no_authorized_evidence`, `blocked`) render as review verdicts, not errors.

## Running

```bash
make auth-demo                     # demo users dev/pe/sec, password acme-demo → .env
make api                           # :8000 (CORS_ORIGINS=http://localhost:3000)
cd apps/web && cp .env.example .env.local && pnpm dev   # :3000
```

`NEXT_PUBLIC_DEMO_PASSWORD` enables one-click demo sign-in; leave it unset in any real deployment.

## Design process (Phase 9)

Impeccable (v4, installed under `.claude/skills/impeccable`, hooks removed, telemetry off) drove the
process: product interview → `PRODUCT.md`; direction roll (seed `2e6246e3`) with the user locking
**Review Bench** over the TUI-console pick and the category standard; direction contract; code-led
build; detector (no findings); fresh-context finish review — three rounds, disposition **ship**;
documenter → `DESIGN.md`. Review captures live in `.impeccable/review/` (regenerate with
`node apps/web/scripts/capture.mjs`).

Unpursued raises from the review's ceiling check: marker→evidence-line connectors, an explicit
merge-verdict line, a "request changes" affordance on the bench.
