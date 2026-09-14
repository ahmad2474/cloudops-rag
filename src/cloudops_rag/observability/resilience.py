"""Deadlines and bounded retries for provider calls.

Retries are only for *retryable* failures (throttling, transient upstream errors, timeouts) and
only for idempotent operations. Generation is never retried after a model has consumed tokens
unless the provider raised before returning any output.
"""

import asyncio
import random
from collections.abc import Awaitable, Callable

from cloudops_rag.errors import ProviderError, ProviderTimeoutError
from cloudops_rag.logging import get_logger

log = get_logger(__name__)


async def with_deadline[T](coro: Awaitable[T], seconds: float, *, what: str) -> T:
    try:
        return await asyncio.wait_for(coro, timeout=seconds)
    except TimeoutError as exc:
        raise ProviderTimeoutError(f"{what} exceeded {seconds:.1f}s") from exc


async def retry[T](
    fn: Callable[[], Awaitable[T]],
    *,
    what: str,
    attempts: int = 3,
    base_delay: float = 0.25,
    max_delay: float = 2.0,
) -> T:
    last: Exception | None = None
    for i in range(1, attempts + 1):
        try:
            return await fn()
        except ProviderError as exc:
            last = exc
            if not exc.retryable or i == attempts:
                raise
            delay = min(max_delay, base_delay * 2 ** (i - 1)) * (0.5 + random.random())  # noqa: S311
            log.warning(
                "provider_retry", what=what, attempt=i, delay_s=round(delay, 2), error=str(exc)
            )
            await asyncio.sleep(delay)
    raise last if last else ProviderError(f"{what} failed")  # pragma: no cover


class TokenBucket:
    """Per-key token bucket. ``rpm`` requests per minute, burst = rpm."""

    def __init__(self, rpm: int) -> None:
        self._rate = rpm / 60.0
        self._cap = float(rpm)
        self._state: dict[str, tuple[float, float]] = {}  # key -> (tokens, last_ts)

    def take(self, key: str, now: float) -> float:
        """Return 0.0 if allowed, else seconds until the next token."""
        tokens, last = self._state.get(key, (self._cap, now))
        tokens = min(self._cap, tokens + (now - last) * self._rate)
        if tokens >= 1.0:
            self._state[key] = (tokens - 1.0, now)
            return 0.0
        self._state[key] = (tokens, now)
        return (1.0 - tokens) / self._rate

    def prune(self, now: float, idle_seconds: float = 300.0) -> None:
        self._state = {k: v for k, v in self._state.items() if now - v[1] < idle_seconds}
