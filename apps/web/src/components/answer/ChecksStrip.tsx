"use client";

import { motion } from "framer-motion";
import { Ramp } from "@/components/ui/Ramp";
import { Pill } from "@/components/ui/Pill";
import { fmtMs, stageLabel } from "@/lib/format";
import type { AnswerResponse, TrailStep } from "@/lib/types";

const ORDER = ["vector_search", "bm25_search", "fusion", "rerank", "select_top_k", "parent_expansion"];

export function ChecksStrip({
  trail,
  response,
  phase,
}: {
  trail: TrailStep[];
  response: AnswerResponse | null;
  phase: "idle" | "retrieving" | "synthesizing" | "done" | "error";
}) {
  const steps = ORDER.map((s) => trail.find((t) => t.stage === s)).filter(Boolean) as TrailStep[];
  const cited = response?.citations.length ?? 0;
  const offered = response?.sources.length ?? 0;
  const dropped = response?.dropped_citations.length ?? 0;
  const ev = response?.evidence ?? null;
  const conflicts = response?.conflicts.length ?? 0;
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-border-subtle bg-surface-1 px-3 py-2 font-mono text-[11px]" aria-label="Checks">
      <span className="text-[10px] tracking-[0.18em] text-text-muted uppercase">checks</span>
      <div className="flex items-center gap-1" aria-label="Retrieval stages">
        {steps.length === 0 && phase === "retrieving" && <span className="text-text-muted">searching…</span>}
        {steps.map((s, i) => (
          <motion.span
            key={s.stage}
            initial={{ opacity: 0, y: 2 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.15, delay: i * 0.05, ease: "easeOut" }}
            className="inline-flex items-center gap-1"
            title={`${s.stage}: ${s.count} in ${fmtMs(s.latency_ms)}`}
          >
            {i > 0 && <span className="text-text-faint">→</span>}
            <span className="text-text-secondary">{stageLabel[s.stage] ?? s.stage}</span>
            <span className="text-text-primary tabular-nums">{s.count}</span>
          </motion.span>
        ))}
      </div>
      <span className="inline-flex items-center gap-1">
        <span className="text-text-secondary">cited</span>
        {response ? (
          <Pill tone={cited > 0 ? "ok" : "muted"}>
            {cited}/{offered} valid{dropped ? ` · ${dropped} dropped` : ""}
          </Pill>
        ) : (
          <span className="text-text-faint">—</span>
        )}
      </span>
      <span className="inline-flex items-center gap-2">
        <span className="text-text-secondary">evidence</span>
        <Ramp value={ev?.score ?? 0} label="evidence strength" width={56} />
        <span className={ev ? "text-text-primary uppercase" : "text-text-faint"}>{ev?.label ?? "—"}</span>
      </span>
      <span className="inline-flex items-center gap-1">
        <span className="text-text-secondary">conflicts</span>
        {response ? <Pill tone={conflicts ? "warn" : "muted"}>{conflicts}</Pill> : <span className="text-text-faint">—</span>}
      </span>
      {phase === "synthesizing" && <span className="ml-auto text-accent">synthesizing…</span>}
    </div>
  );
}
