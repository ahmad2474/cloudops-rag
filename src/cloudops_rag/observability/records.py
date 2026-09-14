"""Per-request observability record (spec §18) and a bounded in-memory ring for the UI.

A durable sink (CloudWatch / S3) is Phase 13; the record shape is fixed here so the log line and
the UI's cost panel read the same fields.
"""

from collections import deque
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict

from cloudops_rag.generation.models import AnswerResponse
from cloudops_rag.retrieval.models import TrailStep


class RequestRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str
    timestamp: str
    user: str
    roles: list[str]
    query: str
    strategy: str
    answer_status: str
    retrieval_count: int
    bm25_results: int
    vector_results: int
    fusion_results: int
    reranker_results: int
    final_sources: int
    citations: int
    conflicts: int
    evidence: str | None
    model: str | None
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    retrieval_latency_ms: float
    reranker_latency_ms: float
    generation_latency_ms: float
    total_latency_ms: float
    abstained: bool
    blocked: bool


def _count(trail: Iterable[TrailStep], stage: str) -> int:
    return next((s.count for s in trail if s.stage == stage), 0)


def _lat(trail: Iterable[TrailStep], stage: str) -> float:
    return round(sum(s.latency_ms for s in trail if s.stage == stage), 2)


def record_from_answer(
    request_id: str, user: str, roles: Sequence[str], strategy: str, res: AnswerResponse
) -> RequestRecord:
    usage = res.usage
    return RequestRecord(
        request_id=request_id,
        timestamp=datetime.now(UTC).isoformat(timespec="milliseconds"),
        user=user,
        roles=list(roles),
        query=res.query[:500],
        strategy=strategy,
        answer_status=res.status,
        retrieval_count=_count(res.trail, "select_top_k"),
        bm25_results=_count(res.trail, "bm25_search"),
        vector_results=_count(res.trail, "vector_search"),
        fusion_results=_count(res.trail, "fusion"),
        reranker_results=_count(res.trail, "rerank"),
        final_sources=len(res.sources),
        citations=len(res.citations),
        conflicts=len(res.conflicts),
        evidence=res.evidence.label if res.evidence else None,
        model=usage.model if usage else None,
        input_tokens=usage.input_tokens if usage else 0,
        output_tokens=usage.output_tokens if usage else 0,
        estimated_cost_usd=usage.estimated_cost_usd if usage else 0.0,
        retrieval_latency_ms=res.latency_ms.get("retrieval", 0.0),
        reranker_latency_ms=_lat(res.trail, "rerank"),
        generation_latency_ms=res.latency_ms.get("generation", 0.0),
        total_latency_ms=res.latency_ms.get("total", 0.0),
        abstained=res.status in ("abstained", "no_authorized_evidence"),
        blocked=res.status == "blocked",
    )


class RequestLedger:
    """Bounded ring of recent records plus running totals for the cost panel."""

    def __init__(self, capacity: int = 500) -> None:
        self._ring: deque[RequestRecord] = deque(maxlen=capacity)
        self.total_requests = 0
        self.total_cost_usd = 0.0
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    def add(self, rec: RequestRecord) -> None:
        self._ring.append(rec)
        self.total_requests += 1
        self.total_cost_usd = round(self.total_cost_usd + rec.estimated_cost_usd, 6)
        self.total_input_tokens += rec.input_tokens
        self.total_output_tokens += rec.output_tokens

    def recent(self, n: int = 50) -> list[RequestRecord]:
        return list(self._ring)[-n:][::-1]

    def summary(self) -> dict[str, float | int]:
        recs = list(self._ring)
        lat = sorted(r.total_latency_ms for r in recs)

        def p(q: float) -> float:
            return lat[min(len(lat) - 1, int(q * len(lat)))] if lat else 0.0

        answered = sum(1 for r in recs if r.answer_status == "answered")
        return {
            "requests": self.total_requests,
            "window": len(recs),
            "answered": answered,
            "abstained": sum(1 for r in recs if r.abstained),
            "blocked": sum(1 for r in recs if r.blocked),
            "avg_cost_usd": round(sum(r.estimated_cost_usd for r in recs) / len(recs), 6)
            if recs
            else 0.0,
            "total_cost_usd": self.total_cost_usd,
            "p50_latency_ms": p(0.5),
            "p95_latency_ms": p(0.95),
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
        }
