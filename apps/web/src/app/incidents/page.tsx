"use client";

import { useEffect, useMemo, useState } from "react";
import { IncidentTable } from "@/components/incidents/IncidentTable";
import { useShell } from "@/components/layout/AppShell";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import { api } from "@/lib/api";
import type { DocumentSummary } from "@/lib/types";

export default function IncidentsPage() {
  const { setQueryField } = useShell();
  const [items, setItems] = useState<DocumentSummary[] | null>(null);
  const [q, setQ] = useState("");
  const [sev, setSev] = useState<string>("all");
  useEffect(() => {
    setQueryField(
      <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Filter incidents — title, service, tag…" aria-label="Filter incidents" className="h-8 w-full bg-transparent font-mono text-[13px] text-text-primary placeholder:text-text-faint focus:outline-none" />,
    );
  }, [q, setQueryField]);
  useEffect(() => {
    api.documents({ document_type: "incident", limit: 500 }).then((d) => setItems(d.sort((a, b) => (b.metadata.incident!.detected_at > a.metadata.incident!.detected_at ? 1 : -1)))).catch(() => setItems([]));
  }, []);
  const filtered = useMemo(() => {
    const ql = q.toLowerCase();
    return (items ?? []).filter((d) => (sev === "all" || d.metadata.incident!.severity === sev) && (!ql || `${d.metadata.title} ${d.metadata.incident!.services.join(" ")} ${d.metadata.tags.join(" ")} ${d.metadata.incident!.root_cause_category}`.toLowerCase().includes(ql)));
  }, [items, q, sev]);
  const counts = useMemo(() => (items ?? []).reduce<Record<string, number>>((a, d) => ((a[d.metadata.incident!.severity] = (a[d.metadata.incident!.severity] ?? 0) + 1), a), {}), [items]);
  return (
    <div>
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 border-b border-border-subtle bg-surface-1 px-3 py-1.5 font-mono text-[11px]">
        <span className="tracking-widest whitespace-nowrap text-text-muted uppercase">incident intelligence</span>
        <span className="text-text-muted" title="visible to your role">{items ? `${filtered.length}/${items.length}` : "…"}</span>
        <span className="hidden text-text-muted sm:inline">visible to your role</span>
        <div className="pane flex w-full gap-1 overflow-x-auto sm:ml-auto sm:w-auto" role="group" aria-label="Severity filter">
          {["all", "SEV-1", "SEV-2", "SEV-3", "SEV-4"].map((s) => (
            <button key={s} type="button" onClick={() => setSev(s)} aria-pressed={sev === s} className={`h-6 shrink-0 border px-2 whitespace-nowrap ${sev === s ? "border-accent-50 bg-accent-15 text-accent" : "border-border-strong text-text-secondary hover:text-text-primary"}`}>
              {s}{s !== "all" && counts[s] != null ? ` ${counts[s]}` : ""}
            </button>
          ))}
        </div>
      </div>
      {items === null ? (
        <div className="grid gap-px p-3">{Array.from({ length: 8 }, (_, i) => <Skeleton key={i} className="h-7" />)}</div>
      ) : filtered.length === 0 ? (
        <div className="p-6"><EmptyState kicker="incidents" title="No incidents match" body="Nothing visible to your role matches the filter." /></div>
      ) : (
        <div className="pane overflow-x-auto"><IncidentTable items={filtered} /></div>
      )}
    </div>
  );
}
