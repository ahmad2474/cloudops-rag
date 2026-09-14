"use client";

import Link from "next/link";
import { Kicker } from "@/components/ui/Kicker";
import { Pill } from "@/components/ui/Pill";
import { toClaimLines } from "@/lib/answer";
import type { DocumentDetail, DocumentSummary } from "@/lib/types";

const SEV: Record<string, "danger" | "warn" | "neutral" | "muted"> = { "SEV-1": "danger", "SEV-2": "warn", "SEV-3": "neutral", "SEV-4": "muted" };

export function IncidentDetail({ doc, related }: { doc: DocumentDetail; related: DocumentSummary[] }) {
  const m = doc.metadata;
  const inc = m.incident!;
  const lines = toClaimLines(doc.body, "document");
  const sameCause = related.filter((r) => r.metadata.incident?.root_cause_category === inc.root_cause_category && r.metadata.document_id !== m.document_id);
  const sharedService = related.filter((r) => r.metadata.document_id !== m.document_id && r.metadata.incident?.services.some((s) => inc.services.includes(s)));
  return (
    <div className="grid gap-px bg-border-subtle lg:grid-cols-[1fr_320px]">
      <article className="min-w-0 bg-surface-0">
        <header className="border-b border-border-subtle bg-surface-1 px-4 py-3">
          <div className="flex flex-wrap items-center gap-2 font-mono text-[11px]">
            <span className="text-text-primary">{inc.incident_id}</span>
            <Pill tone={SEV[inc.severity]}>{inc.severity}</Pill>
            <Pill tone="neutral">{m.environment}</Pill>
            <Pill tone={inc.resolved_at ? "ok" : "warn"}>{inc.resolved_at ? "resolved" : "open"}</Pill>
            <span className="text-text-muted">detected {inc.detected_at.replace("T", " ").replace("Z", " UTC")}</span>
            {inc.resolved_at && <span className="text-text-muted">· resolved {inc.resolved_at.replace("T", " ").replace("Z", " UTC")}</span>}
          </div>
          <h1 className="mt-1 text-[16px] text-text-primary">{m.title.replace(/^INC-\d{4}:\s*/, "")}</h1>
        </header>
        <ol className="p-2 text-[14px] leading-[var(--line-h)]">
          {lines.map((l) => (
            <li key={l.n} className="grid grid-cols-[44px_1fr]">
              <span className="select-none border-r border-border-subtle py-1 pr-2 text-right font-mono text-[11px] text-text-faint tabular-nums">{String(l.n).padStart(2, "0")}</span>
              <div className={`min-w-0 px-3 py-1 break-words ${l.kind === "heading" ? "mt-2 font-mono text-[11px] tracking-widest text-text-muted uppercase" : l.kind === "table" ? "font-mono text-[12px] text-text-secondary" : "text-text-primary"} ${l.kind === "bullet" ? "pl-6" : ""}`}>
                {l.kind === "code" ? <pre className="overflow-x-auto border border-border-subtle bg-surface-1 p-2 font-mono text-[12px] text-text-secondary">{l.inlines[0]?.value}</pre> : l.inlines.map((inl, i) => inl.kind === "code" ? <code key={i} className="bg-surface-2 px-1 font-mono text-[12.5px]">{inl.value}</code> : inl.kind === "strong" ? <strong key={i}>{inl.value}</strong> : <span key={i}>{inl.value}</span>)}
              </div>
            </li>
          ))}
        </ol>
      </article>
      <aside className="bg-surface-1 p-4 font-mono text-[12px]">
        <Kicker>services</Kicker>
        <ul className="mt-1 mb-4 flex flex-wrap gap-1">{inc.services.map((s) => <li key={s}><Pill tone="neutral">{s}</Pill></li>)}</ul>
        <Kicker>root cause category</Kicker>
        <div className="mt-1 mb-4 text-text-primary">{inc.root_cause_category}</div>
        <Kicker>related documents</Kicker>
        <ul className="mt-1 mb-4 grid gap-1">
          {Object.entries(doc.related_titles).map(([id, title]) => (
            <li key={id}><Link href={id.startsWith("inc-") ? `/incidents/${id}` : `/explorer?doc=${id}`} className="text-text-secondary underline-offset-2 hover:text-text-primary hover:underline">{id.startsWith("inc-") ? id.replace("inc-", "INC-") : title}</Link></li>
          ))}
          {Object.keys(doc.related_titles).length === 0 && <li className="text-text-faint">—</li>}
        </ul>
        <Kicker>same root cause</Kicker>
        <ul className="mt-1 mb-4 grid gap-1">
          {sameCause.slice(0, 6).map((r) => <li key={r.metadata.document_id}><Link href={`/incidents/${r.metadata.document_id}`} className="text-text-secondary hover:text-text-primary">{r.metadata.incident!.incident_id} <span className="text-text-muted">· {r.metadata.incident!.severity}</span></Link></li>)}
          {sameCause.length === 0 && <li className="text-text-faint">none</li>}
        </ul>
        <Kicker>shared services</Kicker>
        <ul className="mt-1 mb-4 grid gap-1">
          {sharedService.slice(0, 6).map((r) => <li key={r.metadata.document_id}><Link href={`/incidents/${r.metadata.document_id}`} className="text-text-secondary hover:text-text-primary">{r.metadata.incident!.incident_id} <span className="text-text-muted">· {r.metadata.incident!.services.filter((s) => inc.services.includes(s)).join(", ")}</span></Link></li>)}
          {sharedService.length === 0 && <li className="text-text-faint">none</li>}
        </ul>
        <Kicker>tags</Kicker>
        <div className="mt-1 text-text-muted">{m.tags.join(" · ")}</div>
      </aside>
    </div>
  );
}
