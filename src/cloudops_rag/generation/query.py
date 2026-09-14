"""Query understanding (spec §2, §46): rewrite, structured hints, optional decomposition.

Rule-based by default — deterministic and free. LLM decomposition is opt-in because it costs a
model call per question and only helps multi-part questions.
"""

import json
import re

from pydantic import BaseModel, ConfigDict, Field

from cloudops_rag.providers.base import LLMProvider

_INJECTION_PREFIX = re.compile(
    r"^\s*(ignore|disregard|forget)\b[^.?!]*?(instructions|prompt|rules)[^.?!]*[.?!]?\s*(also,?\s*)?",
    re.I,
)
_VERSION = re.compile(
    r"\b(?:eks|kubernetes|k8s|terraform|postgres(?:ql)?)?\s*v?(1\.\d{1,2})\b", re.I
)
_INCIDENT = re.compile(r"\bINC-\d{4}\b", re.I)
_WS = re.compile(r"\s+")
_DOC_TYPE_HINTS: dict[str, tuple[str, ...]] = {
    "incident": ("which incident", "what incident", "incident involved", "when did", "inc-"),
    "postmortem": ("postmortem", "post-mortem", "root cause of inc", "what did we learn"),
    "policy": ("policy", "allowed to", "am i allowed", "is it permitted", "approved"),
    "runbook": ("runbook", "procedure", "how do i fix", "steps to"),
}


class QueryPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    original: str
    query: str = Field(description="cleaned query used for retrieval")
    subqueries: list[str] = Field(default_factory=list, description="empty unless decomposed")
    version_hint: str | None = None
    incident_ids: list[str] = Field(default_factory=list)
    document_type_hint: str | None = None
    stripped_injection: bool = False


def plan_query(question: str) -> QueryPlan:
    cleaned = _INJECTION_PREFIX.sub("", question)
    stripped = cleaned != question
    cleaned = _WS.sub(" ", cleaned).strip() or question.strip()

    v = _VERSION.search(cleaned)
    incidents = sorted({m.upper() for m in _INCIDENT.findall(cleaned)})
    lower = cleaned.lower()
    dtype = next(
        (t for t, hints in _DOC_TYPE_HINTS.items() if any(h in lower for h in hints)), None
    )
    return QueryPlan(
        original=question,
        query=cleaned,
        version_hint=v.group(1) if v else None,
        incident_ids=incidents,
        document_type_hint=dtype,
        stripped_injection=stripped,
    )


_DECOMPOSE_SYSTEM = """You split an operations question into independent search queries.
Reply with JSON only: {"subqueries": ["...", "..."]}. Use 2-4 short, specific queries when the
question asks about several distinct things; otherwise reply {"subqueries": []}. Never answer
the question."""


async def decompose(plan: QueryPlan, llm: LLMProvider) -> QueryPlan:
    res = await llm.generate(_DECOMPOSE_SYSTEM, plan.query, max_tokens=200)
    m = re.search(r"\{.*\}", res.text, re.S)
    if not m:
        return plan
    try:
        subs = json.loads(m.group(0)).get("subqueries", [])
    except (ValueError, AttributeError):
        return plan
    subs = [s.strip() for s in subs if isinstance(s, str) and len(s.strip()) > 3][:4]
    return plan.model_copy(update={"subqueries": subs if len(subs) >= 2 else []})
