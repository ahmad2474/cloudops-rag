import { Ramp } from "@/components/ui/Ramp";
import { fmtMs, fmtNum, fmtUsd } from "@/lib/format";
import type { ReportSummary } from "@/lib/types";

const COLS: { key: keyof ReportSummary["summary"]; label: string }[] = [
  { key: "recall_at_5", label: "R@5" },
  { key: "recall_at_10", label: "R@10" },
  { key: "mrr", label: "MRR" },
  { key: "ndcg_at_10", label: "NDCG@10" },
  { key: "abstention_accuracy", label: "abstain" },
  { key: "citation_precision", label: "cite P" },
  { key: "faithfulness", label: "faithful" },
];

export function StrategyTable({ reports, onPick, active }: { reports: ReportSummary[]; onPick: (r: ReportSummary) => void; active: string | null }) {
  return (
    <table className="locked w-full font-mono text-[12px]" aria-label="Evaluation runs">
      <thead className="bg-surface-1 text-left text-text-muted">
        <tr>
          <th className="w-48 px-3 py-1.5 font-normal">strategy</th>
          <th className="w-24 px-2 py-1.5 font-normal">date</th>
          <th className="w-14 px-2 py-1.5 text-right font-normal">n</th>
          {COLS.map((c) => <th key={c.key} className="w-24 px-2 py-1.5 text-right font-normal">{c.label}</th>)}
          <th className="w-16 px-2 py-1.5 text-right font-normal">ACL</th>
          <th className="w-24 px-2 py-1.5 text-right font-normal">p95</th>
          <th className="w-24 px-2 py-1.5 text-right font-normal">$/query</th>
        </tr>
      </thead>
      <tbody>
        {reports.map((r) => (
          <tr key={r.name} onClick={() => onPick(r)} className={`cursor-pointer border-t border-border-subtle ${active === r.name ? "bg-surface-2" : "hover:bg-surface-1"}`}>
            <td className="truncate px-3 py-1.5 text-text-primary" title={r.name}>{r.strategy}{r.generation ? "" : <span className="text-text-faint"> · retrieval only</span>}</td>
            <td className="px-2 py-1.5 text-text-secondary tabular-nums">{r.generated_at.slice(0, 10)}</td>
            <td className="px-2 py-1.5 text-right text-text-secondary tabular-nums">{r.summary.n}</td>
            {COLS.map((c) => {
              const v = r.summary[c.key] as number | null;
              return (
                <td key={c.key} className="px-2 py-1.5 text-right tabular-nums">
                  {v == null ? <span className="text-text-faint">—</span> : <span className="inline-flex items-center gap-2"><Ramp value={v} width={40} /><span className="text-text-primary">{fmtNum(v)}</span></span>}
                </td>
              );
            })}
            <td className={`px-2 py-1.5 text-right tabular-nums ${r.summary.acl_violations ? "text-danger" : "text-ok"}`}>{r.summary.acl_violations}</td>
            <td className="px-2 py-1.5 text-right text-text-secondary tabular-nums">{fmtMs(r.latency_ms.generation_p95 ?? r.latency_ms.retrieval_p95)}</td>
            <td className="px-2 py-1.5 text-right text-text-secondary tabular-nums">{fmtUsd(r.cost.per_query_usd, 5)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
