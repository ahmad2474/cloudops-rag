---
name: ui-design
description: Use when creating or modifying anything under apps/web — components, pages, styling, layout, motion. The UI is the portfolio centerpiece and must not look like a generic chat/dashboard template.
---

# UI Design — Operations Intelligence Console

The UI is a portfolio centerpiece. Do not generate generic SaaS/dashboard/chat layouts. Every screen
needs a deliberate visual hierarchy, distinctive information architecture, and cohesive design language.

## Reference feel
Datadog + Linear + a modern IDE + an incident-response console. Software used by a serious platform team.

## Forbidden
- Sidebar + "New Chat" + giant centered textbox + purple gradient + three feature cards.
- Component-library default aesthetic (unstyled shadcn look). Radix/shadcn are **primitives only**.
- Unnecessary gradients, glassmorphism, glow, particle effects, decorative blobs.
- Fake "AI confidence %". Show **evidence strength** derived from retrieval/citation/grounding signals.
- Giant component files. Organise: `components/{answer,sources,retrieval,incidents,explorer,evaluation,layout,ui}/`.
- Installing many UI libraries. Allowed: Tailwind, Radix, Lucide, Framer Motion. Anything else needs justification.

## Visual system
- Dark-first, deep graphite (not pure black) background; subtle technical grid texture; one restrained accent; soft 1px borders; minimal shadows.
- Typography: Inter or Geist for UI; IBM Plex Mono / Geist Mono for commands, errors, K8s resources, AWS IDs, Terraform, metrics, request IDs.
- Dense information layout. Tabular numerals for metrics.
- Design tokens live in `apps/web/src/styles/tokens.css` (CSS variables) and are mirrored in Tailwind config. Don't hard-code colours in components.

## Core screens
Search/Answer (answer, evidence strength, sources, expandable retrieval trail), Source drawer (right side, highlighted evidence, metadata), Incident mode, Knowledge Explorer, Evaluation dashboard, System status/cost.

## Motion
Motion communicates system state (Searching → Retrieving → Reranking → Synthesizing). Short, purposeful, respects `prefers-reduced-motion`.

## Quality bar (enforce on every PR)
Responsive + mobile layout, keyboard navigation, accessible controls, focus states, semantic HTML,
loading/skeleton/empty/error states, streaming responses, reduced-motion support.
