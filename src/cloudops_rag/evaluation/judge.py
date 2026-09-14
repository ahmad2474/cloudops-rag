"""LLM-as-judge faithfulness: fraction of answer claims supported by the cited sources."""

import json
import re

from cloudops_rag.generation.models import Citation
from cloudops_rag.providers.base import LLMProvider

JUDGE_SYSTEM = """You are a strict grader. You receive an ANSWER and the SOURCES it cites.
Split the ANSWER into atomic factual claims. For each claim decide whether it is directly
supported by the SOURCES (not by your own knowledge). Reply with JSON only:
{"claims": <int>, "supported": <int>, "unsupported_examples": ["..."]}"""


async def judge_faithfulness(
    llm: LLMProvider, answer: str, citations: list[Citation], source_texts: dict[str, str]
) -> float | None:
    if not answer.strip() or not citations:
        return None
    blocks = []
    for c in citations:
        txt = source_texts.get(c.parent_id, c.excerpt)
        blocks.append(f"[{c.sid}] {c.title} — {c.section}\n{txt}")
    user = "SOURCES:\n\n" + "\n\n".join(blocks) + f"\n\nANSWER:\n{answer}\n\nJSON:"
    res = await llm.generate(JUDGE_SYSTEM, user, max_tokens=400)
    m = re.search(r"\{.*\}", res.text, re.S)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
        claims = int(data.get("claims", 0))
        supported = int(data.get("supported", 0))
    except (ValueError, TypeError):
        return None
    if claims <= 0:
        return None
    return round(min(supported, claims) / claims, 4)
