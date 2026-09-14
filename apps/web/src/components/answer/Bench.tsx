"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ChecksStrip } from "@/components/answer/ChecksStrip";
import { ClaimLines } from "@/components/answer/ClaimLines";
import { Verdict } from "@/components/answer/Verdict";
import { TrailPacket } from "@/components/retrieval/TrailPacket";
import { EvidencePane } from "@/components/sources/EvidencePane";
import { SourceStrip } from "@/components/sources/SourceStrip";
import { Kbd } from "@/components/ui/Kbd";
import { Pill } from "@/components/ui/Pill";
import type { BenchSettings } from "@/hooks/useBenchSettings";
import { ApiError, askStream } from "@/lib/api";
import { toClaimLines } from "@/lib/answer";
import type { AnswerResponse, Citation, Conflict, QueryPlan, TrailStep } from "@/lib/types";

type Phase = "idle" | "retrieving" | "synthesizing" | "done" | "error";

const EXAMPLES = [
  "Why are my EKS pods stuck in Pending?",
  "Which incident had subnet IP exhaustion?",
  "What is the correct EKS 1.31 pod networking procedure?",
  "How often are RDS credentials rotated — 90 or 180 days?",
  "Show me the break-glass procedure.",
];

export function Bench({ settings, registerQueryField }: { settings: BenchSettings; registerQueryField: (node: React.ReactNode) => void }) {
  const [question, setQuestion] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [error, setError] = useState<string | null>(null);
  const [trail, setTrail] = useState<TrailStep[]>([]);
  const [sources, setSources] = useState<Citation[]>([]);
  const [conflicts, setConflicts] = useState<Conflict[]>([]);
  const [plan, setPlan] = useState<QueryPlan | null>(null);
  const [streamed, setStreamed] = useState("");
  const [response, setResponse] = useState<AnswerResponse | null>(null);
  const [selectedSid, setSelectedSid] = useState<string | null>(null);
  const [activeLine, setActiveLine] = useState<number | null>(null);
  const abort = useRef<AbortController | null>(null);
  const input = useRef<HTMLInputElement>(null);

  const ask = useCallback(
    async (q: string) => {
      const text = q.trim();
      if (!text) return;
      abort.current?.abort();
      const ctl = new AbortController();
      abort.current = ctl;
      setPhase("retrieving");
      setError(null);
      setTrail([]);
      setSources([]);
      setConflicts([]);
      setPlan(null);
      setStreamed("");
      setResponse(null);
      setSelectedSid(null);
      setActiveLine(null);
      try {
        for await (const ev of askStream(
          { question: text, strategy: settings.strategy, rerank: settings.rerank, context_mode: settings.contextMode, filters: { include_deprecated: settings.includeDeprecated } },
          ctl.signal,
        )) {
          if (ev.event === "retrieval") {
            setTrail(ev.trail);
            setSources(ev.sources);
            setConflicts(ev.conflicts);
            setPlan(ev.query_plan);
            setPhase("synthesizing");
          } else if (ev.event === "delta") {
            setStreamed((s) => s + ev.text);
          } else if (ev.event === "done") {
            setResponse(ev.response);
            setTrail(ev.response.trail);
            setSources(ev.response.sources);
            setConflicts(ev.response.conflicts);
            setPhase("done");
            const firstCited = toClaimLines(ev.response.answer).find((l) => l.sids.length > 0);
            setSelectedSid(firstCited?.sids[0] ?? ev.response.citations[0]?.sid ?? null);
            setActiveLine(firstCited?.n ?? null);
          }
        }
      } catch (e) {
        if ((e as Error).name === "AbortError") return;
        setPhase("error");
        setError(e instanceof ApiError ? `${e.title}: ${e.detail}${e.requestId ? ` (${e.requestId})` : ""}` : String(e));
      }
    },
    [settings],
  );

  const queryForm = (
    <form
      className="flex items-center gap-2 border-t border-border-subtle bg-surface-1 px-3 py-2"
      onSubmit={(e) => {
        e.preventDefault();
        void ask(question);
      }}
    >
      <span className="font-mono text-[11px] text-text-faint" aria-hidden="true">›</span>
      <input
        ref={input}
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="Ask the platform — e.g. why are my EKS pods stuck in Pending?"
        aria-label="Question"
        autoFocus
        className="h-8 w-full bg-transparent font-mono text-[13px] text-text-primary placeholder:text-text-faint focus:shadow-[inset_0_-1px_0_var(--accent)] focus:outline-none"
      />
      {phase === "retrieving" || phase === "synthesizing" ? (
        <button type="button" onClick={() => abort.current?.abort()} className="h-6 shrink-0 rounded-sm border border-border-strong px-2 font-mono text-[11px] text-text-secondary hover:text-text-primary">
          stop
        </button>
      ) : (
        <button type="submit" className="h-6 shrink-0 rounded-sm border border-accent-50 bg-accent-15 px-2 font-mono text-[11px] whitespace-nowrap text-accent hover:bg-accent-30">
          ask
        </button>
      )}
    </form>
  );

  // The command bar's query slot stays empty on the bench; the field lives in the pane.
  useEffect(() => {
    registerQueryField(null);
  }, [registerQueryField]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        input.current?.focus();
        input.current?.select();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const answerText = response?.status === "answered" ? response.answer : phase === "synthesizing" ? streamed : "";
  const lines = useMemo(() => toClaimLines(answerText), [answerText]);
  const citedSids = useMemo(() => new Set((response?.citations ?? []).map((c) => c.sid)), [response]);
  const claimText = activeLine ? (lines.find((l) => l.n === activeLine)?.raw ?? null) : null;

  // j/k claims, [ ] sources
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (document.activeElement && ["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)) return;
      if (!lines.length) return;
      if (e.key === "j" || e.key === "k") {
        e.preventDefault();
        setActiveLine((cur) => {
          const idx = cur ? lines.findIndex((l) => l.n === cur) : -1;
          const next = lines[Math.max(0, Math.min(lines.length - 1, idx + (e.key === "j" ? 1 : -1)))];
          if (next?.sids[0]) setSelectedSid(next.sids[0]);
          return next?.n ?? cur;
        });
      } else if ((e.key === "[" || e.key === "]") && sources.length) {
        e.preventDefault();
        setSelectedSid((cur) => {
          const i = sources.findIndex((s) => s.sid === cur);
          return sources[(i + (e.key === "]" ? 1 : -1) + sources.length) % sources.length]?.sid ?? cur;
        });
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [lines, sources]);

  const onSelectSid = useCallback((sid: string, line?: number) => {
    setSelectedSid(sid);
    if (line) setActiveLine(line);
  }, []);

  return (
    <div className="flex min-h-[calc(100vh-var(--bar-h))] flex-col lg:h-[calc(100vh-var(--bar-h))]">
      <div className="grid min-h-0 flex-1 grid-cols-1 gap-px bg-border-subtle lg:grid-cols-[52fr_48fr] lg:overflow-hidden">
        {/* LEFT: the change request */}
        <section className="flex min-h-0 min-w-0 flex-col bg-surface-0" aria-label="Answer">
          <header className="flex items-center gap-2 border-b border-border-subtle bg-surface-1 px-3 py-1.5 font-mono text-[11px]">
            <span className="tracking-widest text-text-primary uppercase">answer</span>
            {response && (
              <Pill tone={response.status === "answered" ? "ok" : response.status === "abstained" ? "warn" : "danger"}>
                {response.status.replaceAll("_", " ")}
              </Pill>
            )}
            {phase === "retrieving" && <Pill tone="accent">retrieving</Pill>}
            {phase === "synthesizing" && <Pill tone="accent">synthesizing</Pill>}
            {response?.query_plan.stripped_injection && <Pill tone="warn">question sanitised</Pill>}
            <span className="ml-auto hidden items-center gap-1 text-text-faint lg:flex">
              <Kbd>j</Kbd><Kbd>k</Kbd> claims <Kbd>[</Kbd><Kbd>]</Kbd> sources
            </span>
          </header>
          <div className="pane max-h-[70vh] min-h-0 flex-1 overflow-auto lg:max-h-none">
            {phase === "idle" && (
              <div className="p-6">
                <p className="max-w-prose text-[14px] text-text-secondary">
                  Ask an operational question. The answer arrives as numbered claims; each carries a marker to the section it was drawn from. Checks below the answer show how it was retrieved, what was cited, and how strong the evidence is.
                </p>
                <ul className="mt-4 grid gap-1 sm:grid-cols-2">
                  {EXAMPLES.map((ex) => (
                    <li key={ex}>
                      <button type="button" onClick={() => { setQuestion(ex); input.current?.focus(); void ask(ex); }} className="w-full border border-border-subtle bg-surface-1 px-3 py-2 text-left text-[13px] text-text-secondary hover:border-border-strong hover:text-text-primary">
                        {ex}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {phase === "error" && (
              <div className="m-3 border border-danger/40 bg-danger/10 p-3 font-mono text-[12px] text-danger" role="alert">{error}</div>
            )}
            {response && response.status !== "answered" && <Verdict response={response} />}
            {(lines.length > 0 || phase === "synthesizing") && (
              <ClaimLines lines={lines} selectedSid={selectedSid} activeLine={activeLine} onSelectSid={onSelectSid} onActivateLine={(n) => { setActiveLine(n); const s = lines.find((l) => l.n === n)?.sids[0]; if (s) setSelectedSid(s); }} conflicts={response?.conflicts ?? conflicts} streaming={phase === "synthesizing"} />
            )}
          </div>
          <ChecksStrip trail={trail} response={response} phase={phase} />
          {queryForm}
        </section>
        {/* RIGHT: the evidence file */}
        <section className="flex min-h-0 min-w-0 flex-col bg-surface-0" aria-label="Evidence">
          <div className="min-h-0 min-w-0 flex-1"><EvidencePane sources={sources} selectedSid={selectedSid} claimText={claimText} onSelectSid={(s) => onSelectSid(s)} citedSids={citedSids} /></div>
          <SourceStrip sources={sources} selectedSid={selectedSid} citedSids={citedSids} onSelect={(s) => onSelectSid(s)} />
        </section>
      </div>
      <TrailPacket trail={trail} plan={response?.query_plan ?? plan} usage={response?.usage ?? null} latency={response?.latency_ms ?? {}} />
    </div>
  );
}
