"use client";

import { ChevronLeft, ChevronRight, ExternalLink } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Pill } from "@/components/ui/Pill";
import { matchLines, tintVar } from "@/lib/answer";
import { api } from "@/lib/api";
import type { Citation } from "@/lib/types";

/**
 * The evidence file: the whole cited document, line-numbered, with the cited section as the
 * hunk and the claim's lexically matched lines highlighted inside it. Falls back to the
 * section text alone if the document can't be loaded (never to an empty pane).
 */
export function EvidencePane({
  sources,
  selectedSid,
  claimText,
  onSelectSid,
  citedSids,
}: {
  sources: Citation[];
  selectedSid: string | null;
  claimText: string | null;
  onSelectSid: (sid: string) => void;
  citedSids: Set<string>;
}) {
  const src = sources.find((s) => s.sid === selectedSid) ?? null;
  const cache = useRef<Map<string, string | null>>(new Map());
  const [body, setBody] = useState<string | null>(null);

  useEffect(() => {
    if (!src) return;
    const id = src.document_id;
    let cancelled = false;
    if (cache.current.has(id)) {
      queueMicrotask(() => { if (!cancelled) setBody(cache.current.get(id) ?? null); });
    } else {
      api.document(id).then((d) => { cache.current.set(id, d.body); if (!cancelled) setBody(d.body); }).catch(() => { cache.current.set(id, null); if (!cancelled) setBody(null); });
    }
    return () => { cancelled = true; };
  }, [src]);

  const file = useMemo(() => {
    if (!src) return { lines: [] as string[], hunk: [0, 0] as [number, number], whole: false };
    const section = src.content.split("\n");
    const doc = body?.split("\n") ?? null;
    if (doc) {
      const first = section.find((l) => l.trim().length > 12)?.trim();
      const start = first ? doc.findIndex((l) => l.trim() === first) : -1;
      if (start >= 0) {
        const firstIdx = section.findIndex((l) => l.trim() === first);
        const s = Math.max(0, start - firstIdx);
        return { lines: doc, hunk: [s, Math.min(doc.length, s + section.length)] as [number, number], whole: true };
      }
    }
    return { lines: section, hunk: [0, section.length] as [number, number], whole: false };
  }, [src, body]);

  const hits = useMemo(() => {
    if (!src || !claimText) return new Set<number>();
    const [s, e] = file.hunk;
    return new Set(matchLines(claimText, file.lines.slice(s, e)).map((i) => i + s));
  }, [src, claimText, file]);

  const [expanded, setExpanded] = useState<Set<"above" | "below">>(new Set());
  useEffect(() => {
    queueMicrotask(() => setExpanded(new Set()));
  }, [src?.sid]);
  const scroller = useRef<HTMLDivElement>(null);
  const anchor = useRef<HTMLDivElement>(null);
  useEffect(() => {
    // Scroll the evidence pane only — never the window — so the bench never jumps.
    const el = anchor.current;
    const box = scroller.current;
    if (!el || !box) return;
    const target = el.offsetTop - box.clientHeight / 2 + el.clientHeight / 2;
    box.scrollTo({ top: Math.max(0, target), behavior: "smooth" });
  }, [hits, file, src?.sid]);

  if (!src) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 p-8 text-center">
        <p className="max-w-xs text-sm text-text-secondary">Select a citation marker in the answer to open the section it was drawn from.</p>
      </div>
    );
  }
  const idx = sources.findIndex((s) => s.sid === src.sid);
  const tint = tintVar(src.sid);
  const go = (d: number) => {
    const n = sources[(idx + d + sources.length) % sources.length];
    if (n) onSelectSid(n.sid);
  };
  const [hs, he] = file.hunk;
  const anchorLine = hits.size ? Math.min(...hits) : hs;
  const CONTEXT = 6;
  const visibleFrom = expanded.has("above") ? 0 : Math.max(0, hs - CONTEXT);
  const visibleTo = expanded.has("below") ? file.lines.length : Math.min(file.lines.length, he + CONTEXT);
  const foldAbove = visibleFrom;
  const foldBelow = file.lines.length - visibleTo;
  return (
    <div className="flex h-full min-h-0 flex-col" style={{ ["--tint" as string]: tint }}>
      <header className="border-b border-border-subtle px-3 py-2" style={{ background: `color-mix(in srgb, ${tint} 9%, var(--surface-1))` }}>
        <div className="flex items-center gap-2 font-mono text-[11px]">
          <span className="rounded-sm px-1.5 py-0.5 font-semibold" style={{ background: tint, color: "var(--surface-0)" }}>{src.sid}</span>
          <span className="text-text-muted">{idx + 1}/{sources.length}</span>
          <Pill tone={citedSids.has(src.sid) ? "ok" : "muted"}>{citedSids.has(src.sid) ? "cited" : "offered, not cited"}</Pill>
          <span className="text-text-muted">{src.document_type}</span>
          {src.version && <span className="text-text-muted">v{src.version}</span>}
          <span className="hidden text-text-muted sm:inline">updated {src.updated_at}</span>
          <span className="ml-auto flex items-center gap-1">
            <button type="button" onClick={() => go(-1)} aria-label="Previous source" className="text-text-muted hover:text-text-primary"><ChevronLeft className="h-4 w-4" /></button>
            <button type="button" onClick={() => go(1)} aria-label="Next source" className="text-text-muted hover:text-text-primary"><ChevronRight className="h-4 w-4" /></button>
          </span>
        </div>
        <div className="mt-1 truncate text-[13px] text-text-primary" title={src.title}>{src.title}</div>
        <div className="flex items-center gap-2 truncate font-mono text-[11px] text-text-secondary">
          <span className="truncate">§ {src.section || "(top)"}</span>
          <span className="text-text-muted">· L{hs + 1}–{he}{file.whole ? ` of ${file.lines.length}` : ""}</span>
          {src.source_url && (
            <a href={src.source_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-text-muted hover:text-text-primary">
              source <ExternalLink className="h-3 w-3" />
            </a>
          )}
          <span className="ml-auto text-text-muted">{src.token_count} tok</span>
        </div>
      </header>
      <div ref={scroller} className="pane relative max-h-[60vh] min-h-0 flex-1 overflow-auto font-mono text-[12px] leading-[1.6] lg:max-h-none" role="region" aria-label={`Evidence from ${src.title}`}>
        {foldAbove > 0 && (
          <button type="button" onClick={() => setExpanded((e) => new Set([...e, "above"]))} className="grid w-full grid-cols-[44px_1fr] text-left text-text-muted hover:bg-surface-2">
            <span className="border-r border-border-subtle pr-2 text-right text-text-faint">⋯</span>
            <span className="px-3">{foldAbove} line{foldAbove > 1 ? "s" : ""} above the cited section · expand</span>
          </button>
        )}
        {file.lines.slice(visibleFrom, visibleTo).map((line, k) => {
          const i = visibleFrom + k;
          const hit = hits.has(i);
          const inHunk = i >= hs && i < he;
          return (
            <div
              key={i}
              ref={i === anchorLine ? anchor : undefined}
              data-hit={hit}
              data-hunk={inHunk}
              className="ev-line grid grid-cols-[44px_1fr]"
            >
              <span className={`select-none border-r pr-2 text-right tabular-nums ${inHunk ? "border-[var(--tint)] text-text-muted" : "border-border-subtle text-text-faint"}`}>{i + 1}</span>
              <span className={`min-w-0 px-3 break-words whitespace-pre-wrap ${inHunk ? (hit ? "text-text-primary" : "text-text-secondary") : "text-text-faint"} ${line.startsWith("#") ? "text-text-primary" : ""}`}>{line || " "}</span>
            </div>
          );
        })}
        {foldBelow > 0 && (
          <button type="button" onClick={() => setExpanded((e) => new Set([...e, "below"]))} className="grid w-full grid-cols-[44px_1fr] text-left text-text-muted hover:bg-surface-2">
            <span className="border-r border-border-subtle pr-2 text-right text-text-faint">⋯</span>
            <span className="px-3">{foldBelow} line{foldBelow > 1 ? "s" : ""} below the cited section · expand</span>
          </button>
        )}
      </div>
      <footer className="flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-border-subtle px-3 py-1 font-mono text-[10.5px] text-text-muted">
        <span className="inline-flex items-center gap-1"><span className="inline-block h-2.5 w-2.5" style={{ background: `color-mix(in srgb, ${tint} 16%, var(--surface-1))`, boxShadow: `inset 2px 0 0 ${tint}` }} /> matches the selected claim</span>
        <span className="inline-flex items-center gap-1"><span className="inline-block h-2.5 w-2.5" style={{ background: `color-mix(in srgb, ${tint} 5%, var(--surface-1))` }} /> cited section</span>
        <span className="inline-flex items-center gap-1"><span className="inline-block h-2.5 w-2.5 bg-surface-1" /> rest of the document (context)</span>
        <span className="ml-auto">{hits.size > 0 ? `${hits.size} matched line${hits.size > 1 ? "s" : ""} (lexical)` : claimText ? "no strong lexical match — read the section" : "select a claim"}</span>
      </footer>
    </div>
  );
}
