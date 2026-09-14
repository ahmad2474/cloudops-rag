import type { ReactNode } from "react";

type Tone = "neutral" | "accent" | "ok" | "warn" | "danger" | "muted";

const tones: Record<Tone, string> = {
  neutral: "border-border-strong text-text-secondary",
  accent: "border-accent-50 text-accent bg-accent-15",
  ok: "border-ok/40 text-ok bg-ok/10",
  warn: "border-warn/40 text-warn bg-warn/10",
  danger: "border-danger/40 text-danger bg-danger/10",
  muted: "border-border-subtle text-text-muted",
};

export function Pill({
  tone = "neutral",
  children,
  title,
  className = "",
}: {
  tone?: Tone;
  children: ReactNode;
  title?: string;
  className?: string;
}) {
  return (
    <span
      title={title}
      className={`inline-flex h-5 items-center gap-1 rounded-sm border px-1.5 font-mono text-[11px] leading-none tracking-wide whitespace-nowrap ${tones[tone]} ${className}`}
    >
      {children}
    </span>
  );
}
