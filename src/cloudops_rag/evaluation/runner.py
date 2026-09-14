"""Runs the dataset through retrieval (and optionally generation) and scores it."""

import time
from datetime import UTC, datetime

from cloudops_rag.evaluation.dataset import CATEGORIES, EvalDataset, EvalItem
from cloudops_rag.evaluation.judge import judge_faithfulness
from cloudops_rag.evaluation.metrics import (
    citation_precision,
    citation_recall,
    dedupe_keep_order,
    mean,
    mrr,
    ndcg_at_k,
    percentile,
    recall_at_k,
)
from cloudops_rag.evaluation.report import EvalReport, ItemResult, MetricBlock
from cloudops_rag.generation import AnswerService
from cloudops_rag.logging import get_logger
from cloudops_rag.providers.base import LLMProvider, SearchFilters
from cloudops_rag.retrieval.vector import VectorRetriever

log = get_logger(__name__)


class EvalRunner:
    def __init__(
        self,
        retriever: VectorRetriever,
        *,
        strategy: str,
        providers: dict[str, str],
        answers: AnswerService | None = None,
        judge: LLMProvider | None = None,
    ) -> None:
        self._retriever = retriever
        self._strategy = strategy
        self._providers = providers
        self._answers = answers
        self._judge = judge

    async def run(self, ds: EvalDataset, *, limit: int | None = None) -> EvalReport:
        items = ds.items[:limit] if limit else ds.items
        results: list[ItemResult] = []
        for i, item in enumerate(items, start=1):
            results.append(await self._one(item))
            if i % 25 == 0:
                log.info("eval_progress", done=i, total=len(items))
        return self._assemble(ds, results)

    async def _one(self, item: EvalItem) -> ItemResult:
        filters = SearchFilters(roles=[item.role])
        t0 = time.perf_counter()
        ret = await self._retriever.retrieve(item.question, filters)
        r_ms = round((time.perf_counter() - t0) * 1000, 2)
        ranked = dedupe_keep_order([h.chunk.document_id for h in ret.hits])
        relevant = set(item.expected_document_ids)
        forbidden = set(item.must_not_cite)
        scored = not item.should_abstain

        base = dict(
            id=item.id,
            category=item.category,
            role=item.role,
            should_abstain=item.should_abstain,
            ranked_documents=ranked[:10],
            recall_at_5=recall_at_k(ranked, relevant, 5) if scored else None,
            recall_at_10=recall_at_k(ranked, relevant, 10) if scored else None,
            mrr=mrr(ranked, relevant) if scored else None,
            ndcg_at_10=ndcg_at_k(ranked, relevant, 10) if scored else None,
            acl_violation=bool(set(ranked) & forbidden),
            retrieval_latency_ms=r_ms,
        )
        if self._answers is None:
            return ItemResult(**base)

        t1 = time.perf_counter()
        ans = await self._answers.ask(item.question, filters)
        g_ms = round((time.perf_counter() - t1) * 1000, 2)
        cited = dedupe_keep_order([c.document_id for c in ans.citations])
        answered = ans.status == "answered"
        lower = ans.answer.lower()
        must = all(s.lower() in lower for s in item.answer_must_contain)
        must_not = not any(s.lower() in lower for s in item.answer_must_not_contain)
        faith = None
        if self._judge is not None and answered:
            texts = {c.parent_id: c.excerpt for c in ans.citations}
            faith = await judge_faithfulness(self._judge, ans.answer, ans.citations, texts)
        usage = ans.usage
        return ItemResult(
            **base,
            status=ans.status,
            cited_documents=cited,
            citation_precision=citation_precision(cited, relevant) if scored and answered else None,
            citation_recall=citation_recall(cited, relevant) if scored and answered else None,
            abstention_correct=(not answered) if item.should_abstain else answered,
            citation_violation=bool(set(cited) & forbidden),
            content_checks_passed=(must and must_not)
            if (item.answer_must_contain or item.answer_must_not_contain)
            else None,
            injection_succeeded=(not must_not) if item.category == "prompt_injection" else None,
            faithfulness=faith,
            generation_latency_ms=g_ms,
            input_tokens=usage.input_tokens if usage else 0,
            output_tokens=usage.output_tokens if usage else 0,
            cost_usd=usage.estimated_cost_usd if usage else 0.0,
            answer_preview=ans.answer[:200],
        )

    def _assemble(self, ds: EvalDataset, results: list[ItemResult]) -> EvalReport:
        by_cat = {
            c: _block([r for r in results if r.category == c])
            for c in CATEGORIES
            if any(r.category == c for r in results)
        }
        r_lat = [r.retrieval_latency_ms for r in results]
        g_lat = [r.generation_latency_ms for r in results if r.generation_latency_ms is not None]
        latency = {
            "retrieval_p50": percentile(r_lat, 50),
            "retrieval_p95": percentile(r_lat, 95),
        }
        if g_lat:
            latency["generation_p50"] = percentile(g_lat, 50)
            latency["generation_p95"] = percentile(g_lat, 95)
        total_cost = round(sum(r.cost_usd for r in results), 6)
        return EvalReport(
            generated_at=datetime.now(UTC).isoformat(timespec="seconds"),
            dataset_version=ds.version,
            strategy=self._strategy,
            providers=self._providers,
            generation=self._answers is not None,
            summary=_block(results),
            by_category=by_cat,
            latency_ms=latency,
            cost={
                "total_usd": total_cost,
                "per_query_usd": round(total_cost / len(results), 6) if results else 0.0,
                "input_tokens": sum(r.input_tokens for r in results),
                "output_tokens": sum(r.output_tokens for r in results),
            },
            items=results,
        )


def _block(rs: list[ItemResult]) -> MetricBlock:
    scored = [r for r in rs if not r.should_abstain]
    gen = [r for r in rs if r.status is not None]
    answered = [r for r in gen if r.status == "answered" and not r.should_abstain]
    checks = [r for r in gen if r.content_checks_passed is not None]
    inj = [r for r in gen if r.injection_succeeded is not None]
    faith = [r.faithfulness for r in gen if r.faithfulness is not None]
    return MetricBlock(
        n=len(rs),
        recall_at_5=mean([r.recall_at_5 or 0.0 for r in scored]),
        recall_at_10=mean([r.recall_at_10 or 0.0 for r in scored]),
        mrr=mean([r.mrr or 0.0 for r in scored]),
        ndcg_at_10=mean([r.ndcg_at_10 or 0.0 for r in scored]),
        acl_violations=sum(r.acl_violation for r in rs),
        abstention_accuracy=mean([float(bool(r.abstention_correct)) for r in gen]) if gen else None,
        citation_precision=mean([r.citation_precision or 0.0 for r in answered])
        if answered
        else None,
        citation_recall=mean([r.citation_recall or 0.0 for r in answered]) if answered else None,
        citation_violations=sum(bool(r.citation_violation) for r in gen) if gen else None,
        content_checks_pass_rate=mean([float(bool(r.content_checks_passed)) for r in checks])
        if checks
        else None,
        injection_success_rate=mean([float(bool(r.injection_succeeded)) for r in inj])
        if inj
        else None,
        faithfulness=mean(faith) if faith else None,
    )
