"""Explicit configuration. The only place environment variables are read."""

from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ProviderName = Literal["stub", "bedrock"]
SearchProviderName = Literal["opensearch"]
RetrievalStrategy = Literal["vector", "bm25", "hybrid_rrf", "hybrid_weighted"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["local", "test", "aws"] = "local"
    log_level: str = "INFO"

    # --- providers -------------------------------------------------------------------------
    llm_provider: ProviderName = "stub"
    llm_model: str = "amazon.nova-lite-v1:0"
    llm_max_tokens: int = Field(default=1024, ge=64, le=8192)
    embedding_provider: ProviderName = "stub"
    embedding_model: str = "amazon.titan-embed-text-v2:0"
    embedding_dimensions: int = 1024  # Titan V2 supports 256 / 512 / 1024
    reranker_provider: ProviderName = "stub"
    reranker_model: str = "cohere.rerank-v3-5:0"

    # --- AWS -------------------------------------------------------------------------------
    aws_region: str = "us-east-1"
    # Hard guard: Bedrock providers refuse to run unless this is explicitly true (cost control).
    allow_aws_calls: bool = False

    # --- search ----------------------------------------------------------------------------
    search_provider: SearchProviderName = "opensearch"
    opensearch_url: str = "http://localhost:9200"
    opensearch_index_prefix: str = "cloudops"

    # --- retrieval / generation knobs (baseline; tuned in later phases) --------------------
    retrieval_strategy: RetrievalStrategy = "vector"
    retrieval_candidates: int = Field(default=50, ge=1, le=500)
    retrieval_top_k: int = Field(default=8, ge=1, le=50)
    fusion_rrf_k: int = Field(default=60, ge=1, le=1000)
    fusion_vector_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    rerank_enabled: bool = False
    rerank_candidates: int = Field(default=20, ge=1, le=100)
    context_token_budget: int = Field(default=6000, ge=500, le=64000)
    chunk_target_tokens: int = Field(default=400, ge=100, le=2000)

    @field_validator("embedding_dimensions")
    @classmethod
    def _titan_dimensions(cls, v: int) -> int:
        if v not in (256, 512, 1024):
            raise ValueError("embedding_dimensions must be 256, 512 or 1024 (Titan V2)")
        return v

    @property
    def uses_aws(self) -> bool:
        return "bedrock" in {self.llm_provider, self.embedding_provider, self.reranker_provider}


def load_settings() -> Settings:
    return Settings()
