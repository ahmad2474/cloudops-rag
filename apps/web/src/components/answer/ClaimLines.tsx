"use client";

import type { ClaimLine } from "@/lib/answer";
import { tintVar } from "@/lib/answer";
import type { Conflict } from "@/lib/types";
import { ConflictComment } from "./ConflictComment";

export function ClaimLines({
  lines,
  selectedSid,
  activeLine,
  onSelectSid,
  onActivateLine,
  conflicts,
  streaming,
}: {
  lines: ClaimLine[];
  selectedSid: string | null;
  activeLine: number | null;
  onSelectSid: (sid: string, line: number) => void;
  onActivateLine: (n: number) => void;
  conflicts: Conflict[];
  streaming: boolean;
}) {
  return (
    <ol className="font-sans text-[14px] leading-[var(--line-h)]" aria-label="Answer claims">
      {lines.map((l) => {
        const involved = conflicts.filter((c) => c.sids.some((s) => l.sids.includes(s)));
        const active = activeLine === l.n;
        return (
          <li key={l.n} className="group">
            <div
              className={`grid grid-cols-[44px_1fr_minmax(56px,auto)] ${active ? "bg-surface-2" : "hover:bg-surface-1"}`}
              onClick={() => onActivateLine(l.n)}
            >
              <span className="select-none border-r border-border-subtle py-1 pr-2 text-right font-mono text-[11px] text-text-faint tabular-nums">
                {String(l.n).padStart(2, "0")}
              </span>
              <div className={`min-w-0 px-3 py-1 break-words ${l.kind === "heading" ? "font-medium text-text-primary" : l.kind === "table" ? "font-mono text-[12px] text-text-secondary" : "text-text-primary"} ${l.kind === "bullet" ? "pl-6 before:absolute before:-ml-3 before:text-text-muted before:content-['–']" : ""} relative`}>
                {l.kind === "code" ? (
                  <pre className="overflow-x-auto rounded-sm border border-border-subtle bg-surface-0 p-2 font-mono text-[12px] text-text-secondary">{l.inlines[0]?.value}</pre>
                ) : (
                  l.inlines.map((inl, i) => {
                    if (inl.kind === "code") return <code key={i} className="rounded-[3px] bg-surface-2 px-1 font-mono text-[12.5px] text-text-primary">{inl.value}</code>;
                    if (inl.kind === "strong") return <strong key={i} className="font-semibold">{inl.value}</strong>;
                    if (inl.kind === "cite") return null; // rendered in the gutter
                    return <span key={i}>{inl.value}</span>;
                  })
                )}
              </div>
              <div className="flex flex-wrap content-start justify-end gap-1 py-1 pr-2" aria-label={l.sids.length ? `Cited: ${l.sids.join(", ")}` : undefined}>
                {l.sids.map((sid) => {
                  const sel = selectedSid === sid;
                  return (
                    <button
                      key={sid}
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectSid(sid, l.n);
                      }}
                      aria-pressed={sel}
                      className="h-5 rounded-sm border px-1.5 font-mono text-[11px] leading-none tabular-nums"
                      style={{
                        borderColor: sel ? tintVar(sid) : "var(--border-strong)",
                        color: sel ? "var(--surface-0)" : tintVar(sid),
                        background: sel ? tintVar(sid) : "transparent",
                      }}
                    >
                      {sid}
                    </button>
                  );
                })}
              </div>
            </div>
            {involved.map((c, i) => (
              <ConflictComment key={i} conflict={c} onSelectSid={(s) => onSelectSid(s, l.n)} />
            ))}
          </li>
        );
      })}
      {streaming && (
        <li className="grid grid-cols-[44px_1fr]">
          <span className="border-r border-border-subtle py-1 pr-2 text-right font-mono text-[11px] text-text-faint">··</span>
          <span className="px-3 py-1 font-mono text-[12px] text-text-muted">synthesizing…</span>
        </li>
      )}
    </ol>
  );
}
