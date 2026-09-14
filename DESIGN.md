---
name: CloudOps Intelligence
description: A code-review bench for operational answers — graphite panes, hairline gutters, one cyan-teal ramp for every score.
colors:
  surface-0: "#0e1013"
  surface-1: "#14171c"
  surface-2: "#1a1e25"
  surface-3: "#21262f"
  border-subtle: "#262b34"
  border-strong: "#343a45"
  text-primary: "#e6e9ee"
  text-secondary: "#9aa3b0"
  text-muted: "#626b78"
  text-faint: "#444b56"
  accent: "#4fd1c5"
  accent-90: "#45bdb2"
  accent-70: "#3a9a91"
  accent-50: "#2f736c"
  accent-30: "#244e4a"
  accent-15: "#1b3230"
  accent-ink: "#0a1f1d"
  ok: "#5fcf80"
  warn: "#e3b341"
  danger: "#f0605d"
  info: "#7aa2f7"
  tint-1: "#4fd1c5"
  tint-2: "#c792ea"
  tint-3: "#89ddff"
  tint-4: "#f78c6c"
  tint-5: "#d4bfff"
  tint-6: "#a3e4d7"
  tint-7: "#f5c2e7"
  tint-8: "#b8d8ff"
  grid-line: "rgba(255, 255, 255, 0.035)"
typography:
  headline:
    fontFamily: "Geist, Inter, system-ui, sans-serif"
    fontSize: "22px"
    fontWeight: 500
    lineHeight: 1.3
  title:
    fontFamily: "Geist, Inter, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.4
  body:
    fontFamily: "Geist, Inter, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.55
  body-small:
    fontFamily: "Geist, Inter, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.55
  data:
    fontFamily: "Geist Mono, IBM Plex Mono, ui-monospace, monospace"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.6
    fontFeature: "tnum"
  label:
    fontFamily: "Geist Mono, IBM Plex Mono, ui-monospace, monospace"
    fontSize: "11px"
    fontWeight: 400
    lineHeight: 1
    letterSpacing: "0.18em"
  micro:
    fontFamily: "Geist Mono, IBM Plex Mono, ui-monospace, monospace"
    fontSize: "10.5px"
    fontWeight: 400
    lineHeight: 1.4
rounded:
  none: "0"
  cell: "1px"
  inline: "3px"
  sm: "4px"
  md: "6px"
spacing:
  gutter: "1px"
  "0.5": "2px"
  "1": "4px"
  "1.5": "6px"
  "2": "8px"
  "3": "12px"
  "4": "16px"
  "6": "24px"
  "8": "32px"
  line-gutter: "44px"
  bar: "48px"
  control-sm: "20px"
  control: "24px"
  input: "32px"
  plate-h: "64px"
  plate-w: "176px"
