export function Kicker({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`font-mono text-[11px] tracking-[0.18em] text-text-muted uppercase ${className}`}>{children}</div>
  );
}
