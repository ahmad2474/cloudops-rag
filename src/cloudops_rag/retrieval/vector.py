"""Baseline dense retrieval — a HybridRetriever pinned to strategy="vector"."""

from cloudops_rag.providers.base import EmbeddingProvider, SearchProvider
from cloudops_rag.retrieval.hybrid import HybridRetriever


class VectorRetriever(HybridRetriever):
    def __init__(
        self,
        embedding: EmbeddingProvider,
        search: SearchProvider,
        *,
        candidates: int = 50,
        top_k: int = 8,
    ) -> None:
        super().__init__(embedding, search, strategy="vector", candidates=candidates, top_k=top_k)
