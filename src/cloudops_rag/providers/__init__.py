"""Provider interfaces. Application code depends on these Protocols, never on SDKs.

Phase 0 ships only the ``stub`` implementations. Bedrock/OpenSearch implementations arrive in
Phase 2 and are selected by name through :func:`cloudops_rag.providers.registry.build_providers`.
"""

from cloudops_rag.providers.base import (
    EmbeddingProvider,
    LLMProvider,
    RerankedItem,
    RerankerProvider,
    SearchHit,
    SearchProvider,
)

__all__ = [
    "EmbeddingProvider",
    "LLMProvider",
    "RerankedItem",
    "RerankerProvider",
    "SearchHit",
    "SearchProvider",
]
