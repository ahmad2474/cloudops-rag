import asyncio

import pytest

from cloudops_rag.errors import ProviderError, ProviderTimeoutError
from cloudops_rag.observability.resilience import TokenBucket, retry, with_deadline


async def test_with_deadline_raises_timeout_error() -> None:
    async def slow() -> int:
        await asyncio.sleep(0.2)
        return 1

    with pytest.raises(ProviderTimeoutError, match="slow exceeded"):
        await with_deadline(slow(), 0.01, what="slow")
    assert await with_deadline(asyncio.sleep(0, result=7), 0.5, what="fast") == 7


async def test_retry_only_on_retryable_errors() -> None:
    calls = {"n": 0}

    async def flaky() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise ProviderError("throttled", retryable=True)
        return "ok"

    assert await retry(flaky, what="flaky", attempts=3, base_delay=0.001) == "ok"
    assert calls["n"] == 3

    async def fatal() -> str:
        calls["n"] += 1
        raise ProviderError("bad request", retryable=False)

    calls["n"] = 0
    with pytest.raises(ProviderError, match="bad request"):
        await retry(fatal, what="fatal", attempts=3, base_delay=0.001)
    assert calls["n"] == 1


async def test_retry_gives_up_after_attempts() -> None:
    async def always() -> None:
        raise ProviderError("still throttled", retryable=True)

    with pytest.raises(ProviderError, match="still throttled"):
        await retry(always, what="x", attempts=2, base_delay=0.001)


def test_token_bucket_refills_over_time() -> None:
    b = TokenBucket(rpm=60)  # 1 token/s, burst 60
    now = 1000.0
    for _ in range(60):
        assert b.take("u", now) == 0.0
    wait = b.take("u", now)
    assert 0 < wait <= 1.0
    assert b.take("u", now + 1.0) == 0.0
    assert b.take("other", now) == 0.0
    b.prune(now + 10_000)
    assert b.take("u", now + 10_000) == 0.0
