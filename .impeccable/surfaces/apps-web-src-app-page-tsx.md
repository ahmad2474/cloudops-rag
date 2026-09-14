---
version: 1
slug: "apps-web-src-app-page-tsx"
primary_target: "apps/web/src/app/page.tsx"
related_targets: ["apps/web/src/app/incidents/page.tsx","apps/web/src/app/explorer/page.tsx","apps/web/src/app/evaluation/page.tsx","apps/web/src/app/system/page.tsx","apps/web/src/app/login/page.tsx"]
---

# Surface brief — the console (apps/web, routes: /, /incidents, /explorer, /evaluation, /system, /login)

Scope: the whole operations console; visitor mode Operate. Audience: Acme on-call engineer (roles
developer / platform-engineer / security-admin); secondary: portfolio reviewers watching a demo.
Task: ask a question, verify the answer against evidence, act. Proof: real API responses.
Constraints: PRODUCT.md brand commitments (dark graphite, one accent, dense, mono identifiers);
stack fixed (Next.js App Router, Tailwind v4, Radix primitives, Lucide, Framer Motion).
Memorable moment: a claim's gutter marker lights the exact evidence lines across the bench.
Unresolved: none blocking; evaluation page shows an honest empty state until reports exist.

## Direction contract

THESIS: An answer is a change request. Claims on the left must each be justified by evidence on
the right, and a checks line says whether it may merge into your incident. It refuses the
category default — sidebar + centered search + answer card + source cards — and the chat clone.

OWN-WORLD: Graphite panes (#0e1013 / #14171c / #1a1e25) separated by 1px hairline gutters, no
shadows, 4–6px radii. One accent, cyan-teal #4fd1c5, used as a single luminance ramp for every
score (rerank, fusion, evidence). Amber #e3b341 for delayed/conflict, red #f0605d for withheld/
blocked, green #5fcf80 for checks passed. Geist Sans for prose; Geist Mono for identifiers, line
numbers, SIDs, counts, commands, latencies, costs. Review-comment callouts (left rule, mono
kicker). Check-run pills. Column-locked tables whose rows restyle in place. Source cards at one
fixed scale on one baseline. With all content removed it still reads as a code-review bench.

STORY: The engineer types a question in the command bar and watches the checks strip fill stage
by stage (Searching → Retrieving → Reranking → Synthesizing). The answer lands as numbered claim
lines; each carries an [S#] marker in the gutter. Hovering or selecting a marker floods the
evidence pane with that source's tint and highlights the exact supporting lines; conflicts appear
as pinned review comments on the claim they affect. They see what was withheld (role) and why.
They believe the answer because they can read the evidence; they act, or "request changes"
(rephrase / switch strategy / switch role).

FIRST VIEWPORT (desktop 1440): Command bar full width, 48px: brand mark (mono, "CLOUDOPS
INTELLIGENCE"), tab set (Bench · Incidents · Explorer · Evaluation · System), query field
(mono, ⌘K), role chip, strategy chip. Below, the bench: left pane 52% — answer header (status
pill, evidence strength ramp bar, cost/latency mono), then claim lines numbered 01.. with gutter
markers; right pane 48% — evidence file: header (title · section · version · updated, tinted by
selected source), line-numbered content with highlighted lines, prev/next source. Under the left
pane a CHECKS strip (Retrieval 42→38→20→6 · Citations 5/5 · Evidence HIGH · Conflicts 1). At the
bottom a one-line trail packet that pulls open into the full stage sheet. Primary action = the
query field; it has focus on load.

FORM: Review Bench — position 3 of 7 on the ordered list; seed key 2e6246e3. Raises kept:
column-locked rows (split-flap), one-ink ramp (ASCII), fixed-scale plates (botanical), packet→sheet
trail (Miura), selection floods the readout (racing).

SIGNATURE INTERACTION: marker ↔ evidence-line linkage: selecting [S#] scrolls and highlights the
exact excerpt lines in the evidence pane and tints its header; keyboard j/k moves between claims,
[ ] between sources. MOTION GRAMMAR: stage-by-stage checks fill (150ms each, ease-out), evidence
line highlight fades in 120ms, trail packet deploys 200ms; no motion on hover except tint; all
motion off under prefers-reduced-motion.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the
verdict, DESIGN.md, and every shipping raster carrying its provenance.
