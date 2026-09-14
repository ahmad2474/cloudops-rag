/** One-ink luminance ramp for any 0..1 score (evidence strength, rerank, fusion). */
export function Ramp({
  value,
  label,
  width = 96,
  tint,
}: {
  value: number | null | undefined;
  label?: string;
  width?: number;
  tint?: string;
}) {
  const v = value == null ? 0 : Math.max(0, Math.min(1, value));
  const cells = 10;
  const lit = Math.round(v * cells);
  return (
    <span className="inline-flex items-center gap-2" style={{ width }} aria-label={`${label ?? "score"} ${Math.round(v * 100)}%`}>
      <span className="flex h-2 flex-1 gap-px" aria-hidden="true">
        {Array.from({ length: cells }, (_, i) => (
          <span
            key={i}
            className="flex-1 rounded-[1px]"
            style={{
              background: i < lit ? (tint ?? "var(--accent)") : "var(--surface-3)",
              opacity: i < lit ? 0.35 + (0.65 * (i + 1)) / cells : 1,
            }}
          />
        ))}
      </span>
    </span>
  );
}
