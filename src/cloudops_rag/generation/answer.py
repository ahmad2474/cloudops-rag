"""AnswerService: retrieve → build context → generate → validate citations → abstain if needed."""

import time

from cloudops_rag.generation.citations import to_citation, validate_citations
from cloudops_rag.generation.context import build_context
from cloudops_rag.generation.models import AnswerResponse, Usage
from cloudops_rag.generation.prompts import ABSTAIN_TOKEN, SYSTEM_PROMPT, build_user_prompt
from cloudops_rag.logging import get_logger
from cloudops_rag.observability.pricing import estimate_cost_usd
from cloudops_rag.providers.base import LLMProvider, SearchFilters
from cloudops_rag.retrieval.vector import VectorRetriever

log = get_logger(__name__)

NO_EVIDENCE_ANSWER = (
    "I couldn't find sufficient evidence in the authorized knowledge base to answer this reliably."
)


class AnswerService:
    def __init__(
        self,
        retriever: VectorRetriever,
        llm: LLMProvider,
        *,
        context_token_budget: int = 6000,
        max_tokens: int = 1024,
    ) -> None:
        self._retriever = retriever
        self._llm = llm
        self._budget = context_token_budget
        self._max_tokens = max_tokens

    async def ask(self, question: str, filters: SearchFilters) -> AnswerResponse:
        t_start = time.perf_counter()
        retrieval = await self._retriever.retrieve(question, filters)
        t_retrieved = time.perf_counter()

        sources = build_context(retrieval.parents, self._budget)
        offered = [to_citation(s) for s in sources]
        base = {
            "query": question,
            "sources": offered,
            "trail": retrieval.trail,
        }
        if not sources:
            log.info("answer", status="no_authorized_evidence", roles=filters.roles)
            return AnswerResponse(
                **base,
                status="no_authorized_evidence",
                answer=NO_EVIDENCE_ANSWER,
                citations=[],
                usage=None,
                latency_ms=_lat(t_start, t_retrieved, None),
            )

        result = await self._llm.generate(
            SYSTEM_PROMPT, build_user_prompt(question, sources), max_tokens=self._max_tokens
        )
        t_generated = time.perf_counter()
        usage = Usage(
            model=result.model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            estimated_cost_usd=estimate_cost_usd(
                result.model, result.input_tokens, result.output_tokens
            ),
        )
        raw = result.text.strip()
        if not raw or ABSTAIN_TOKEN in raw[:64]:
            log.info("answer", status="abstained", roles=filters.roles)
            return AnswerResponse(
                **base,
                status="abstained",
                answer=NO_EVIDENCE_ANSWER,
                citations=[],
                usage=usage,
                latency_ms=_lat(t_start, t_retrieved, t_generated),
            )

        cleaned, citations, dropped = validate_citations(raw, sources)
        if not citations:
            # An uncited answer is ungrounded by definition; treat as abstention rather than
            # return unverifiable text.
            log.info("answer", status="abstained", reason="no_valid_citations", dropped=dropped)
            return AnswerResponse(
                **base,
                status="abstained",
                answer=NO_EVIDENCE_ANSWER,
                citations=[],
                dropped_citations=dropped,
                usage=usage,
                latency_ms=_lat(t_start, t_retrieved, t_generated),
            )
        log.info(
            "answer",
            status="answered",
            citations=len(citations),
            dropped=len(dropped),
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cost_usd=usage.estimated_cost_usd,
        )
        return AnswerResponse(
            **base,
            status="answered",
            answer=cleaned,
            citations=citations,
            dropped_citations=dropped,
            usage=usage,
            latency_ms=_lat(t_start, t_retrieved, t_generated),
        )


def _lat(t0: float, t1: float, t2: float | None) -> dict[str, float]:
    out = {"retrieval": round((t1 - t0) * 1000, 2)}
    if t2 is not None:
        out["generation"] = round((t2 - t1) * 1000, 2)
    out["total"] = round(((t2 or t1) - t0) * 1000, 2)
    return out
