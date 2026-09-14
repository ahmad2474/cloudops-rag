"""Explicit configuration. The only place environment variables are read."""

from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ProviderName = Literal["stub", "bedrock"]
SearchProviderName = Literal["opensearch"]
RetrievalStrategy = Literal["vector", "bm25", "hybrid_rrf", "hybrid_weighted"]
ContextMode = Literal["parent", "child", "child_window"]
QueryUnderstanding = Literal["rules", "llm"]


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

    # --- production API (Phase 8) ----------------------------------------------------------
    timeout_embed_s: float = Field(default=10.0, gt=0)
    timeout_search_s: float = Field(default=10.0, gt=0)
    timeout_rerank_s: float = Field(default=15.0, gt=0)
    timeout_llm_s: float = Field(default=60.0, gt=0)
    provider_retries: int = Field(default=3, ge=1, le=6)
    rate_limit_rpm: int = Field(default=60, ge=1, le=10000)
    max_request_bytes: int = Field(default=16_384, ge=1024)
    request_ledger_size: int = Field(default=500, ge=10, le=10000)
    cors_origins: str = "http://localhost:3000"

    # --- auth -----------------------------------------------------------------------------
    # HS256 signing secret (>= 32 chars). Local default is deliberately obvious; override in prod.
    auth_secret: str = "local-dev-secret-change-me-please-32chars!!"
    auth_token_ttl_seconds: int = Field(default=3600, ge=60, le=86400)
    # JSON: {"alice": {"password_hash": "$2b$...", "roles": ["developer"]}}. Empty = no login.
    auth_users: str = ""
    # Accept the dev-only X-Acme-Role header instead of a token. Forced off when app_env=aws.
    auth_allow_role_header: bool = True

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
    context_mode: ContextMode = "parent"
    context_window: int = Field(default=1, ge=0, le=5, description="siblings each side")
    query_understanding: QueryUnderstanding = "rules"
    chunk_target_tokens: int = Field(default=400, ge=100, le=2000)

    @field_validator("embedding_dimensions")
    @classmethod
    def _titan_dimensions(cls, v: int) -> int:
        if v not in (256, 512, 1024):
            raise ValueError("embedding_dimensions must be 256, 512 or 1024 (Titan V2)")
        return v

    @property
    def role_header_enabled(self) -> bool:
        """The dev-only identity header is honoured only for local runs and tests."""
        return self.app_env in ("local", "test") and self.auth_allow_role_header

    def validate_for_environment(self) -> list[str]:
        """Misconfigurations that must fail startup outside local (spec: fail loudly, early)."""
        problems: list[str] = []
        if self.app_env == "aws":
            if self.auth_secret.startswith("local-dev-secret"):
                problems.append("AUTH_SECRET is the dev default")
            if not self.auth_users:
                problems.append("AUTH_USERS is empty — nobody could log in")
        if len(self.auth_secret) < 32:
            problems.append("AUTH_SECRET must be at least 32 characters")
        return problems

    @property
    def uses_aws(self) -> bool:
        return "bedrock" in {self.llm_provider, self.embedding_provider, self.reranker_provider}


def load_settings() -> Settings:
    return Settings()
