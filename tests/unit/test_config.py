import pytest

from cloudops_rag.config import Settings
from cloudops_rag.errors import ConfigurationError
from cloudops_rag.providers.registry import build_providers


def test_defaults_are_local_and_stub() -> None:
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.app_env == "local"
    assert s.llm_provider == "stub"
    assert s.uses_aws is False


def test_uses_aws_when_any_provider_is_bedrock() -> None:
    assert Settings(embedding_provider="bedrock").uses_aws is True


def test_bedrock_is_refused_until_implemented() -> None:
    """Phase 0-9 guard: nothing may reach AWS."""
    with pytest.raises(ConfigurationError, match="Bedrock"):
        build_providers(Settings(llm_provider="bedrock"), use_stub_search=True)


def test_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENSEARCH_INDEX_PREFIX", "test-prefix")
    monkeypatch.setenv("EMBEDDING_DIMENSIONS", "512")
    s = Settings()
    assert s.opensearch_index_prefix == "test-prefix"
    assert s.embedding_dimensions == 512
