"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ChevronRight } from "lucide-react";
import { useState } from "react";
import { Pill } from "@/components/ui/Pill";
import { fmtMs, stageLabel } from "@/lib/format";
import type { QueryPlan, TrailStep, Usage } from "@/lib/types";

/** Packet → sheet: one line at rest; one pull deploys the full stage table. */
export function TrailPacket({ trail, plan, usage, latency }: { trail: TrailStep[]; plan: QueryPlan | null; usage: Usage | null; latency: Record<string, number> }) {
  const [open, setOpen] = useState(false);
  if (!trail.length) return null;
  const total = trail.reduce((a, s) => a + s.latency_ms, 0);
  return (
    <section className="border-t border-border-subtle bg-surface-1" aria-label="Retrieval trail">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full min-w-0 items-center gap-3 px-3 py-1.5 text-left font-mono text-[11px] hover:bg-surface-2"
      >
        <ChevronRight className={`h-3.5 w-3.5 text-text-muted transition-transform ${open ? "rotate-90" : ""}`} aria-hidden="true" />
        <span className="tracking-widest text-text-muted uppercase">trail</span>
        <span className="truncate text-text-secondary">
          {trail.map((s) => `${stageLabel[s.stage] ?? s.stage} ${s.count}`).join("  ›  ")}
        </span>
        <span className="ml-auto min-w-0 truncate text-text-muted tabular-nums">
          {fmtMs(total)} retrieval{latency.generation != null ? ` · ${fmtMs(latency.generation)} generation` : ""}
          <span className="hidden sm:inline">{usage ? ` · ${usage.input_tokens}→${usage.output_tokens} tok · $${usage.estimated_cost_usd.toFixed(4)}` : ""}</span>
        </span>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            key="sheet"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="overflow-hidden"
          >
            <div className="grid gap-px border-t border-border-subtle bg-border-subtle lg:grid-cols-[1fr_minmax(280px,0.6fr)]">
              <table className="locked w-full bg-surface-1 font-mono text-[11.5px]">
                <thead>
                  <tr className="text-left text-text-muted">
                    <th className="w-8 px-3 py-1 font-normal">#</th>
                    <th className="w-32 px-2 py-1 font-normal">stage</th>
                    <th className="w-20 px-2 py-1 text-right font-normal">count</th>
                    <th className="w-24 px-2 py-1 text-right font-normal">latency</th>
                    <th className="px-2 py-1 font-normal">detail</th>
                  </tr>
                </thead>
                <tbody>
                  {trail.map((s, i) => (
                    <tr key={i} className="border-t border-border-subtle text-text-secondary">
                      <td className="px-3 py-1 text-text-faint">{String(i + 1).padStart(2, "0")}</td>
                      <td className="px-2 py-1 text-text-primary">{s.stage}</td>
                      <td className="px-2 py-1 text-right text-text-primary tabular-nums">{s.count}</td>
                      <td className="px-2 py-1 text-right tabular-nums">{fmtMs(s.latency_ms)}</td>
                      <td className="truncate px-2 py-1 text-text-muted" title={JSON.stringify(s.detail)}>
                        {Object.entries(s.detail).map(([k, v]) => `${k}=${Array.isArray(v) ? v.join("+") : String(v)}`).join("  ")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="bg-surface-1 p-3 font-mono text-[11.5px] text-text-secondary">
                <div className="mb-1 tracking-widest text-text-muted uppercase">query plan</div>
                {plan ? (
                  <dl className="grid grid-cols-[110px_1fr] gap-y-1">
                    <dt className="text-text-muted">searched</dt>
                    <dd className="text-text-primary">{plan.query}</dd>
                    {plan.subqueries.length > 0 && (<><dt className="text-text-muted">subqueries</dt><dd>{plan.subqueries.join(" | ")}</dd></>)}
                    {plan.version_hint && (<><dt className="text-text-muted">version</dt><dd><Pill tone="accent">{plan.version_hint}</Pill></dd></>)}
                    {plan.incident_ids.length > 0 && (<><dt className="text-text-muted">incidents</dt><dd>{plan.incident_ids.join(", ")}</dd></>)}
                    {plan.document_type_hint && (<><dt className="text-text-muted">type hint</dt><dd>{plan.document_type_hint}</dd></>)}
                    {plan.stripped_injection && (<><dt className="text-text-muted">sanitised</dt><dd><Pill tone="warn">instruction preamble stripped</Pill></dd></>)}
                  </dl>
                ) : (
                  <span className="text-text-faint">—</span>
                )}
                {usage && (
                  <>
                    <div className="mt-3 mb-1 tracking-widest text-text-muted uppercase">generation</div>
                    <dl className="grid grid-cols-[110px_1fr] gap-y-1">
                      <dt className="text-text-muted">model</dt><dd className="truncate text-text-primary">{usage.model}</dd>
                      <dt className="text-text-muted">tokens</dt><dd className="tabular-nums">{usage.input_tokens} in · {usage.output_tokens} out</dd>
                      <dt className="text-text-muted">est. cost</dt><dd className="tabular-nums">${usage.estimated_cost_usd.toFixed(5)}</dd>
                    </dl>
                  </>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
}
