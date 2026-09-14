"use client";

import Link from "next/link";
import { Pill } from "@/components/ui/Pill";
import type { DocumentSummary } from "@/lib/types";

const SEV: Record<string, "danger" | "warn" | "neutral" | "muted"> = { "SEV-1": "danger", "SEV-2": "warn", "SEV-3": "neutral", "SEV-4": "muted" };

/** Column-locked: columns never move; rows restyle in place. */
export function IncidentTable({ items, activeId }: { items: DocumentSummary[]; activeId?: string }) {
  return (
    <table className="locked w-full min-w-[880px] font-mono text-[12px]" aria-label="Incidents">
      <thead className="bg-surface-1 text-left text-text-muted">
        <tr>
          <th className="w-24 px-3 py-1.5 font-normal">id</th>
          <th className="w-24 px-2 py-1.5 font-normal">date</th>
          <th className="w-20 px-2 py-1.5 font-normal">sev</th>
          <th className="px-2 py-1.5 font-normal">title</th>
          <th className="w-48 px-2 py-1.5 font-normal">services</th>
          <th className="w-32 px-2 py-1.5 font-normal">cause</th>
          <th className="w-28 px-2 py-1.5 font-normal">env</th>
        </tr>
      </thead>
      <tbody>
        {items.map((d) => {
          const m = d.metadata;
          const inc = m.incident!;
          const active = m.document_id === activeId;
          return (
            <tr key={m.document_id} className={`border-t border-border-subtle ${active ? "bg-surface-2" : "hover:bg-surface-1"}`}>
              <td className="px-3 py-1.5">
                <Link href={`/incidents/${m.document_id}`} className="text-text-primary underline-offset-2 hover:underline">{inc.incident_id}</Link>
              </td>
              <td className="px-2 py-1.5 text-text-secondary tabular-nums">{inc.detected_at.slice(0, 10)}</td>
              <td className="px-2 py-1.5"><Pill tone={SEV[inc.severity]}>{inc.severity}</Pill></td>
              <td className="truncate px-2 py-1.5 font-sans text-[13px] text-text-primary" title={m.title}>{m.title.replace(/^INC-\d{4}:\s*/, "")}</td>
              <td className="truncate px-2 py-1.5 text-text-secondary" title={inc.services.join(", ")}>{inc.services.join(" · ")}</td>
              <td className="truncate px-2 py-1.5 text-text-secondary">{inc.root_cause_category}</td>
              <td className="truncate px-2 py-1.5 text-text-muted">{m.environment}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
