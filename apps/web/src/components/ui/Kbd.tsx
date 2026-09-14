export function Kbd({ children }: { children: React.ReactNode }) {
  return (
    <kbd className="inline-flex h-4 min-w-4 items-center justify-center rounded-[3px] border border-border-strong bg-surface-2 px-1 font-mono text-[10px] text-text-muted">
      {children}
    </kbd>
  );
}
