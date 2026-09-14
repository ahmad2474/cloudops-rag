"""Evidence strength (spec §28): derived from retrieval and citation signals, never a model's
self-reported confidence."""

import re

from cloudops_rag.generation.models import Citation, EvidenceStrength
from cloudops_rag.retrieval.models import RetrievalResult

_CITE = re.compile(r"\[S\d+\]")


def evidence_strength(
    retrieval: RetrievalResult, answer: str, citations: list[Citation]
) -> EvidenceStrength:
    if not citations or not answer.strip():
        return EvidenceStrength(score=0.0, label="none", signals={})
    paragraphs = [p for p in answer.split("\n\n") if p.strip()]
    cited_paras = sum(1 for p in paragraphs if _CITE.search(p))
    coverage = cited_paras / len(paragraphs) if paragraphs else 0.0
    distinct_docs = len({c.document_id for c in citations})
    doc_signal = min(distinct_docs, 3) / 3
    top_scores = [h.score for h in retrieval.hits[:2]]
    # Rerank scores are 0..1 relevance; cosine/RRF scores are not comparable across strategies,
    # so only use the *margin* between rank 1 and 2 as a weak agreement signal.
    margin = 0.0
    if len(top_scores) == 2 and top_scores[0] > 0:
        margin = max(0.0, min(1.0, (top_scores[0] - top_scores[1]) / top_scores[0]))
    score = round(0.5 * coverage + 0.35 * doc_signal + 0.15 * (1 - margin), 3)
    label = "high" if score >= 0.75 else "medium" if score >= 0.45 else "low"
    return EvidenceStrength(
        score=score,
        label=label,
        signals={
            "citation_coverage": round(coverage, 3),
            "distinct_documents": float(distinct_docs),
            "top_margin": round(margin, 3),
        },
    )
