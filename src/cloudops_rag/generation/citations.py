"""Parse and validate [S#] citations against the sources actually offered to the model."""

import re

from cloudops_rag.generation.models import Citation, ContextSource

_CITE = re.compile(r"\[(S\d+)\]")


def to_citation(src: ContextSource) -> Citation:
    p = src.parent
    return Citation(
        sid=src.sid,
        document_id=p.document_id,
        parent_id=p.parent_id,
        title=p.title,
        section=" > ".join(p.section_path) if p.section_path else "",
        source_url=p.source_url,
        document_type=p.document_type,
        version=p.version,
        updated_at=p.updated_at,
        excerpt=_excerpt(src.content),
        content=src.content,
        token_count=src.token_count,
    )


def validate_citations(
    answer: str, sources: list[ContextSource]
) -> tuple[str, list[Citation], list[str]]:
    """Return (cleaned answer, cited sources in first-use order, dropped unknown ids).

    Unknown ids are removed from the text so the UI never renders a dangling citation.
    """
    known = {s.sid: s for s in sources}
    cited: list[str] = []
    dropped: list[str] = []
    for sid in _CITE.findall(answer):
        if sid in known:
            if sid not in cited:
                cited.append(sid)
        elif sid not in dropped:
            dropped.append(sid)
    cleaned = answer
    for sid in dropped:
        cleaned = cleaned.replace(f"[{sid}]", "")
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned).strip()
    return cleaned, [to_citation(known[s]) for s in cited], dropped


def _excerpt(text: str, limit: int = 240) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[: limit - 1].rsplit(" ", 1)[0] + "…"
