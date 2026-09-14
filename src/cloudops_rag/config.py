"""Explicit configuration. The only place environment variables are read."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ProviderName = Literal["stub", "bedrock"]
SearchProviderName = Literal["opensearch"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["local", "test", "aws"] = "local"
    log_level: str = "INFO"

    llm_provider: ProviderName = "stub"
    llm_model: str = "stub-model"
    embedding_provider: ProviderName = "stub"
    embedding_model: str = "stub-embed"
    embedding_dimensions: int = Field(default=256, ge=8, le=4096)
    reranker_provider: ProviderName = "stub"

    search_provider: SearchProviderName = "opensearch"
    opensearch_url: str = "http://localhost:9200"
    opensearch_index_prefix: str = "cloudops"

    aws_region: str = "us-east-1"

    @property
    def uses_aws(self) -> bool:
        """True if any provider would make an AWS call. Must be False through Phase 9."""
        return "bedrock" in {self.llm_provider, self.embedding_provider, self.reranker_provider}


def load_settings() -> Settings:
    return Settings()
