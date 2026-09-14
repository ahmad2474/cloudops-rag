"use client";

import * as Select from "@radix-ui/react-select";
import { Check, ChevronDown, LogOut } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Kbd } from "@/components/ui/Kbd";
import { useAuth } from "@/lib/auth";
import type { Strategy } from "@/lib/types";
import type { BenchSettings } from "@/hooks/useBenchSettings";

const TABS = [
  { href: "/", label: "Bench" },
  { href: "/incidents", label: "Incidents" },
  { href: "/explorer", label: "Explorer" },
  { href: "/evaluation", label: "Evaluation" },
  { href: "/system", label: "System" },
];

const STRATEGIES: { value: Strategy | "default"; label: string }[] = [
  { value: "default", label: "server default" },
  { value: "vector", label: "vector" },
  { value: "bm25", label: "bm25" },
  { value: "hybrid_rrf", label: "hybrid · rrf" },
  { value: "hybrid_weighted", label: "hybrid · weighted" },
];

export function CommandBar({
  settings,
  onSettings,
  queryField,
}: {
  settings: BenchSettings;
  onSettings: (p: Partial<BenchSettings>) => void;
  queryField?: React.ReactNode;
}) {
  const path = usePathname();
  const { principal, logout } = useAuth();
  const role = principal?.roles[0] ?? "—";
  return (
    <header className="sticky top-0 z-30 border-b border-border-subtle bg-surface-1/95 backdrop-blur" role="banner">
    <div className="flex flex-wrap items-stretch">
      <Link
        href="/"
        className="flex h-[var(--bar-h)] shrink-0 items-center gap-2 border-r border-border-subtle px-3 font-mono text-[11px] tracking-[0.2em] text-text-secondary uppercase hover:text-text-primary lg:px-4"
      >
        <span className="inline-block h-2 w-2 bg-accent" aria-hidden="true" />
        <span className="hidden sm:inline">CloudOps Intelligence</span>
        <span className="sm:hidden">CI</span>
      </Link>
      <nav aria-label="Sections" className="pane flex h-[var(--bar-h)] min-w-0 flex-1 items-stretch overflow-x-auto border-r border-border-subtle lg:flex-none">
        {TABS.map((t) => {
          const active = t.href === "/" ? path === "/" : path.startsWith(t.href);
          return (
            <Link
              key={t.href}
              href={t.href}
              aria-current={active ? "page" : undefined}
              className={`flex items-center px-3 text-[13px] ${
                active ? "text-text-primary shadow-[inset_0_-2px_0_var(--accent)]" : "text-text-secondary hover:text-text-primary"
              }`}
            >
              {t.label}
            </Link>
          );
        })}
      </nav>
      <div className="order-last flex min-w-0 basis-full items-center border-t border-border-subtle px-3 py-1.5 lg:order-none lg:basis-auto lg:flex-1 lg:border-t-0 lg:py-0">
        {queryField}
      </div>
      <div className="ml-auto flex h-[var(--bar-h)] shrink-0 items-center gap-2 border-l border-border-subtle px-3 lg:ml-0">
        <div className="hidden items-center gap-2 md:flex">
        <Select.Root
          value={settings.strategy ?? "default"}
          onValueChange={(v) => onSettings({ strategy: v === "default" ? null : (v as Strategy) })}
        >
          <Select.Trigger
            aria-label="Retrieval strategy"
            className="inline-flex h-6 items-center gap-1 rounded-sm border border-border-strong px-2 font-mono text-[11px] text-text-secondary hover:text-text-primary"
          >
            <span className="text-text-muted">strategy</span>
            <Select.Value />
            <ChevronDown className="h-3 w-3" aria-hidden="true" />
          </Select.Trigger>
          <Select.Portal>
            <Select.Content position="popper" sideOffset={4} className="z-50 min-w-40 border border-border-strong bg-surface-2 p-1 font-mono text-[12px] shadow-none">
              <Select.Viewport>
                {STRATEGIES.map((s) => (
                  <Select.Item
                    key={s.value}
                    value={s.value}
                    className="flex cursor-default items-center justify-between gap-2 px-2 py-1 text-text-secondary outline-none data-[highlighted]:bg-surface-3 data-[highlighted]:text-text-primary"
                  >
                    <Select.ItemText>{s.label}</Select.ItemText>
                    <Select.ItemIndicator>
                      <Check className="h-3 w-3 text-accent" />
                    </Select.ItemIndicator>
                  </Select.Item>
                ))}
              </Select.Viewport>
            </Select.Content>
          </Select.Portal>
        </Select.Root>
        <button
          type="button"
          onClick={() => onSettings({ rerank: settings.rerank ? null : true })}
          aria-pressed={!!settings.rerank}
          className={`h-6 rounded-sm border px-2 font-mono text-[11px] ${
            settings.rerank ? "border-accent-50 bg-accent-15 text-accent" : "border-border-strong text-text-secondary hover:text-text-primary"
          }`}
        >
          rerank
        </button>
        </div>
        <span className="ml-1 inline-flex h-6 items-center gap-1 rounded-sm border border-border-strong px-2 font-mono text-[11px] text-text-secondary" title={principal?.username}>
          <span className="text-text-muted">role</span> {role}
        </span>
        <button type="button" onClick={logout} aria-label="Sign out" className="text-text-muted hover:text-text-primary">
          <LogOut className="h-3.5 w-3.5" />
        </button>
        <span className="hidden items-center gap-1 lg:inline-flex">
          <Kbd>⌘</Kbd>
          <Kbd>K</Kbd>
        </span>
      </div>
    </div>
    </header>
  );
}
