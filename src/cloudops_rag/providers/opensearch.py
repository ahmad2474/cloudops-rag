"""OpenSearch search provider. Phase 0: connectivity only. Indexing/search arrive in Phase 2."""

from opensearchpy import AsyncOpenSearch


class OpenSearchProvider:
    def __init__(self, url: str, index_prefix: str) -> None:
        self._client = AsyncOpenSearch(hosts=[url], use_ssl=url.startswith("https"))
        self._index_prefix = index_prefix

    @property
    def index_prefix(self) -> str:
        return self._index_prefix

    async def ping(self) -> bool:
        try:
            return bool(await self._client.ping())
        except Exception:  # readiness probe must never raise
            return False

    async def close(self) -> None:
        await self._client.close()
