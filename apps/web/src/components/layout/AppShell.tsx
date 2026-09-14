"use client";

import { MotionConfig } from "framer-motion";
import { usePathname, useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { CommandBar } from "@/components/layout/CommandBar";
import { useBenchSettings, type BenchSettings } from "@/hooks/useBenchSettings";
import { useAuth } from "@/lib/auth";

interface Shell {
  settings: BenchSettings;
  setSettings: (p: Partial<BenchSettings>) => void;
  setQueryField: (node: React.ReactNode) => void;
}

const ShellCtx = createContext<Shell | null>(null);

export function useShell(): Shell {
  const v = useContext(ShellCtx);
  if (!v) throw new Error("useShell outside AppShell");
  return v;
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const [settings, setSettings] = useBenchSettings();
  const [queryField, setQueryFieldState] = useState<React.ReactNode>(null);
  const setQueryField = useCallback((n: React.ReactNode) => setQueryFieldState(n), []);
  const { principal, loading } = useAuth();
  const router = useRouter();
  const path = usePathname();

  useEffect(() => {
    if (!loading && !principal && path !== "/login") router.replace(`/login?next=${encodeURIComponent(path)}`);
  }, [loading, principal, path, router]);

  const value = useMemo(() => ({ settings, setSettings, setQueryField }), [settings, setSettings, setQueryField]);

  if (path === "/login") return <MotionConfig reducedMotion="user"><ShellCtx.Provider value={value}>{children}</ShellCtx.Provider></MotionConfig>;
  if (loading || !principal) {
    return (
      <div className="flex h-screen items-center justify-center font-mono text-[12px] text-text-muted" aria-busy="true">
        {loading ? "checking session…" : "redirecting to sign-in…"}
      </div>
    );
  }
  return (
    <MotionConfig reducedMotion="user">
      <ShellCtx.Provider value={value}>
        <CommandBar settings={settings} onSettings={setSettings} queryField={queryField} />
        <main id="main">{children}</main>
      </ShellCtx.Provider>
    </MotionConfig>
  );
}
