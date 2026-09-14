"""Turn retrieved children into the units the context builder will pack (spec §8).

- ``parent``: each child's H2 section (deduped, best-child order) — precision at retrieval,
  context at generation.
- ``child``: the retrieved chunks themselves — smallest context, fewest tokens.
- ``child_window``: each chunk plus ``window`` siblings on either side within its parent,
  merged into one unit per parent — a middle ground.

All modes return ``ParentChunk`` objects so the context builder and citations don't care;
synthetic units keep the real ``parent_id``/``child_ids`` so citations still resolve.
"""

from typing import Literal

from cloudops_rag.chunking.models import Chunk, ParentChunk
from cloudops_rag.chunking.tokens import count_tokens
from cloudops_rag.providers.base import SearchHit, SearchProvider

ContextMode = Literal["parent", "child", "child_window"]


def _unit_from_chunks(parent: ParentChunk | None, chunks: list[Chunk]) -> ParentChunk:
    first = chunks[0]
    text = "\n\n".join(c.content for c in chunks)
    base = first.model_dump(exclude={"chunk_id", "position", "parent_id"})
    return ParentChunk(
        **base,
        parent_id=first.parent_id,
        child_ids=[c.chunk_id for c in chunks],
    ).model_copy(
        update={
            "content": text,
            "token_count": count_tokens(text),
            "section_path": parent.section_path if parent else first.section_path,
        }
    )


async def build_units(
    hits: list[SearchHit], search: SearchProvider, *, mode: ContextMode, window: int = 1
) -> list[ParentChunk]:
    if mode == "parent":
        order: list[str] = []
        for h in hits:
            if h.chunk.parent_id not in order:
                order.append(h.chunk.parent_id)
        return await search.get_parents(order)

    # group hits by parent, keeping best-child order of parents
    grouped: dict[str, list[Chunk]] = {}
    for h in hits:
        grouped.setdefault(h.chunk.parent_id, []).append(h.chunk)

    if mode == "child":
        return [
            _unit_from_chunks(None, sorted(chunks, key=lambda c: c.position))
            for chunks in grouped.values()
        ]

    parents = {p.parent_id: p for p in await search.get_parents(list(grouped))}
    units: list[ParentChunk] = []
    for pid, chunks in grouped.items():
        parent = parents.get(pid)
        if parent is None:
            units.append(_unit_from_chunks(None, chunks))
            continue
        ids = parent.child_ids
        wanted: list[str] = []
        for c in chunks:
            i = ids.index(c.chunk_id) if c.chunk_id in ids else -1
            span = ids[max(0, i - window) : i + window + 1] if i >= 0 else [c.chunk_id]
            for cid in span:
                if cid not in wanted:
                    wanted.append(cid)
        wanted.sort(key=ids.index)
        fetched = await search.get_chunks(wanted)
        units.append(_unit_from_chunks(parent, fetched or chunks))
    return units
