"use client";

import { Fragment, useEffect, useState } from "react";
import { useShell } from "@/components/layout/AppShell";
import { Kicker } from "@/components/ui/Kicker";
import { Pill } from "@/components/ui/Pill";
import { Skeleton } from "@/components/ui/Skeleton";
import { api } from "@/lib/api";
import { fmtMs, fmtUsd } from "@/lib/format";
import type { ReadyResponse, RequestRecord, SystemSummary } from "@/lib/types";

export default function SystemPage() {
  const { setQueryField } = useShell();
  const [ready, setReady] = useState<ReadyResponse | null>(null);
  const [summary, setSummary] = useState<SystemSummary | null>(null);
  const [recs, setRecs] = useState<RequestRecord[] | null>(null);
  useEffect(() => { setQueryField(<span className="font-mono text-[12px] text-text-muted">System status · costs from the request ledger, not estimates</span>); }, [setQueryField]);
  useEffect(() => {
    const load = () => {
      api.ready().then(setReady).catch(() => setReady(null));
      api.systemSummary().then(setSummary).catch(() => setSummary(null));
      api.systemRequests(50).then(setRecs).catch(() => setRecs([]));
    };
    load();
    const t = setInterval(load, 10_000);
    return () => clearInterval(t);
  }, []);
  const l = summary?.ledger;
  return (
    <div>
      <table className="locked w-full border-b border-border-subtle font-mono text-[12px]" aria-label="Status">
        <thead className="bg-surface-1 text-left text-text-muted">
          <tr><th className="w-40 px-3 py-1.5 font-normal">readiness</th><th className="px-2 py-1.5 font-normal">index</th><th className="w-28 px-2 py-1.5 text-right font-normal">requests</th><th className="w-40 px-2 py-1.5 text-right font-normal">answered · abst · blocked</th><th className="w-32 px-2 py-1.5 text-right font-normal">p50 / p95</th><th className="w-28 px-2 py-1.5 text-right font-normal">total cost</th><th className="w-28 px-2 py-1.5 text-right font-normal">avg / query</th></tr>
        </thead>
        <tbody>
          <tr className="border-t border-border-subtle text-text-secondary">
            <td className="px-3 py-1.5"><Pill tone={ready?.status === "ready" ? "ok" : ready ? "warn" : "danger"}>{ready ? ready.status : "api unreachable"}</Pill></td>
            <td className="truncate px-2 py-1.5">{ready ? `search ${ready.search ? "reachable" : "down"} · ${ready.index.chunks ?? 0} chunks · ${ready.index.parents ?? 0} parents` : "—"}</td>
            <td className="px-2 py-1.5 text-right text-text-primary tabular-nums">{l ? l.requests : "—"}</td>
            <td className="px-2 py-1.5 text-right tabular-nums">{l ? `${l.answered} · ${l.abstained} · ${l.blocked}` : "—"}</td>
            <td className="px-2 py-1.5 text-right tabular-nums">{l ? `${fmtMs(l.p50_latency_ms)} / ${fmtMs(l.p95_latency_ms)}` : "—"}</td>
            <td className="px-2 py-1.5 text-right text-text-primary tabular-nums">{l ? fmtUsd(l.total_cost_usd, 4) : "—"}</td>
            <td className="px-2 py-1.5 text-right tabular-nums">{l ? fmtUsd(l.avg_cost_usd, 5) : "—"}</td>
          </tr>
        </tbody>
      </table>
      <div className="grid gap-px bg-border-subtle lg:grid-cols-[1fr_300px]">
        <section className="bg-surface-0">
          <div className="border-b border-border-subtle bg-surface-1 px-3 py-1.5 font-mono text-[11px] tracking-widest text-text-muted uppercase">recent requests</div>
          {recs === null ? <div className="grid gap-px p-3">{Array.from({ length: 6 }, (_, i) => <Skeleton key={i} className="h-6" />)}</div> : recs.length === 0 ? <p className="p-4 font-mono text-[12px] text-text-muted">No requests recorded in this process yet.</p> : (
            <table className="locked w-full font-mono text-[11.5px]">
              <thead className="text-left text-text-muted"><tr><th className="w-20 px-3 py-1 font-normal">time</th><th className="w-28 px-2 py-1 font-normal">user</th><th className="px-2 py-1 font-normal">query</th><th className="w-24 px-2 py-1 font-normal">status</th><th className="w-28 px-2 py-1 font-normal">strategy</th><th className="w-20 px-2 py-1 text-right font-normal">vec/bm25</th><th className="w-14 px-2 py-1 text-right font-normal">cite</th><th className="w-20 px-2 py-1 text-right font-normal">total</th><th className="w-20 px-2 py-1 text-right font-normal">cost</th></tr></thead>
              <tbody>
                {recs.map((r) => (
                  <tr key={r.request_id} className="border-t border-border-subtle text-text-secondary">
                    <td className="px-3 py-1 tabular-nums">{r.timestamp.slice(11, 19)}</td>
                    <td className="truncate px-2 py-1">{r.user}</td>
                    <td className="truncate px-2 py-1 font-sans text-[12.5px] text-text-primary" title={r.query}>{r.query}</td>
                    <td className="px-2 py-1"><Pill tone={r.answer_status === "answered" ? "ok" : r.blocked ? "danger" : "warn"}>{r.answer_status.replaceAll("_", " ")}</Pill></td>
                    <td className="truncate px-2 py-1">{r.strategy}</td>
                    <td className="px-2 py-1 text-right tabular-nums">{r.vector_results}/{r.bm25_results}</td>
                    <td className="px-2 py-1 text-right tabular-nums">{r.citations}</td>
                    <td className="px-2 py-1 text-right tabular-nums">{fmtMs(r.total_latency_ms)}</td>
                    <td className="px-2 py-1 text-right tabular-nums">{fmtUsd(r.estimated_cost_usd, 5)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
        <aside className="bg-surface-1 p-4 font-mono text-[12px]">
          <Kicker>active configuration</Kicker>
          <dl className="mt-1 mb-4 grid grid-cols-[100px_1fr] gap-y-1 text-text-secondary">
            {Object.entries(summary?.config ?? {}).map(([k, v]) => <Fragment key={k}><dt className="text-text-muted">{k}</dt><dd className="truncate">{String(v)}</dd></Fragment>)}
          </dl>
          <Kicker>providers</Kicker>
          <dl className="mt-1 grid grid-cols-[100px_1fr] gap-y-1 text-text-secondary">
            {Object.entries(ready?.providers ?? {}).map(([k, v]) => <Fragment key={k}><dt className="text-text-muted">{k}</dt><dd className="truncate">{v}</dd></Fragment>)}
          </dl>
          <p className="mt-4 text-[11px] text-text-faint">Costs are estimated from token usage at list prices; AWS billing is the source of truth.</p>
        </aside>
      </div>
    </div>
  );
}
