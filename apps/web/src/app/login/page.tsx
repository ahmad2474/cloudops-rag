"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { Kicker } from "@/components/ui/Kicker";
import { Pill } from "@/components/ui/Pill";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const DEMO_PASSWORD = process.env.NEXT_PUBLIC_DEMO_PASSWORD ?? "";
const DEMO = [
  { user: "dev", role: "developer", sees: "runbooks, troubleshooting, policies, incidents, public docs" },
  { user: "pe", role: "platform-engineer", sees: "+ DR, security account layout, Terraform runbooks, PE-only incidents" },
  { user: "sec", role: "security-admin", sees: "+ break-glass, credential rotation, security postmortems" },
];

function LoginForm() {
  const { login } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const next = params.get("next") || "/";
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const go = async (u: string, p: string) => {
    setBusy(u);
    setError(null);
    try {
      await login(u, p);
      router.replace(next);
    } catch (e) {
      setError(e instanceof ApiError && e.status === 401 ? "Invalid credentials." : e instanceof ApiError ? `${e.title}: ${e.detail}` : "API unreachable — is the backend running on :8000?");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-3xl flex-col justify-center px-6 py-16">
      <div className="mb-8 flex items-center gap-2 font-mono text-[11px] tracking-[0.2em] text-text-secondary uppercase">
        <span className="inline-block h-2 w-2 bg-accent" aria-hidden="true" /> CloudOps Intelligence · Acme Cloud Platform
      </div>
      <h1 className="text-[22px] font-medium text-text-primary">Sign in</h1>
      <p className="mt-1 max-w-prose text-[14px] text-text-secondary">What you can see is decided before retrieval. Pick a role to see the knowledge base as that engineer.</p>

      {DEMO_PASSWORD && (
        <table className="locked mt-6 w-full border border-border-subtle font-mono text-[12px]" aria-label="Demo users">
          <thead className="bg-surface-1 text-left text-text-muted">
            <tr><th className="w-16 px-3 py-1.5 font-normal">user</th><th className="w-40 px-2 py-1.5 font-normal">role</th><th className="px-2 py-1.5 font-normal">can read</th><th className="w-24 px-2 py-1.5 font-normal"></th></tr>
          </thead>
          <tbody>
            {DEMO.map((d) => (
              <tr key={d.user} className="border-t border-border-subtle bg-surface-1 hover:bg-surface-2">
                <td className="px-3 py-2 text-text-primary">{d.user}</td>
                <td className="px-2 py-2"><Pill tone="accent">{d.role}</Pill></td>
                <td className="truncate px-2 py-2 font-sans text-[12.5px] text-text-secondary" title={d.sees}>{d.sees}</td>
                <td className="px-2 py-2 text-right">
                  <button type="button" disabled={!!busy} onClick={() => go(d.user, DEMO_PASSWORD)} className="h-6 border border-accent-50 bg-accent-15 px-2 text-accent hover:bg-accent-30 disabled:opacity-60">
                    {busy === d.user ? "…" : "sign in"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <form
        className="mt-6 grid gap-2 border border-border-subtle bg-surface-1 p-4 sm:grid-cols-[1fr_1fr_auto]"
        onSubmit={(e) => {
          e.preventDefault();
          void go(username, password);
        }}
      >
        <Kicker className="sm:col-span-3">credentials</Kicker>
        <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="username" autoComplete="username" aria-label="Username" className="h-8 border border-border-strong bg-surface-0 px-2 font-mono text-[13px] text-text-primary" />
        <input value={password} onChange={(e) => setPassword(e.target.value)} placeholder="password" type="password" autoComplete="current-password" aria-label="Password" className="h-8 border border-border-strong bg-surface-0 px-2 font-mono text-[13px] text-text-primary" />
        <button type="submit" disabled={!!busy || !username || !password} className="h-8 border border-accent-50 bg-accent-15 px-3 font-mono text-[12px] text-accent hover:bg-accent-30 disabled:opacity-50">sign in</button>
      </form>
      {error && <p role="alert" className="mt-3 font-mono text-[12px] text-danger">{error}</p>}
      <p className="mt-8 font-mono text-[11px] text-text-faint">Sessions are short-lived JWTs. Roles are validated on every request; authorization is a search filter, not a prompt.</p>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
