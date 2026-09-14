"""Detect sources that plausibly disagree, so the prompt can say so (spec §1 step 9, §46)."""

import re
from datetime import date

from cloudops_rag.generation.models import Conflict, ContextSource

_STOP = {
    "runbook",
    "policy",
    "architecture",
    "troubleshooting",
    "the",
    "a",
    "an",
    "of",
    "for",
    "and",
    "to",
    "in",
    "on",
    "guide",
    "procedure",
    "acme",
}
_WORD = re.compile(r"[a-z0-9]+")


def _topic(title: str) -> set[str]:
    words = (w[:-1] if w.endswith("s") and len(w) > 3 else w for w in _WORD.findall(title.lower()))
    return {w for w in words if w not in _STOP and len(w) > 2}


def _same_topic(a: ContextSource, b: ContextSource) -> bool:
    """Containment of the smaller title's topic words in the larger one's (≥ 0.5).

    Containment, not Jaccard: "Policy: Production access (2024)" vs "Policy: Production access
    (Privileged Access Workflow)" must match even though the longer title has extra words.
    """
    ta, tb = _topic(a.parent.title), _topic(b.parent.title)
    if not ta or not tb or a.parent.document_id == b.parent.document_id:
        return False
    return len(ta & tb) / min(len(ta), len(tb)) >= 0.5


def _newer(a: ContextSource, b: ContextSource) -> ContextSource:
    return a if a.parent.updated_at >= b.parent.updated_at else b


def detect_conflicts(sources: list[ContextSource], *, stale_days: int = 365) -> list[Conflict]:
    out: list[Conflict] = []
    seen: set[tuple[str, str]] = set()
    for i, a in enumerate(sources):
        if a.parent.status == "deprecated":
            active = [s for s in sources if s.parent.status == "active" and _same_topic(a, s)]
            pref = active[0].sid if active else ""
            out.append(
                Conflict(
                    kind="deprecated",
                    sids=[a.sid, *[s.sid for s in active]],
                    preferred=pref,
                    note=f"{a.sid} is DEPRECATED"
                    + (f"; prefer {pref} (active)" if pref else "; treat as history only"),
                )
            )
        for b in sources[i + 1 :]:
            pair = sorted((a.parent.document_id, b.parent.document_id))
            key = (pair[0], pair[1])
            if key in seen or not _same_topic(a, b):
                continue
            if a.parent.status == "deprecated" or b.parent.status == "deprecated":
                continue
            seen.add(key)
            if a.parent.version and b.parent.version and a.parent.version != b.parent.version:
                n = _newer(a, b)
                out.append(
                    Conflict(
                        kind="version",
                        sids=[a.sid, b.sid],
                        preferred=n.sid,
                        note=f"{a.sid} (v{a.parent.version}) and {b.sid} (v{b.parent.version}) "
                        f"cover the same topic; prefer {n.sid} unless the question names a version",
                    )
                )
                continue
            try:
                da, db = (
                    date.fromisoformat(a.parent.updated_at),
                    date.fromisoformat(b.parent.updated_at),
                )
            except ValueError:
                continue
            if abs((da - db).days) >= stale_days:
                n = _newer(a, b)
                older = b if n is a else a
                out.append(
                    Conflict(
                        kind="stale",
                        sids=[a.sid, b.sid],
                        preferred=n.sid,
                        note=f"{older.sid} (updated {older.parent.updated_at}) is much older than "
                        f"{n.sid} ({n.parent.updated_at}); prefer {n.sid} where they disagree",
                    )
                )
    return out


def conflict_note(conflicts: list[Conflict]) -> str:
    if not conflicts:
        return ""
    lines = "\n".join(f"- {c.note}" for c in conflicts)
    return f"\n\nSource notes (from metadata, not content):\n{lines}\n"
