"""Builds concrete providers from Settings. The single place provider names are interpreted."""

from dataclasses import dataclass

from cloudops_rag.config import Settings
from cloudops_rag.errors import ProviderNotConfiguredError
from cloudops_rag.providers.base import (
    EmbeddingProvider,
    LLMProvider,
    RerankerProvider,
    SearchProvider,
)
from cloudops_rag.providers.bedrock import (
    BedrockEmbeddingProvider,
    BedrockLLMProvider,
    BedrockRerankerProvider,
)
from cloudops_rag.providers.nvidia import NvidiaLLMProvider
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
    """Instantiate providers. Raises at startup on anything unsupported — never lazily.

    Bedrock providers additionally raise unless ``settings.allow_aws_calls`` is true.
    """
    search: SearchProvider = (
        StubSearchProvider()
        if use_stub_search
        else OpenSearchProvider(
            settings.opensearch_url,
            settings.opensearch_index_prefix,
            auth=settings.opensearch_auth,
            region=settings.aws_region,
        )
    )
    return Providers(
        embedding=_build_embedding(settings),
        llm=_build_llm(settings),
        reranker=_build_reranker(settings),
        search=search,
    )


def _build_embedding(settings: Settings) -> EmbeddingProvider:
    if settings.embedding_provider == "stub":
        return StubEmbeddingProvider(dimensions=settings.embedding_dimensions)
    if settings.embedding_provider == "bedrock":
        return BedrockEmbeddingProvider(
            model=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
            region=settings.aws_region,
            allow_aws_calls=settings.allow_aws_calls,
        )
    raise ProviderNotConfiguredError(f"embedding provider: {settings.embedding_provider}")


def _build_llm(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "stub":
        return StubLLMProvider(model=settings.llm_model)
    if settings.llm_provider == "bedrock":
        return BedrockLLMProvider(
            model=settings.llm_model,
            region=settings.aws_region,
            allow_aws_calls=settings.allow_aws_calls,
        )
    if settings.llm_provider == "nvidia":
        key = settings.nvidia_api_key
        return NvidiaLLMProvider(
            model=settings.llm_model,
            api_key=key.get_secret_value() if key else None,
            base_url=settings.nvidia_base_url,
            allow_nvidia_calls=settings.allow_nvidia_calls,
            timeout_s=settings.timeout_llm_s,
            max_concurrency=settings.nvidia_max_concurrency,
        )
    raise ProviderNotConfiguredError(f"llm provider: {settings.llm_provider}")


def _build_reranker(settings: Settings) -> RerankerProvider:
    if settings.reranker_provider == "stub":
        return StubRerankerProvider()
    if settings.reranker_provider == "bedrock":
        return BedrockRerankerProvider(
            model=settings.reranker_model,
            region=settings.aws_region,
            allow_aws_calls=settings.allow_aws_calls,
        )
    raise ProviderNotConfiguredError(f"reranker provider: {settings.reranker_provider}")
