"""Heading-tree chunker.

Parent = the section under the nearest H2 (H1 when a document has no H2; the whole document
when it has no headings). Preamble before the first section heading becomes its own parent.
Oversized parents are split at H3 boundaries, then sequentially.

Child = blocks packed to ``target_tokens``. A code block or table is never split; a single
block larger than ``max_tokens`` is split on paragraph/sentence boundaries as a last resort.
"""

import re
from dataclasses import dataclass

from cloudops_rag.chunking.blocks import Block, split_blocks
from cloudops_rag.chunking.models import Chunk, ChunkedDocument, ParentChunk
from cloudops_rag.chunking.tokens import count_tokens
from cloudops_rag.ingestion.parsers.models import ParsedDocument


@dataclass(frozen=True)
class ChunkingConfig:
    target_tokens: int = 400
    max_tokens: int = 700
    parent_max_tokens: int = 2000
    parent_level: int = 2  # H2 sections are parents
    min_section_tokens: int = 40


@dataclass
class _Section:
    path: list[str]
    blocks: list[Block]


def _sections(blocks: list[Block], parent_level: int) -> list[_Section]:
    """Group blocks into sections keyed by heading trail down to parent_level (deeper headings
    stay inside their section as blocks so children keep their local heading)."""
    trail: dict[int, str] = {}
    sections: list[_Section] = []
    current = _Section(path=[], blocks=[])

    def path_now() -> list[str]:
        return [trail[lvl] for lvl in sorted(trail) if lvl <= parent_level]

    for b in blocks:
        if b.kind == "heading" and b.level <= parent_level:
            if current.blocks:
                sections.append(current)
            for lvl in list(trail):
                if lvl >= b.level:
                    del trail[lvl]
            trail[b.level] = b.text
            current = _Section(path=path_now(), blocks=[])
        elif b.kind == "heading":
            # Sub-heading: keep as a block so the child text carries it.
            current.blocks.append(Block("heading", f"{'#' * b.level} {b.text}", level=b.level))
        else:
            current.blocks.append(b)
    if current.blocks:
        sections.append(current)
    return sections


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _restates_title(heading: str, title: str) -> bool:
    h, t = _norm(heading), _norm(title)
    return bool(h) and (t.startswith(h) or h.startswith(t))


def _merge_tiny(sections: list[_Section], min_tokens: int) -> list[_Section]:
    """A section too small to stand alone (e.g. "See X.") joins its predecessor."""
    out: list[_Section] = []
    for sec in sections:
        tokens = sum(count_tokens(b.text) for b in sec.blocks)
        if out and tokens < min_tokens:
            out[-1].blocks.extend(
                [Block("heading", f"## {sec.path[-1]}", level=2)] if sec.path else []
            )
            out[-1].blocks.extend(sec.blocks)
        else:
            out.append(sec)
    return out


def _has_any_heading(blocks: list[Block], max_level: int) -> bool:
    return any(b.kind == "heading" and b.level <= max_level for b in blocks)


_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def _split_oversized(text: str, max_tokens: int) -> list[str]:
    if count_tokens(text) <= max_tokens:
        return [text]
    parts = [p for p in text.split("\n\n") if p.strip()]
    if len(parts) == 1:
        parts = _SENTENCE_END.split(text)
    out: list[str] = []
    buf = ""
    for p in parts:
        cand = f"{buf}\n\n{p}" if buf else p
        if buf and count_tokens(cand) > max_tokens:
            out.append(buf)
            buf = p
        else:
            buf = cand
    if buf:
        out.append(buf)
    return out


def _split_rows(lines: list[str], header: list[str], max_tokens: int, fence: str = "") -> list[str]:
    """Split a table (header repeated) or a code block (fence repeated) by lines."""
    out: list[str] = []
    buf: list[str] = []
    head_t = count_tokens("\n".join(header)) if header else 0
    for ln in lines:
        cand = [*buf, ln]
        if buf and head_t + count_tokens("\n".join(cand)) > max_tokens:
            out.append("\n".join(header + buf))
            buf = [ln]
        else:
            buf = cand
    if buf:
        out.append("\n".join(header + buf))
    if fence:
        out = [f"{fence}\n{part}\n```" for part in out]
    return out


