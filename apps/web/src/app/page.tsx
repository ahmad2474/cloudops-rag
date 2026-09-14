import { fetchReady } from "@/lib/api";

/**
 * Phase 0 placeholder. Proves the frontend ↔ API wiring and the token system.
 * The real Operations Intelligence Console is designed and built in Phase 9.
 */
export default async function Home() {
  const ready = await fetchReady();

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-8 px-6 py-16">
      <header className="flex items-baseline justify-between border-b border-border-subtle pb-4">
        <h1 className="font-mono text-sm tracking-[0.2em] text-text-secondary uppercase">
          CloudOps Intelligence
        </h1>
        <StatusPill state={ready ? (ready.search ? "ok" : "degraded") : "offline"} />
      </header>

      <section className="grid gap-4 sm:grid-cols-2">
        <Card label="Phase">
          <span className="font-mono text-2xl">0</span>
          <span className="ml-2 text-text-secondary">Foundation</span>
        </Card>
        <Card label="API">
          <dl className="font-mono text-xs leading-6" data-testid="providers">
            {ready ? (
              Object.entries(ready.providers).map(([k, v]) => (
                <div key={k} className="flex justify-between gap-4">
                  <dt className="text-text-muted">{k}</dt>
                  <dd className="truncate">{v}</dd>
                </div>
              ))
            ) : (
              <span className="text-text-muted">unreachable — start with `make api`</span>
            )}
          </dl>
        </Card>
      </section>
    </main>
  );
}

function Card({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="rounded-md border border-border-subtle bg-surface-1 p-4">
      <div className="mb-2 font-mono text-[11px] tracking-widest text-text-muted uppercase">{label}</div>
      {children}
    </div>
  );
}

function StatusPill({ state }: { state: "ok" | "degraded" | "offline" }) {
  const styles = {
    ok: "text-ok",
    degraded: "text-warn",
    offline: "text-text-muted",
  } as const;
  return (
    <span
      role="status"
      data-testid="api-status"
      data-state={state}
      className={`font-mono text-xs tracking-widest uppercase ${styles[state]}`}
    >
      ● {state}
    </span>
  );
}
