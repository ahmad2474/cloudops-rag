"""Token-budgeted context assembly from expanded parents."""

from cloudops_rag.chunking.models import ParentChunk
from cloudops_rag.chunking.tokens import count_tokens
from cloudops_rag.generation.models import ContextSource

_HEADER_OVERHEAD = 40  # tokens per source for the [S#] header line


def build_context(parents: list[ParentChunk], budget: int) -> list[ContextSource]:
    """Keep parents in rank order; truncate the one that crosses the budget; drop the rest."""
    out: list[ContextSource] = []
    used = 0
    for i, p in enumerate(parents, start=1):
        remaining = budget - used - _HEADER_OVERHEAD
        if remaining < 80:
            break
        content, tokens, truncated = p.content, p.token_count, False
        if tokens > remaining:
            content, truncated = _truncate(content, remaining), True
            tokens = count_tokens(content)
        out.append(
            ContextSource(
                sid=f"S{i}", parent=p, content=content, token_count=tokens, truncated=truncated
            )
        )
        used += tokens + _HEADER_OVERHEAD
    return out


def _truncate(text: str, max_tokens: int) -> str:
    paras = text.split("\n\n")
    kept: list[str] = []
    total = 0
    for para in paras:
        t = count_tokens(para)
        if total + t > max_tokens:
            break
        kept.append(para)
        total += t
    if not kept:  # single huge paragraph — hard cut on words
        words = text.split()
        return " ".join(words[: max(10, int(len(words) * max_tokens / max(count_tokens(text), 1)))])
    return "\n\n".join(kept)


def source_header(src: ContextSource) -> str:
    p = src.parent
    section = " > ".join(p.section_path) if p.section_path else "(top)"
    ver = f" · version {p.version}" if p.version else ""
    status = "" if p.status == "active" else f" · STATUS: {p.status.upper()}"
    return (
        f"[{src.sid}] {p.title} — {section} · {p.document_type} · "
        f"updated {p.updated_at}{ver}{status}"
    )
