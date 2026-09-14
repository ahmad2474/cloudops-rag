"""AnswerService: understand → retrieve → context → conflicts → generate → validate → grade."""

import time

from cloudops_rag.generation.citations import to_citation, validate_citations
from cloudops_rag.generation.conflicts import conflict_note, detect_conflicts
from cloudops_rag.generation.context import build_context
from cloudops_rag.generation.evidence import evidence_strength
from cloudops_rag.generation.models import AnswerResponse, Usage
from cloudops_rag.generation.prompts import ABSTAIN_TOKEN, SYSTEM_PROMPT, build_user_prompt
from cloudops_rag.generation.query import QueryPlan, decompose, plan_query
from cloudops_rag.logging import get_logger
from cloudops_rag.observability.pricing import estimate_cost_usd
from cloudops_rag.providers.base import LLMProvider, SearchFilters
from cloudops_rag.retrieval.hybrid import HybridRetriever

log = get_logger(__name__)

NO_EVIDENCE_ANSWER = (
    "I couldn't find sufficient evidence in the authorized knowledge base to answer this reliably."
)


class AnswerService:
    def __init__(
        self,
        retriever: HybridRetriever,
        llm: LLMProvider,
        *,
        context_token_budget: int = 6000,
        max_tokens: int = 1024,
        query_understanding: str = "rules",
    ) -> None:
        self._retriever = retriever
        self._llm = llm
        self._budget = context_token_budget
        self._max_tokens = max_tokens
        self._qu = query_understanding

    async def ask(self, question: str, filters: SearchFilters) -> AnswerResponse:
        t_start = time.perf_counter()
        plan = await self._plan(question)
        queries = plan.subqueries or [plan.query]
        retrieval = await self._retriever.retrieve_many(queries, filters)
        t_retrieved = time.perf_counter()

        sources = build_context(retrieval.parents, self._budget)
        conflicts = detect_conflicts(sources)
        offered = [to_citation(s) for s in sources]
        base = {
            "query": question,
            "sources": offered,
            "trail": retrieval.trail,
            "conflicts": conflicts,
            "query_plan": plan.model_dump(mode="json"),
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

        user_prompt = build_user_prompt(
            plan.query,
            sources,
            notes=conflict_note(conflicts),
            version_hint=plan.version_hint,
        )
        result = await self._llm.generate(SYSTEM_PROMPT, user_prompt, max_tokens=self._max_tokens)
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
        evidence = evidence_strength(retrieval, cleaned, citations)
        log.info(
            "answer",
            status="answered",
            citations=len(citations),
            dropped=len(dropped),
            conflicts=len(conflicts),
            evidence=evidence.label,
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
            evidence=evidence,
            usage=usage,
            latency_ms=_lat(t_start, t_retrieved, t_generated),
        )

    async def _plan(self, question: str) -> QueryPlan:
        plan = plan_query(question)
        if self._qu == "llm":
            plan = await decompose(plan, self._llm)
        return plan


def _lat(t0: float, t1: float, t2: float | None) -> dict[str, float]:
    out = {"retrieval": round((t1 - t0) * 1000, 2)}
    if t2 is not None:
        out["generation"] = round((t2 - t1) * 1000, 2)
    out["total"] = round(((t2 or t1) - t0) * 1000, 2)
    return out
