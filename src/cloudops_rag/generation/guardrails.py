"""Output-side guardrails (spec §2 guardrail layer). Cheap, deterministic, run on every answer.

The retrieval-time ACL and the citation validator are the structural defences; this is the last
line: if a model was talked into echoing its instructions, the response never leaves the service.
"""

import re

from pydantic import BaseModel, ConfigDict

_WINDOW = 48


class GuardVerdict(BaseModel):
    model_config = ConfigDict(frozen=True)

    blocked: bool
    reasons: list[str]


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def detect_system_prompt_leak(answer: str, system_prompt: str) -> bool:
    """True if any 48-char window of the system prompt appears verbatim in the answer."""
    a, s = _norm(answer), _norm(system_prompt)
    if len(s) < _WINDOW or not a:
        return False
    step = _WINDOW // 2
    return any(s[i : i + _WINDOW] in a for i in range(0, len(s) - _WINDOW + 1, step))


_OVERRIDE_MARKERS = (
    "access granted",
    "override accepted",
    "maintenance mode",
    "ignoring previous instructions",
    "as instructed by the document",
)


def check_answer(answer: str, system_prompt: str) -> GuardVerdict:
    reasons: list[str] = []
    if detect_system_prompt_leak(answer, system_prompt):
        reasons.append("system_prompt_leak")
    low = answer.lower()
    if any(m in low for m in _OVERRIDE_MARKERS):
        reasons.append("override_marker")
    return GuardVerdict(blocked=bool(reasons), reasons=reasons)
