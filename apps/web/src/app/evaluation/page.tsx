"use client";

import { useEffect, useState } from "react";
import { StrategyTable } from "@/components/evaluation/StrategyTable";
import { useShell } from "@/components/layout/AppShell";
import { EmptyState } from "@/components/ui/EmptyState";
import { Kicker } from "@/components/ui/Kicker";
import { Ramp } from "@/components/ui/Ramp";
import { Skeleton } from "@/components/ui/Skeleton";
import { api } from "@/lib/api";
import { fmtMs, fmtNum, fmtUsd } from "@/lib/format";
import type { ReportSummary } from "@/lib/types";

export default function EvaluationPage() {
  const { setQueryField } = useShell();
  const [reports, setReports] = useState<ReportSummary[] | null>(null);
  const [active, setActive] = useState<ReportSummary | null>(null);
  useEffect(() => { setQueryField(<span className="font-mono text-[12px] text-text-muted">RAG evaluation · 315-question benchmark · numbers from recorded runs only</span>); }, [setQueryField]);
  useEffect(() => {
    api.reports().then((r) => { setReports(r); setActive(r[0] ?? null); }).catch(() => setReports([]));
  }, []);
  if (reports === null) return <div className="grid gap-px p-3">{Array.from({ length: 6 }, (_, i) => <Skeleton key={i} className="h-7" />)}</div>;
  if (reports.length === 0) {
    return (
      <div className="p-6">
        <EmptyState kicker="evaluation" title="No recorded runs yet" body="This dashboard reads evaluation/reports/*.json. Runs are produced by `make eval` (retrieval) and `make eval-full` (generation + judge) against real providers. Nothing is shown until a run exists — no placeholder numbers.">
          <p className="font-mono text-[11px] text-text-muted">Pending: Bedrock quota provisioning on the AWS account.</p>
        </EmptyState>
      </div>
    );
  }
  return (
    <div>
      <div className="border-b border-border-subtle bg-surface-1 px-3 py-1.5 font-mono text-[11px]"><span className="tracking-widest text-text-muted uppercase">retrieval strategies</span> <span className="text-text-muted">· click a run for the per-category breakdown</span></div>
      <StrategyTable reports={reports} onPick={setActive} active={active?.name ?? null} />
      {active && (
        <div className="grid gap-px border-t border-border-subtle bg-border-subtle lg:grid-cols-[1fr_320px]">
          <div className="bg-surface-0">
            <div className="border-b border-border-subtle bg-surface-1 px-3 py-1.5 font-mono text-[11px] tracking-widest text-text-muted uppercase">by category · {active.strategy}</div>
            <table className="locked w-full font-mono text-[12px]">
              <thead className="text-left text-text-muted"><tr><th className="w-48 px-3 py-1 font-normal">category</th><th className="w-12 px-2 py-1 text-right font-normal">n</th><th className="px-2 py-1 font-normal">R@5</th><th className="px-2 py-1 font-normal">MRR</th><th className="px-2 py-1 font-normal">NDCG</th><th className="w-16 px-2 py-1 text-right font-normal">ACL</th><th className="w-20 px-2 py-1 text-right font-normal">abstain</th><th className="w-20 px-2 py-1 text-right font-normal">inject</th></tr></thead>
              <tbody>
                {Object.entries(active.by_category).map(([cat, b]) => (
                  <tr key={cat} className="border-t border-border-subtle">
                    <td className="px-3 py-1 text-text-primary">{cat}</td>
                    <td className="px-2 py-1 text-right text-text-secondary tabular-nums">{b.n}</td>
                    {(["recall_at_5", "mrr", "ndcg_at_10"] as const).map((k) => <td key={k} className="px-2 py-1"><span className="inline-flex items-center gap-2"><Ramp value={b[k]} width={80} /><span className="text-text-secondary tabular-nums">{fmtNum(b[k])}</span></span></td>)}
                    <td className={`px-2 py-1 text-right tabular-nums ${b.acl_violations ? "text-danger" : "text-ok"}`}>{b.acl_violations}</td>
                    <td className="px-2 py-1 text-right text-text-secondary tabular-nums">{fmtNum(b.abstention_accuracy)}</td>
                    <td className="px-2 py-1 text-right text-text-secondary tabular-nums">{fmtNum(b.injection_success_rate)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <aside className="bg-surface-1 p-4 font-mono text-[12px]">
            <Kicker>run</Kicker>
            <dl className="mt-1 mb-4 grid grid-cols-[90px_1fr] gap-y-1 text-text-secondary">
              <dt className="text-text-muted">file</dt><dd className="truncate">{active.name}</dd>
              <dt className="text-text-muted">dataset</dt><dd>v{active.dataset_version}</dd>
              <dt className="text-text-muted">embedding</dt><dd className="truncate">{active.providers.embedding}</dd>
              <dt className="text-text-muted">llm</dt><dd className="truncate">{active.providers.llm}</dd>
              <dt className="text-text-muted">reranker</dt><dd className="truncate">{active.providers.reranker ?? "off"}</dd>
            </dl>
            <Kicker>system</Kicker>
            <dl className="mt-1 grid grid-cols-[90px_1fr] gap-y-1 text-text-secondary">
              <dt className="text-text-muted">retrieval p50</dt><dd>{fmtMs(active.latency_ms.retrieval_p50)}</dd>
              <dt className="text-text-muted">retrieval p95</dt><dd>{fmtMs(active.latency_ms.retrieval_p95)}</dd>
              {active.latency_ms.generation_p95 != null && <><dt className="text-text-muted">generation p95</dt><dd>{fmtMs(active.latency_ms.generation_p95)}</dd></>}
              <dt className="text-text-muted">cost/query</dt><dd>{fmtUsd(active.cost.per_query_usd, 5)}</dd>
              <dt className="text-text-muted">run cost</dt><dd>{fmtUsd(active.cost.total_usd, 4)}</dd>
              <dt className="text-text-muted">ctx tokens</dt><dd>{Math.round(active.context.avg_tokens ?? 0)}</dd>
            </dl>
          </aside>
        </div>
      )}
    </div>
  );
}
