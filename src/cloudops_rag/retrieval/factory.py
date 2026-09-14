"""Build a HybridRetriever from Settings, with optional per-call overrides."""

from cloudops_rag.config import Settings
from cloudops_rag.providers.registry import Providers
from cloudops_rag.retrieval.hybrid import HybridRetriever, Strategy


def make_retriever(
    providers: Providers,
    settings: Settings,
    *,
    strategy: Strategy | None = None,
    rerank: bool | None = None,
    top_k: int | None = None,
    candidates: int | None = None,
) -> HybridRetriever:
    use_rerank = settings.rerank_enabled if rerank is None else rerank
    return HybridRetriever(
        providers.embedding,
        providers.search,
        strategy=strategy or settings.retrieval_strategy,
        candidates=candidates or settings.retrieval_candidates,
        top_k=top_k or settings.retrieval_top_k,
        reranker=providers.reranker if use_rerank else None,
        rerank_candidates=settings.rerank_candidates,
        rrf_k=settings.fusion_rrf_k,
        vector_weight=settings.fusion_vector_weight,
    )
