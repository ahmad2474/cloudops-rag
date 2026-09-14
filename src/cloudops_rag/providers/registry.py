"""Builds concrete providers from Settings. The single place provider names are interpreted."""

from dataclasses import dataclass

from cloudops_rag.config import Settings
from cloudops_rag.errors import ConfigurationError, ProviderNotConfiguredError
from cloudops_rag.providers.base import (
    EmbeddingProvider,
    LLMProvider,
    RerankerProvider,
    SearchProvider,
)
from cloudops_rag.providers.opensearch import OpenSearchProvider
from cloudops_rag.providers.stub import (
    StubEmbeddingProvider,
    StubLLMProvider,
    StubRerankerProvider,
    StubSearchProvider,
)


@dataclass(frozen=True)
class Providers:
    embedding: EmbeddingProvider
    llm: LLMProvider
    reranker: RerankerProvider
    search: SearchProvider


def build_providers(settings: Settings, *, use_stub_search: bool = False) -> Providers:
    """Instantiate providers. Raises at startup on anything unsupported — never lazily."""
    if settings.uses_aws:
        # Phase 0-9 guard. Bedrock implementations land in Phase 2 behind explicit approval.
        raise ConfigurationError(
            "Bedrock providers are not implemented yet; set *_PROVIDER=stub for local development."
        )

    embedding = _build_embedding(settings)
    llm = _build_llm(settings)
    reranker = _build_reranker(settings)
    search: SearchProvider = (
        StubSearchProvider()
        if use_stub_search
        else OpenSearchProvider(settings.opensearch_url, settings.opensearch_index_prefix)
    )
    return Providers(embedding=embedding, llm=llm, reranker=reranker, search=search)


def _build_embedding(settings: Settings) -> EmbeddingProvider:
    if settings.embedding_provider == "stub":
        return StubEmbeddingProvider(dimensions=settings.embedding_dimensions)
    raise ProviderNotConfiguredError(f"embedding provider: {settings.embedding_provider}")


def _build_llm(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "stub":
        return StubLLMProvider(model=settings.llm_model)
    raise ProviderNotConfiguredError(f"llm provider: {settings.llm_provider}")


def _build_reranker(settings: Settings) -> RerankerProvider:
    if settings.reranker_provider == "stub":
        return StubRerankerProvider()
    raise ProviderNotConfiguredError(f"reranker provider: {settings.reranker_provider}")
