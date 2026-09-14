"""Retrieval: query → authorized candidate chunks → parents. Baseline = vector only (Phase 2)."""

from cloudops_rag.retrieval.models import RetrievalResult, TrailStep
from cloudops_rag.retrieval.vector import VectorRetriever

__all__ = ["RetrievalResult", "TrailStep", "VectorRetriever"]
