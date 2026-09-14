"""Split Markdown into typed blocks. Code fences and tables are atomic."""

import re
from dataclasses import dataclass
from typing import Literal

BlockKind = Literal["heading", "code", "table", "list", "paragraph"]
_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_LIST_ITEM = re.compile(r"^\s*([-*+]|\d+[.)])\s+")


@dataclass(frozen=True)
class Block:
    kind: BlockKind
    text: str
    level: int = 0  # headings only


def split_blocks(markdown: str) -> list[Block]:
    lines = markdown.split("\n")
    blocks: list[Block] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith("```") or line.startswith("~~~"):
            fence = line[:3]
            j = i + 1
            while j < n and not lines[j].startswith(fence):
                j += 1
            blocks.append(Block("code", "\n".join(lines[i : min(j + 1, n)])))
            i = j + 1
            continue
        m = _HEADING.match(line)
        if m:
            blocks.append(Block("heading", m.group(2).strip(), level=len(m.group(1))))
            i += 1
            continue
        if line.lstrip().startswith("|"):
            j = i
            while j < n and lines[j].lstrip().startswith("|"):
                j += 1
            blocks.append(Block("table", "\n".join(lines[i:j])))
            i = j
            continue
        if _LIST_ITEM.match(line):
            j = i
            while (
                j < n
                and lines[j].strip()
                and (_LIST_ITEM.match(lines[j]) or lines[j].startswith((" ", "\t")))
            ):
                j += 1
            blocks.append(Block("list", "\n".join(lines[i:j])))
            i = j
            continue
        j = i
        while j < n and lines[j].strip() and not lines[j].startswith(("```", "~~~", "#", "|")):
            j += 1
        if j == i:
            j = i + 1
        blocks.append(Block("paragraph", "\n".join(lines[i:j])))
        i = j
    return blocks
