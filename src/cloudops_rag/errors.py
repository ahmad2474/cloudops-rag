"""Exception hierarchy. The API layer maps these to HTTP problem responses."""


class CloudOpsRagError(Exception):
    """Base for all library errors."""


class ConfigurationError(CloudOpsRagError):
    """Invalid or inconsistent settings; raised at startup, never on first request."""


class ProviderError(CloudOpsRagError):
    """An external provider (search, embedding, LLM, reranker) failed."""


class ProviderNotConfiguredError(ProviderError):
    """A provider name was requested that has no implementation registered."""
