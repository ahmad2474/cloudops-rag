"""Exception hierarchy. The API layer maps these to RFC 7807 problem responses."""


class CloudOpsRagError(Exception):
    """Base for all library errors."""

    status_code = 500
    title = "Internal error"


class ConfigurationError(CloudOpsRagError):
    """Invalid or inconsistent settings; raised at startup, never on first request."""

    title = "Configuration error"


class ProviderError(CloudOpsRagError):
    """An external provider (search, embedding, LLM, reranker) failed."""

    status_code = 502
    title = "Upstream provider error"

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class ProviderNotConfiguredError(ProviderError):
    """A provider name was requested that has no implementation registered."""

    status_code = 500
    title = "Provider not configured"


class ProviderTimeoutError(ProviderError):
    """A provider call exceeded its deadline."""

    status_code = 504
    title = "Upstream timeout"

    def __init__(self, message: str) -> None:
        super().__init__(message, retryable=True)


class RateLimitedError(CloudOpsRagError):
    status_code = 429
    title = "Too many requests"

    def __init__(self, retry_after: float) -> None:
        super().__init__(f"rate limited; retry after {retry_after:.1f}s")
        self.retry_after = retry_after
