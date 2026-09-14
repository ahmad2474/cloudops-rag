export function EmptyState({
  title,
  body,
  children,
}: {
  kicker?: string; // accepted for call-site compatibility; intentionally not rendered (no eyebrows)
  title: string;
  body?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-start gap-2 border border-dashed border-border-subtle p-6">
      <h2 className="text-sm text-text-primary">{title}</h2>
      {body && <p className="max-w-prose text-sm text-text-secondary">{body}</p>}
      {children}
    </div>
  );
}
