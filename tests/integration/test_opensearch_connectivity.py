"""Requires `make up`. Skipped automatically when OpenSearch is unreachable."""

import httpx
import pytest

from cloudops_rag.config import Settings
from cloudops_rag.providers.opensearch import OpenSearchProvider

pytestmark = pytest.mark.integration


def _opensearch_up(url: str) -> bool:
    try:
        return httpx.get(f"{url}/_cluster/health", timeout=2.0).status_code == 200
    except httpx.HTTPError:
        return False


async def test_ping_local_opensearch(settings: Settings) -> None:
    if not _opensearch_up(settings.opensearch_url):
        pytest.skip("OpenSearch not running (make up)")
    p = OpenSearchProvider(settings.opensearch_url, settings.opensearch_index_prefix)
    try:
        assert await p.ping() is True
    finally:
        await p.close()
