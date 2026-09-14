import { Pill } from "@/components/ui/Pill";
import type { AnswerResponse } from "@/lib/types";

/** Non-answer outcomes rendered as a review verdict, not an error toast. */
export function Verdict({ response }: { response: AnswerResponse }) {
  const map = {
    abstained: { tone: "warn" as const, kicker: "changes requested", title: "Insufficient evidence to answer reliably", body: "The model declined to merge this answer: the authorized sources did not support it, or no claim could be cited." },
    no_authorized_evidence: { tone: "danger" as const, kicker: "withheld", title: "No authorized evidence", body: "Retrieval returned nothing your role may read for this question. This is deliberate: authorization is applied before the model sees any document." },
    blocked: { tone: "danger" as const, kicker: "blocked", title: "Answer withheld by a safety check", body: `Guard: ${response.guard_reasons.join(", ") || "policy"}. The generated text tried to expose instructions or obey an embedded override and was not returned.` },
    answered: { tone: "ok" as const, kicker: "", title: "", body: "" },
  }[response.status];
  if (response.status === "answered") return null;
  return (
    <div className="m-3 border border-border-subtle bg-surface-1 p-4" role="status">
      <Pill tone={map.tone}>{map.kicker}</Pill>
      <h2 className="mt-2 text-[15px] text-text-primary">{map.title}</h2>
      <p className="mt-1 max-w-prose text-[13px] text-text-secondary">{map.body}</p>
      {response.sources.length > 0 && (
        <p className="mt-2 font-mono text-[11px] text-text-muted">{response.sources.length} source{response.sources.length > 1 ? "s were" : " was"} offered to the model — inspect them in the evidence pane.</p>
      )}
    </div>
  );
}