components:
  button-primary:
    backgroundColor: "{colors.accent-15}"
    textColor: "{colors.accent}"
    typography: "{typography.label}"
    rounded: "{rounded.sm}"
    padding: "0 8px"
    height: "{spacing.control}"
  button-primary-hover:
    backgroundColor: "{colors.accent-30}"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.text-secondary}"
    typography: "{typography.label}"
    rounded: "{rounded.sm}"
    padding: "0 8px"
    height: "{spacing.control}"
  button-ghost-hover:
    textColor: "{colors.text-primary}"
  chip-selected:
    backgroundColor: "{colors.accent-15}"
    textColor: "{colors.accent}"
    typography: "{typography.label}"
    rounded: "{rounded.sm}"
    padding: "0 8px"
    height: "{spacing.control}"
  pill-neutral:
    backgroundColor: "transparent"
    textColor: "{colors.text-secondary}"
    typography: "{typography.label}"
    rounded: "{rounded.sm}"
    padding: "0 6px"
    height: "{spacing.control-sm}"
  pill-accent:
    backgroundColor: "{colors.accent-15}"
    textColor: "{colors.accent}"
    typography: "{typography.label}"
    rounded: "{rounded.sm}"
    padding: "0 6px"
    height: "{spacing.control-sm}"
  pill-ok:
    textColor: "{colors.ok}"
    typography: "{typography.label}"
    rounded: "{rounded.sm}"
    padding: "0 6px"
    height: "{spacing.control-sm}"
  pill-warn:
    textColor: "{colors.warn}"
    typography: "{typography.label}"
    rounded: "{rounded.sm}"
    padding: "0 6px"
    height: "{spacing.control-sm}"
  pill-danger:
    textColor: "{colors.danger}"
    typography: "{typography.label}"
    rounded: "{rounded.sm}"
    padding: "0 6px"
    height: "{spacing.control-sm}"
  pill-muted:
    backgroundColor: "transparent"
    textColor: "{colors.text-muted}"
    typography: "{typography.label}"
    rounded: "{rounded.sm}"
    padding: "0 6px"
    height: "{spacing.control-sm}"
  input-query:
    backgroundColor: "transparent"
    textColor: "{colors.text-primary}"
    typography: "{typography.body-small}"
    rounded: "{rounded.none}"
    padding: "0"
    height: "{spacing.input}"
  input-field:
    backgroundColor: "{colors.surface-0}"
    textColor: "{colors.text-primary}"
    typography: "{typography.body-small}"
    rounded: "{rounded.none}"
    padding: "0 8px"
    height: "{spacing.input}"
  kbd:
    backgroundColor: "{colors.surface-2}"
    textColor: "{colors.text-muted}"
    rounded: "{rounded.inline}"
    padding: "0 4px"
    height: "16px"
  nav-tab:
    backgroundColor: "transparent"
    textColor: "{colors.text-secondary}"
    padding: "0 12px"
    height: "{spacing.bar}"
  nav-tab-active:
    textColor: "{colors.text-primary}"
  pane-header:
    backgroundColor: "{colors.surface-1}"
    textColor: "{colors.text-muted}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    padding: "6px 12px"
  source-plate:
    backgroundColor: "{colors.surface-1}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.none}"
    padding: "8px"
    height: "{spacing.plate-h}"
    width: "{spacing.plate-w}"
  source-plate-hover:
    backgroundColor: "{colors.surface-2}"
  callout-review:
    textColor: "{colors.text-secondary}"
    typography: "{typography.body-small}"
    rounded: "{rounded.none}"
    padding: "8px 12px"
  code-inline:
    backgroundColor: "{colors.surface-2}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.inline}"
    padding: "0 4px"
  empty-state:
    backgroundColor: "transparent"
    textColor: "{colors.text-secondary}"
    rounded: "{rounded.none}"
    padding: "24px"
---

# Design System: CloudOps Intelligence

## Overview

**Creative North Star: "The Review Bench"**

An answer is a change request. Every screen in the console is built the way a code-review tool is built: a left pane of numbered claim lines, a right pane of line-numbered evidence, a checks strip that says whether the answer may merge, and a one-line trail packet that pulls open into the full stage sheet. Nothing here is a chat. There is no message bubble, no centered textbox, no sidebar of past conversations; the query field lives in a 48px command bar and the work happens in panes that sit edge to edge, separated by 1px hairline gutters.

The material is graphite, never black. Four surface steps (`surface-0` page → `surface-1` pane → `surface-2` raised row → `surface-3` selected) carry all depth; there are no drop shadows anywhere in the build. A faint 24px technical grid sits under the page. One accent, cyan-teal, does every job that needs emphasis: focus, selection, the active tab, and — as a luminance ramp of ten cells — every score the system reports (evidence strength, recall, MRR). Semantic states borrow the vocabulary of review: green for checks passed, amber for conflict or stale, red for withheld or blocked. Eight fixed source tints let S1…S8 keep their identity across the bench so a claim's marker, its evidence header, and its plate in the strip all read as one thing.

Density is the default. Body prose is 14px on a 1.55 line; everything that is an identifier, count, latency, cost, command, or line number is Geist Mono at 10.5–12px with tabular figures. Rows restyle in place; columns never move. Motion exists only to show pipeline state: stages fill one after another, a matched evidence line fades in, the trail sheet deploys. Hover changes tint, never position.

**Key Characteristics:**
- Two-pane review bench (52/48 on desktop) with hairline gutters, not cards on a canvas
- Graphite tonal layering; zero box-shadows; depth by surface step and inset rules
- One accent used as a ten-cell luminance ramp for every 0–1 score
- Review vocabulary for state: ok / warn / danger pills, left-rule review callouts
- Mono for identifiers, counts, and labels; sans only for readable prose
- Column-locked tables that restyle rows in place; fixed-scale source plates on one baseline
- Motion communicates pipeline stages only; all of it off under reduced-motion

