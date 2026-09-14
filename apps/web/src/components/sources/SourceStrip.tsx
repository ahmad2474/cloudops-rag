"use client";

import { tintVar } from "@/lib/answer";
import type { Citation } from "@/lib/types";

/** Fixed-scale plates: every source the same size, same baseline, regardless of rank. */
export function SourceStrip({ sources, selectedSid, citedSids, onSelect }: { sources: Citation[]; selectedSid: string | null; citedSids: Set<string>; onSelect: (sid: string) => void }) {
  if (!sources.length) return null;
  return (
    <div className="flex gap-px overflow-x-auto border-t border-border-subtle bg-border-subtle" role="list" aria-label="Sources offered to the model">
      {sources.map((s) => {
        const sel = s.sid === selectedSid;
        const tint = tintVar(s.sid);
        return (
          <div key={s.sid} role="listitem" className="contents">
          <button
            type="button"
            onClick={() => onSelect(s.sid)}
            aria-pressed={sel}
            className={`flex h-16 w-44 shrink-0 flex-col justify-between bg-surface-1 p-2 text-left hover:bg-surface-2 ${sel ? "bg-surface-2" : ""}`}
            style={{ boxShadow: sel ? `inset 0 2px 0 ${tint}` : undefined }}
          >
            <div className="flex items-center gap-1 font-mono text-[10.5px]">
              <span className="font-semibold" style={{ color: tint }}>{s.sid}</span>
              <span className={citedSids.has(s.sid) ? "text-ok" : "text-text-faint"}>{citedSids.has(s.sid) ? "cited" : "offered"}</span>
              <span className="ml-auto text-text-faint">{s.document_type}</span>
            </div>
            <div className="line-clamp-1 text-[12px] text-text-primary">{s.title}</div>
            <div className="truncate font-mono text-[10.5px] text-text-muted">§ {s.section || "(top)"}</div>
          </button>
          </div>
        );
      })}
    </div>
  );
}
