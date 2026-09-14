"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useShell } from "@/components/layout/AppShell";
import { Kicker } from "@/components/ui/Kicker";
import { Pill } from "@/components/ui/Pill";
import { Skeleton } from "@/components/ui/Skeleton";
import { toClaimLines } from "@/lib/answer";
import { api } from "@/lib/api";
import type { CatalogueStats, DocumentDetail, DocumentSummary } from "@/lib/types";

/**
 * Knowledge explorer: the corpus as a tag map (not a graph DB). Left: type/tag tree with counts
 * for what your role can see; middle: documents; right: the document, line-numbered.
 */
function Explorer() {
  const params = useSearchParams();
  const { setQueryField } = useShell();
  const [stats, setStats] = useState<CatalogueStats | null>(null);
  const [docs, setDocs] = useState<DocumentSummary[]>([]);
  const [tag, setTag] = useState<string | null>(null);
  const [type, setType] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [open, setOpen] = useState<DocumentDetail | null>(null);
  const [openId, setOpenId] = useState<string | null>(params.get("doc"));

  useEffect(() => {
    setQueryField(
      <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Find a document — title, id, tag…" aria-label="Find a document" className="h-8 w-full bg-transparent font-mono text-[13px] text-text-primary placeholder:text-text-faint focus:outline-none" />,
    );
  }, [q, setQueryField]);
  useEffect(() => {
    api.documentStats().then(setStats).catch(() => setStats(null));
    api.documents({ limit: 1000 }).then(setDocs).catch(() => setDocs([]));
  }, []);
  useEffect(() => {
    let cancelled = false;
    if (openId) {
      api.document(openId).then((d) => { if (!cancelled) setOpen(d); }).catch(() => { if (!cancelled) setOpen(null); });
    } else {
      queueMicrotask(() => { if (!cancelled) setOpen(null); });
    }
    return () => { cancelled = true; };
  }, [openId]);

  const visible = useMemo(() => {
    const ql = q.toLowerCase();
    return docs.filter((d) => (!tag || d.metadata.tags.includes(tag)) && (!type || d.metadata.document_type === type) && (!ql || `${d.metadata.title} ${d.metadata.document_id} ${d.metadata.tags.join(" ")}`.toLowerCase().includes(ql)));
  }, [docs, tag, type, q]);
  const tags = useMemo(() => Object.entries(stats?.tags ?? {}).sort((a, b) => b[1] - a[1]).slice(0, 60), [stats]);
  const lines = useMemo(() => (open ? toClaimLines(open.body, "document") : []), [open]);

  return (
    <div className="grid min-h-[calc(100vh-var(--bar-h))] grid-cols-1 gap-px bg-border-subtle lg:grid-cols-[220px_minmax(280px,0.9fr)_1.4fr]">
      <aside className="bg-surface-1 p-3 font-mono text-[12px]">
        <Kicker>corpus</Kicker>
        <div className="mt-1 mb-3 text-text-secondary">{stats ? `${stats.visible} of ${stats.total} documents visible to your role` : "…"}</div>
        <Kicker>type</Kicker>
        <ul className="mt-1 mb-3">
          {Object.entries(stats?.by_type ?? {}).sort((a, b) => b[1] - a[1]).map(([t, n]) => (
            <li key={t}>
              <button type="button" onClick={() => setType(type === t ? null : t)} aria-pressed={type === t} className={`flex w-full justify-between py-0.5 ${type === t ? "text-accent" : "text-text-secondary hover:text-text-primary"}`}>
                <span>{t}</span><span className="text-text-faint tabular-nums">{n}</span>
              </button>
            </li>
          ))}
        </ul>
        <Kicker>tags</Kicker>
        <ul className="pane mt-1 max-h-[50vh] overflow-auto">
          {tags.map(([t, n]) => (
            <li key={t}>
              <button type="button" onClick={() => setTag(tag === t ? null : t)} aria-pressed={tag === t} className={`flex w-full justify-between py-0.5 ${tag === t ? "text-accent" : "text-text-secondary hover:text-text-primary"}`}>
                <span className="truncate">{t}</span><span className="text-text-faint tabular-nums">{n}</span>
              </button>
            </li>
          ))}
        </ul>
      </aside>
      <section className="min-w-0 bg-surface-0" aria-label="Documents">
        <div className="sticky top-[var(--bar-h)] flex items-center gap-2 border-b border-border-subtle bg-surface-1 px-3 py-1.5 font-mono text-[11px]">
          <span className="tracking-widest text-text-muted uppercase">documents</span>
          <span className="text-text-muted">{visible.length}</span>
          {type && <Pill tone="accent">{type}</Pill>}
          {tag && <Pill tone="accent">#{tag}</Pill>}
        </div>
        <ul className="pane max-h-[calc(100vh-var(--bar-h)-32px)] overflow-auto">
          {docs.length === 0 && Array.from({ length: 12 }, (_, i) => <li key={i} className="p-2"><Skeleton className="h-6" /></li>)}
          {visible.map((d) => (
            <li key={d.metadata.document_id}>
              <button type="button" onClick={() => setOpenId(d.metadata.document_id)} aria-pressed={openId === d.metadata.document_id} className={`grid w-full grid-cols-[72px_1fr] gap-2 border-b border-border-subtle px-3 py-1.5 text-left hover:bg-surface-1 ${openId === d.metadata.document_id ? "bg-surface-2" : ""}`}>
                <span className="truncate font-mono text-[10.5px] text-text-muted">{d.metadata.document_type}</span>
                <span className="min-w-0">
                  <span className="block truncate text-[13px] text-text-primary">{d.metadata.title}</span>
                  <span className="block truncate font-mono text-[10.5px] text-text-faint">{d.metadata.source} · {d.metadata.document_id}{d.metadata.version ? ` · v${d.metadata.version}` : ""}{d.metadata.status !== "active" ? ` · ${d.metadata.status}` : ""}</span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      </section>
      <section className="min-w-0 bg-surface-0" aria-label="Document">
        {open ? (
          <div className="flex h-full flex-col">
            <header className="sticky top-[var(--bar-h)] border-b border-border-subtle bg-surface-1 px-3 py-2">
              <div className="flex flex-wrap items-center gap-2 font-mono text-[11px] text-text-muted">
                <Pill tone={open.metadata.status === "active" ? "neutral" : "warn"}>{open.metadata.status}</Pill>
                <span>{open.metadata.document_type}</span><span>{open.metadata.source}</span>
                {open.metadata.version && <span>v{open.metadata.version}</span>}
                <span>updated {open.metadata.updated_at}</span>
                <span className="ml-auto">{open.metadata.permissions.join(" · ")}</span>
              </div>
              <h1 className="mt-1 text-[15px] text-text-primary">{open.metadata.title}</h1>
              {(open.metadata.supersedes || Object.keys(open.related_titles).length > 0) && (
                <div className="mt-1 flex flex-wrap gap-2 font-mono text-[11px]">
                  {open.metadata.supersedes && <button type="button" onClick={() => setOpenId(open.metadata.supersedes)} className="text-warn hover:underline">supersedes {open.metadata.supersedes}</button>}
                  {Object.keys(open.related_titles).map((id) => <button key={id} type="button" onClick={() => setOpenId(id)} className="text-text-secondary hover:text-text-primary hover:underline">→ {id}</button>)}
                </div>
              )}
            </header>
            <ol className="pane max-h-[calc(100vh-var(--bar-h)-90px)] overflow-auto py-2 text-[13.5px] leading-[var(--line-h)]">
              {lines.map((l) => (
                <li key={l.n} className="grid grid-cols-[44px_1fr]">
                  <span className="select-none border-r border-border-subtle py-0.5 pr-2 text-right font-mono text-[11px] text-text-faint tabular-nums">{String(l.n).padStart(2, "0")}</span>
                  <div className={`min-w-0 px-3 py-0.5 break-words ${l.kind === "heading" ? "mt-2 font-mono text-[11px] tracking-widest text-text-muted uppercase" : l.kind === "table" ? "font-mono text-[12px] text-text-secondary" : "text-text-primary"} ${l.kind === "bullet" ? "pl-6" : ""}`}>
                    {l.kind === "code" ? <pre className="overflow-x-auto border border-border-subtle bg-surface-1 p-2 font-mono text-[12px] text-text-secondary">{l.inlines[0]?.value}</pre> : l.inlines.map((inl, i) => inl.kind === "code" ? <code key={i} className="bg-surface-2 px-1 font-mono text-[12px]">{inl.value}</code> : inl.kind === "strong" ? <strong key={i}>{inl.value}</strong> : <span key={i}>{inl.value}</span>)}
                  </div>
                </li>
              ))}
            </ol>
          </div>
        ) : (
          <div className="flex h-full items-center justify-center p-8 text-center"><p className="max-w-xs text-sm text-text-secondary">Pick a document. Restricted documents are simply absent from this list for your role.</p></div>
        )}
      </section>
    </div>
  );
}

export default function ExplorerPage() {
  return <Suspense><Explorer /></Suspense>;
}
