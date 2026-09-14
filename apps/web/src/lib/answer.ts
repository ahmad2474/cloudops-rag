/** Turn Markdown answer text into numbered claim lines, and match claims to evidence lines. */

export interface Inline {
  kind: "text" | "code" | "strong" | "cite";
  value: string;
}

export interface ClaimLine {
  n: number;
  kind: "paragraph" | "bullet" | "heading" | "code" | "table";
  inlines: Inline[];
  raw: string;
  sids: string[];
}

const CITE = /\[(S\d+)\]/g;

export function parseInlines(text: string): Inline[] {
  const out: Inline[] = [];
  const re = /(`[^`]+`)|(\*\*[^*]+\*\*)|(\[S\d+\])/g;
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push({ kind: "text", value: text.slice(last, m.index) });
    if (m[1]) out.push({ kind: "code", value: m[1].slice(1, -1) });
    else if (m[2]) out.push({ kind: "strong", value: m[2].slice(2, -2) });
    else if (m[3]) out.push({ kind: "cite", value: m[3].slice(1, -1) });
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push({ kind: "text", value: text.slice(last) });
  return out;
}

/** Split Markdown into claim lines: one per paragraph / bullet / heading; code blocks atomic. */
export function toClaimLines(markdown: string, mode: "answer" | "document" = "answer"): ClaimLine[] {
  const lines: ClaimLine[] = [];
  // Answers: every line is a reviewable claim. Documents are hard-wrapped, so paragraphs stay
  // whole (blank-line separated) while list items still split per item. Fences stay atomic.
  const blocks: string[] = [];
  const text = markdown.replace(/\r\n/g, "\n");
  const splitter = (chunk: string): string[] => {
    if (mode === "answer") return chunk.split("\n");
    const out: string[] = [];
    for (const para of chunk.split(/\n{2,}/)) {
      const rows = para.split("\n");
      if (rows.every((r) => /^\s*([-*+]|\d+[.)])\s+/.test(r) || /^\s+/.test(r) || !r.trim())) {
        let cur = "";
        for (const r of rows) {
          if (/^\s*([-*+]|\d+[.)])\s+/.test(r)) { if (cur) out.push(cur); cur = r; } else cur += " " + r.trim();
        }
        if (cur) out.push(cur);
      } else if (/^#{1,6}\s/.test(para.trim()) || /^\|/.test(para.trim())) {
        out.push(...rows);
      } else {
        out.push(rows.map((r) => r.trim()).join(" "));
      }
    }
    return out;
  };
  const fence = /```[\s\S]*?```/g;
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = fence.exec(text))) {
    if (m.index > last) blocks.push(...splitter(text.slice(last, m.index)));
    blocks.push(m[0]);
    last = m.index + m[0].length;
  }
  if (last < text.length) blocks.push(...splitter(text.slice(last)));
  let n = 0;
  const push = (kind: ClaimLine["kind"], raw: string) => {
    const trimmed = raw.trim();
    if (!trimmed) return;
    n += 1;
    const sids = Array.from(trimmed.matchAll(CITE), (x) => x[1]);
    lines.push({
      n,
      kind,
      raw: trimmed,
      sids: Array.from(new Set(sids)),
      inlines:
        kind === "code"
          ? [{ kind: "code", value: trimmed.replace(/^```\w*\n?|```$/g, "") }]
          : kind === "table"
            ? [{ kind: "text", value: trimmed.split("|").slice(1, -1).map((c) => c.trim()).join("  │  ") }]
            : parseInlines(trimmed),
    });
  };
  for (const block of blocks) {
    if (block.trim().startsWith("```")) {
      push("code", block);
      continue;
    }
    const row = block.trim();
    if (!row) continue;
    if (/^\s*([-*+]|\d+[.)])\s+/.test(row)) {
      push("bullet", row.replace(/^\s*([-*+]|\d+[.)])\s+/, ""));
      continue;
    }
    if (/^#{1,6}\s/.test(row)) {
      push("heading", row.replace(/^#{1,6}\s+/, ""));
      continue;
    }
    if (/^\|/.test(row)) {
      if (/^\|[\s:|-]+\|$/.test(row)) continue; // separator row
      push("table", row);
      continue;
    }
    push("paragraph", row);
  }
  return lines;
}

const STOP = new Set(["the", "a", "an", "of", "to", "in", "on", "for", "and", "or", "is", "are", "be", "with", "by", "that", "this", "it", "as", "at", "from", "not", "if", "when", "then", "than", "s"]);

export function tokens(text: string): Set<string> {
  return new Set(
    text
      .toLowerCase()
      .replace(/\[s\d+\]/g, " ")
      .split(/[^a-z0-9:_\-./]+/)
      .filter((t) => t.length > 2 && !STOP.has(t)),
  );
}

/**
 * Which evidence lines most plausibly support a claim: token overlap, top-3 above a threshold.
 * Labelled "matched lines" in the UI — it is a lexical match, not a model-provided pointer.
 */
export function matchLines(claim: string, evidenceLines: string[]): number[] {
  const q = tokens(claim);
  if (q.size === 0) return [];
  const scored = evidenceLines.map((line, i) => {
    const t = tokens(line);
    if (t.size === 0) return { i, s: 0 };
    let hit = 0;
    for (const w of q) if (t.has(w)) hit += 1;
    return { i, s: hit / Math.sqrt(q.size) };
  });
  const best = scored.filter((x) => x.s >= 0.9).sort((a, b) => b.s - a.s).slice(0, 3);
  return best.map((x) => x.i).sort((a, b) => a - b);
}

export function sidIndex(sid: string): number {
  return Math.max(1, parseInt(sid.replace(/^S/, ""), 10) || 1);
}

export function tintVar(sid: string): string {
  return `var(--tint-${((sidIndex(sid) - 1) % 8) + 1})`;
}