## Colors

A four-step graphite ramp, one cyan-teal accent expanded into its own luminance ramp, three review-state colors, and eight fixed source tints.

### Primary
- **Bench Teal** (`accent`): the only accent. Focus outline (2px, offset 2px), text selection (via `accent-30`), caret, the active-tab underline, the brand square in the command bar, and the "ask" button. As a ramp it fills score cells and the selected-source markers.
- **Bench Teal Ramp** (`accent-90` … `accent-15`, `accent-ink`): pre-mixed luminance steps of the accent. `accent-15` is the fill of every selected chip and primary button; `accent-50` is their border; `accent-30` is the hover fill and the selection highlight. `accent-ink` is reserved for accent-on-accent text; the shipped build does not yet use it.

### Neutral
- **Page Graphite** (`surface-0`): the page and the inside of both bench panes; also the field background of login inputs.
- **Pane Graphite** (`surface-1`): pane headers, table heads, the checks strip, the trail packet, the command bar (at 95% with backdrop blur), source plates, asides, example buttons, verdict cards.
- **Raised Graphite** (`surface-2`): the active claim line, the selected table row, the selected source plate, inline code, kbd caps, the Select popover, the hover state of the trail button.
- **Selected Graphite** (`surface-3`): unlit ramp cells and the highlighted item in a Select popover.
- **Hairline** (`border-subtle`): every gutter between panes, every row divider, every pane header rule. Also the background of the pane grid, so the 1px gap between panes reads as a line.
- **Strong Hairline** (`border-strong`): control borders (buttons, chips, pills, kbd, inputs), the scrollbar thumb, and the unselected [S#] marker border.
- **Primary Ink** (`text-primary`): prose, titles, counts, identifiers that matter.
- **Secondary Ink** (`text-secondary`): supporting prose, unselected controls, in-hunk evidence lines, most table cells.
- **Muted Ink** (`text-muted`): pane labels, table heads, definition-list keys, metadata.
- **Faint Ink** (`text-faint`): line numbers, placeholders, out-of-hunk evidence lines, disabled-looking dashes.
- **Grid Line** (`grid-line`): a 3.5% white line on a 24px grid, painted once on the body.

### Semantic
- **Checks Passed** (`ok`): "answered" and "cited" pills, zero-ACL-violation cells, resolved incidents.
- **Conflict Amber** (`warn`): review callout left rule and its 8% wash, "abstained" / "possibly stale" / "sanitised" pills, SEV-2, open incidents, superseded-document links.
- **Withheld Red** (`danger`): "withheld" / "blocked" / "api unreachable" pills, SEV-1, error blocks (10% wash, 40% border), ACL violation counts.
- **Evidence Blue** (`info`): defined and mapped in the theme but unused in the shipped build; reserved for links inside evidence.

### Source Tints
- **Tints 1–8** (`tint-1` … `tint-8`): assigned by source index, wrapping after eight. A tint is the [S#] marker's ink (and its fill when selected), the evidence header wash (9% into `surface-1`), the hunk gutter rule, the hit-line wash (16%) and its 2px inset left rule, and the 2px inset top rule on a selected source plate. `tint-1` equals the accent so the first source and the system read as one.

### Named Rules
**The One Ink Rule.** Every score in the console is the same ten-cell ramp of the accent, lit cells stepping in opacity from 0.35 to 1.0. No second hue encodes magnitude; a source tint may replace the accent only when the ramp belongs to that source.

**The Review Vocabulary Rule.** `ok`, `warn`, and `danger` name outcomes of a check, never decoration. They appear as pill ink with a 10% wash and a 40% border, as a callout rule, or as a table cell's ink; never as a fill.

**The Hairline Rule.** Panes are separated by a 1px gap over `border-subtle`, not by borders on each pane. Rows divide with a 1px top rule of the same color.

## Typography

**Body Font:** Geist Sans (with Inter, system-ui, sans-serif)
**Data / Label Font:** Geist Mono (with IBM Plex Mono, ui-monospace, monospace)

**Character:** A neutral grotesk for the few things a human reads as prose; a monospace for everything the machine produced. Tabular numerals are on globally (`tnum`) so counts line up in columns without effort. There is no display face and no serif.

### Hierarchy
- **Headline** (500, 22px): the sign-in heading only. The console itself has no page titles; the pane label does that job.
- **Title** (400, 15–16px): a document's or incident's title inside its pane header, and the verdict card's heading. Regular weight; hierarchy comes from ink and position.
- **Body** (400, 14px, 1.55): claim lines and incident/document lines. Bench prose reads at `max-w-prose`.
- **Body Small** (400, 13–13.5px): explorer document lines, the query field (mono), review callout text, list rows, table title cells that mix sans into a mono table.
- **Data** (400, 12px mono, 1.6 in evidence): table cells, evidence lines, aside definition lists, code blocks. Trail tables and recent-request tables step down to 11.5px.
- **Label** (400, 11px mono, uppercase, 0.18–0.2em tracking): pane labels ("answer", "checks", "trail", "documents"), the brand mark (0.2em), aside field labels, headings inside a rendered document. Pills use the same 11px mono without uppercase, with `tracking-wide`.
- **Micro** (400, 10.5px mono): source-plate metadata, the evidence footer, explorer row metadata. Kbd caps sit at 10px.

### Named Rules
**The Mono Identifier Rule.** Anything that is an id, a count, a latency, a cost, a command, a Kubernetes or AWS resource, a version, a timestamp, or a line number is set in Geist Mono with tabular figures. Prose and titles are the only sans text.

**The Pane Label Rule.** Uppercase tracked mono labels name a pane, a table column group, or an aside field. They sit in the pane header or directly above the field they label, in `text-muted`, and never introduce prose.

## Layout

The console is a full-bleed grid of panes under a sticky 48px command bar. The command bar holds, left to right, the brand mark (bordered right), the tab set, the query field, and the settings cluster (bordered left); each cell is a full-height flex item with hairline dividers between them. On the bench, the area below the bar fills the viewport (`calc(100vh - 48px)`) and splits 52fr/48fr at `lg` (1024px) with a 1px gutter; each pane is a flex column of header, scrolling body, and footer strip. Explorer is three panes at `220px / minmax(280px, 0.9fr) / 1.4fr`; incident and evaluation detail views are `1fr / 320px` with an aside; the system page is `1fr / 300px`.

The spacing scale is Tailwind's 4px scale used sparingly: 2px between ramp cells and plate meta, 4px between chips and list rows, 6px vertical in pane headers and table cells, 8px in plates and callouts, 12px horizontal in headers and cells, 16px in asides and verdict cards, 24px in empty states and the bench idle copy, 32px in the empty evidence pane. Line-numbered content uses a fixed 44px gutter column with a right hairline; the number is right-aligned mono in `text-faint`. Control heights are fixed: pills 20px, buttons and chips 24px, inputs 32px, source plates 64×176px.

Responsive: below `lg` the panes stack into one column; each scrolling pane caps at 60–70vh so the page still scrolls as a whole. The query field wraps to its own full-width row under the bar with a top hairline. Below `md` (768px) the strategy and rerank controls are hidden; below `sm` (640px) the brand collapses to "CI" and the evidence "updated" stamp hides. Tables keep a minimum width (880px for incidents) and scroll inside a `.pane` container rather than the page.

## Elevation & Depth

Flat, by tonal layering only. There are no box-shadows in the build: the Radix Select popover explicitly ships `shadow-none`, and no card or panel lifts off the surface. Depth is one surface step: a pane header is `surface-1` on a `surface-0` pane; a selected row is `surface-2`; a hover row steps up one. The command bar is the sole translucent element (`surface-1` at 95% with a backdrop blur) so content scrolling under it still reads as under.

Emphasis that would elsewhere be a shadow is an inset rule: 2px bottom in the accent under the active tab, 2px top in the source tint on a selected plate, 2px left in the tint on a matched evidence line, 1px bottom in the accent under the focused query field. Callouts get a 2px left rule in `warn` over an 8% wash.

### Named Rules
**The No-Shadow Rule.** Nothing casts a shadow. Elevation is a surface step; selection and focus are inset rules of 1–2px in the accent or the source tint.

**The Wash Rule.** A state color never fills a region. It washes it: 8% for callouts, 10% for pills and error blocks, 9% for the tinted evidence header, 5% for the hunk and 16% for a matched line.

## Shapes

Square by default. Panes, tables, headers, callouts, asides, verdict cards, empty states, login inputs and buttons, and source plates all have no radius; the hairline grid is the form language. Small interactive tokens get a 4px radius (pills, the ask/stop/rerank/strategy buttons, [S#] markers, severity chips, code blocks in the answer, skeleton rows). Inline code and kbd caps get 3px. Ramp cells get 1px. The 6px `md` radius is defined in tokens but nothing in the shipped build uses it. Borders are 1px hairlines; a dashed hairline marks an empty state. The brand mark is a filled 8px square in the accent, not a logo glyph.

## Components

### Buttons
- **Shape:** 24px tall, 4px radius where the button lives in the command bar or bench header; square on the login page. Mono 11–12px lowercase text, 8px horizontal padding.
- **Primary** ("ask", "sign in"): accent ink on an `accent-15` fill with an `accent-50` border.
- **Hover / Focus:** fill steps to `accent-30`; focus is the global 2px accent outline. Disabled drops to 50–60% opacity.
- **Ghost** ("stop", strategy trigger, severity filters, the role readout): `border-strong` hairline, `text-secondary` ink, `text-primary` on hover, no fill. A pressed ghost becomes the primary treatment (this is how chips work).
- **Icon buttons** (sign out, prev/next source): no border, `text-muted` to `text-primary` on hover, 14–16px Lucide glyph.

### Pills
- **Style:** 20px tall, 4px radius, 6px padding, mono 11px with `tracking-wide`, `leading-none`, one hairline border.
- **Tones:** `neutral` (strong hairline, secondary ink, no fill); `muted` (subtle hairline, muted ink); `accent` (`accent-50` border, `accent-15` fill); `ok` / `warn` / `danger` (40% border and 10% wash of the state color, state ink). Tone is chosen by outcome: answered/abstained/withheld, cited/offered, SEV-1..4, resolved/open.

### Chips (selected filters)
- **Unselected:** ghost button treatment.
- **Selected:** `accent-15` fill, `accent-50` border, accent ink, `aria-pressed`.

### Cards / Containers (panes)
- **Corner Style:** square.
- **Background:** `surface-0` body with a `surface-1` header row (6px × 12px padding, mono label) separated by a hairline; asides are `surface-1` with 16px padding.
- **Shadow Strategy:** none (see Elevation).
- **Border:** panes have no border of their own; the 1px gap over `border-subtle` is the divider.
- **Internal Padding:** content is edge-to-edge (rows carry their own 12px padding); free-standing cards (verdict, error, empty state) sit 12px in from the pane with 16–24px internal padding.

### Inputs / Fields
- **Query field:** transparent, 32px tall, mono 13px, `text-primary` on `text-faint` placeholder, no border; focus draws a 1px accent inset rule along the bottom and suppresses the outline. Has focus on load; ⌘K refocuses it.
- **Login fields:** `surface-0` fill, `border-strong` hairline, square, 32px tall, mono 13px.
- **Select (Radix):** ghost trigger with a 12px chevron; popover is `surface-2` with a `border-strong` hairline, 4px padding, mono 12px items, `surface-3` highlight, accent check on the selected item, no shadow.
- **Error:** `danger` ink mono 12px under the form; error blocks in panes use the danger wash.

### Navigation
- **Style:** tab set in the command bar, 13px sans, 12px horizontal padding, full 48px height. Default `text-secondary`, hover `text-primary`, active `text-primary` with a 2px accent inset underline; `aria-current="page"`. On narrow viewports the tab row scrolls horizontally inside a `.pane`.

### Claim Lines (signature)
Numbered claim rows in a `44px / 1fr / minmax(56px, auto)` grid: mono line number in the gutter with a right hairline; 14px sans body; [S#] markers right-aligned. A marker is a 20px, 4px-radius button in its source tint (tint ink and border, transparent fill); selected inverts to a tint fill with `surface-0` ink. The active line is `surface-2`; hover is `surface-1`. Review callouts (conflicts) hang under the line they affect, indented past the gutter, with a `warn` pill kicker inside the callout and a "prefer S#" mono link.

### Evidence File (signature)
The whole cited document, line-numbered in the same 44px gutter, mono 12px on a 1.6 line. Out-of-hunk lines are `text-faint`; the hunk is `text-secondary` on a 5% tint wash with a tint gutter rule; matched lines are `text-primary` on a 16% wash with a 2px tint inset left rule. The header is `surface-1` washed 9% with the tint, carrying a tint-filled SID badge, position, cited/offered pill, type, version, updated, title, section, and line range. Selecting a marker scrolls this pane only, never the window.

### Checks Strip and Ramp
A `surface-1` strip under the answer, mono 11px: a "checks" label, the stage counts joined by faint arrows, a cited pill, the evidence ramp with its label, and a conflicts pill. The Ramp is ten 8px-tall cells with 1px gaps and 1px radius; lit cells are the accent (or a tint) with opacity 0.35→1.0; unlit cells are `surface-3`.

### Source Plates
Fixed-scale plates in a horizontal strip: 176×64px, `surface-1`, 8px padding, separated by 1px gutters over `border-subtle`. Top row: tint SID, cited/offered in `ok`/`text-faint`, type right-aligned; middle: 12px sans title clamped to one line; bottom: micro mono section. Hover and selected are `surface-2`; selected adds a 2px tint inset top rule.

### Trail Packet
One mono 11px line at rest (chevron, "trail" label, stage summary, latency/tokens/cost right-aligned) that deploys a two-column sheet: a column-locked stage table (11.5px mono, fixed widths, ellipsised detail) and a query-plan / generation definition list.

### Column-Locked Tables
`table-layout: fixed`, collapsed borders, every cell `nowrap` with ellipsis. Heads are `surface-1`, mono 12px, `font-normal`, `text-muted`, left-aligned with numeric columns right-aligned. Rows divide with a hairline; hover steps to `surface-1`, active to `surface-2`. Columns never reflow; a title cell may switch to 13px sans inside a mono table.

### Kbd
16px tall, 3px radius, `surface-2` fill, `border-strong` hairline, mono 10px `text-muted`. Used for ⌘ K in the bar and j / k / [ / ] hints in the answer header.

### Skeleton / Empty State
Skeletons are `surface-2` rows with 4px radius and the default pulse. Empty states are a dashed `border-subtle` box, 24px padding, 14px title in `text-primary`, 14px body in `text-secondary`; no icon, no eyebrow.

## Do's and Don'ts

### Do:
- **Do** build every new surface as panes on the hairline grid: `surface-0` body, `surface-1` header with a mono uppercase label, 1px gaps over `border-subtle`.
- **Do** render every score as the ten-cell accent Ramp; a source tint is the only permitted substitute, and only for that source's own score.
- **Do** set identifiers, counts, latencies, costs, commands, versions, and line numbers in Geist Mono with tabular figures, and keep prose in Geist Sans at 13–14px.
- **Do** express state through Pill tones (`ok` / `warn` / `danger` / `accent` / `neutral` / `muted`) and inset rules of 1–2px; step one surface for hover and one more for selected.
- **Do** keep tables column-locked (`table.locked`) so rows restyle in place; scroll wide content inside a `.pane`.
- **Do** put the page's primary text input in the command bar's query slot and give it focus on load.
- **Do** keep motion to pipeline state: 150ms ease-out stage fills staggered 50ms, 120ms evidence-line fades, 200ms sheet deploys; honour `prefers-reduced-motion` via `MotionConfig reducedMotion="user"` and the global CSS override.

### Don't:
- **Don't** add box-shadows, gradients, or translucent glass panels; the only translucency is the command bar's 95% surface with blur.
- **Don't** introduce a second accent hue or use `info` for emphasis; amber, red, and green are reserved for check outcomes.
- **Don't** build a chat layout: no message bubbles, no centered textbox, no conversation sidebar, no "new chat".
- **Don't** lay out marketing rows of three feature cards or use a component library's default aesthetic; every control is the 24px hairline button or pill described above.
- **Don't** use pure black, rounded corners above 4px, or glyph icons as decoration; Lucide glyphs appear only as 12–16px affordances (chevrons, check, external link, sign out).
- **Don't** hard-code a colour, radius, or font in a component; consume the tokens through the Tailwind `@theme` mapping.
- **Don't** move an element on hover; hover changes ink or steps a surface, nothing else.
