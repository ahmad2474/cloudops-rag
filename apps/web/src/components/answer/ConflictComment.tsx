import { Pill } from "@/components/ui/Pill";
import type { Conflict } from "@/lib/types";

const KIND: Record<Conflict["kind"], string> = {
  version: "version conflict",
  deprecated: "deprecated source",
  stale: "possibly stale",
};

export function ConflictComment({ conflict, onSelectSid }: { conflict: Conflict; onSelectSid: (sid: string) => void }) {
  return (
    <div className="callout mx-3 my-1 ml-[44px] px-3 py-2 text-[13px]" role="note">
      <div className="mb-1 flex items-center gap-2">
        <Pill tone="warn">review · {KIND[conflict.kind]}</Pill>
        {conflict.preferred && (
          <button type="button" onClick={() => onSelectSid(conflict.preferred)} className="font-mono text-[11px] text-text-secondary underline-offset-2 hover:underline">
            prefer {conflict.preferred}
          </button>
        )}
      </div>
      <p className="text-text-secondary">{conflict.note}</p>
    </div>
  );
}