def _split_table(text: str, max_tokens: int) -> list[str]:
    if count_tokens(text) <= max_tokens:
        return [text]
    lines = text.split("\n")
    is_sep = len(lines) > 2 and set(lines[1].replace("|", "").strip()) <= set("-: ")
    header = lines[:2] if is_sep else []
    return _split_rows(lines[len(header) :], header, max_tokens)


def _split_code(text: str, max_tokens: int) -> list[str]:
    if count_tokens(text) <= max_tokens:
        return [text]
    lines = text.split("\n")
    fence = lines[0]
    body = lines[1:-1] if lines[-1].startswith(("```", "~~~")) else lines[1:]
    return _split_rows(body, [], max_tokens, fence=fence)


def _pack(blocks: list[Block], cfg: ChunkingConfig) -> list[str]:
    """Greedy packing of blocks into child texts around target_tokens."""
    pieces: list[str] = []
    for b in blocks:
        if b.kind == "table":
            pieces.extend(_split_table(b.text, cfg.max_tokens))
        elif b.kind == "code":
            pieces.extend(_split_code(b.text, cfg.max_tokens))
        else:
            pieces.extend(_split_oversized(b.text, cfg.max_tokens))

    children: list[str] = []
    buf: list[str] = []
    buf_tokens = 0
    for piece in pieces:
        t = count_tokens(piece)
        if buf and buf_tokens + t > cfg.target_tokens:
            children.append("\n\n".join(buf))
            buf, buf_tokens = [], 0
        buf.append(piece)
        buf_tokens += t
    if buf:
        children.append("\n\n".join(buf))
    # Absorb a tiny trailing child (e.g. a lone heading) into the previous one.
    if len(children) > 1 and count_tokens(children[-1]) < 40:
        last = children.pop()
        children[-1] = f"{children[-1]}\n\n{last}"
    return children


def chunk_document(doc: ParsedDocument, cfg: ChunkingConfig | None = None) -> ChunkedDocument:
    cfg = cfg or ChunkingConfig()
    blocks = split_blocks(doc.body)
    level = cfg.parent_level if _has_any_heading(blocks, cfg.parent_level) else 1
    sections = (
        _sections(blocks, level)
        if _has_any_heading(blocks, level)
        else [_Section(path=[], blocks=blocks)]
    )
    sections = _merge_tiny(sections, cfg.min_section_tokens)
    for sec in sections:
        if sec.path and _restates_title(sec.path[0], doc.title):
            sec.path = sec.path[1:]

    # Split oversized sections into several parents (sequentially by child boundaries).
    m = doc.metadata
    common = {
        "document_id": m.document_id,
        "title": m.title,
        "source": m.source,
        "source_url": m.source_url,
        "document_type": m.document_type,
        "version": m.version,
        "environment": m.environment,
        "permissions": list(m.permissions),
        "status": m.status,
        "updated_at": m.updated_at.isoformat(),
        "content_hash": doc.content_hash,
    }

    parents: list[ParentChunk] = []
    chunks: list[Chunk] = []
    position = 0
    for sec in sections:
        child_texts = _pack(sec.blocks, cfg)
        # group children into parents no larger than parent_max_tokens
        groups: list[list[str]] = []
        cur: list[str] = []
        cur_t = 0
        for ct in child_texts:
            t = count_tokens(ct)
            if cur and cur_t + t > cfg.parent_max_tokens:
                groups.append(cur)
                cur, cur_t = [], 0
            cur.append(ct)
            cur_t += t
        if cur:
            groups.append(cur)

        for g in groups:
            pidx = len(parents)
            parent_id = f"{m.document_id}#{pidx:03d}"
            child_ids: list[str] = []
            for cidx, text in enumerate(g):
                chunk_id = f"{parent_id}.{cidx:03d}"
                child_ids.append(chunk_id)
                chunks.append(
                    Chunk(
                        **common,
                        section_path=list(sec.path),
                        content=text,
                        token_count=count_tokens(text),
                        chunk_id=chunk_id,
                        parent_id=parent_id,
                        position=position,
                    )
                )
                position += 1
            parent_text = "\n\n".join(g)
            parents.append(
                ParentChunk(
                    **common,
                    section_path=list(sec.path),
                    content=parent_text,
                    token_count=count_tokens(parent_text),
                    parent_id=parent_id,
                    child_ids=child_ids,
                )
            )
    return ChunkedDocument(
        document_id=m.document_id, content_hash=doc.content_hash, parents=parents, chunks=chunks
    )
