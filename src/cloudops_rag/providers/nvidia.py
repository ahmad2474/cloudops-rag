"""NVIDIA NIM (build.nvidia.com hosted endpoints) as an optional LLM provider.

OpenAI-compatible ``/chat/completions`` over httpx. This exists so generation and
LLM-judged evaluation can run locally while Bedrock is unavailable; it is never the AWS
runtime (docs/providers.md). Two gates: the key comes only from ``NVIDIA_API_KEY`` and
``ALLOW_NVIDIA_CALLS=true`` must be set — tests never reach the network.
"""

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from cloudops_rag.chunking.tokens import count_tokens
from cloudops_rag.errors import ConfigurationError, ProviderError, ProviderTimeoutError
from cloudops_rag.providers.base import LLMResult, StreamEvent

DEFAULT_BASE_URL = "https://integrate.api.nvidia.com/v1"
_RETRYABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}


class NvidiaLLMProvider:
    """Any catalog chat model (``meta/llama-3.3-70b-instruct`` …). Temperature 0 for grounding."""

    def __init__(
        self,
        model: str = "meta/llama-3.3-70b-instruct",
        *,
        api_key: str | None,
        base_url: str = DEFAULT_BASE_URL,
        allow_nvidia_calls: bool = False,
        timeout_s: float = 60.0,
        max_concurrency: int = 2,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._model = model
        if client is None:
            if not allow_nvidia_calls:
                raise ConfigurationError(
                    "NVIDIA provider requested but ALLOW_NVIDIA_CALLS is not true. "
                    "Set it explicitly for the run; tests must never set it."
                )
            if not api_key:
                raise ConfigurationError(
                    "LLM_PROVIDER=nvidia needs NVIDIA_API_KEY in the environment"
                )
            client = httpx.AsyncClient(
                base_url=base_url.rstrip("/"),
                headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
                timeout=httpx.Timeout(timeout_s, connect=10.0),
            )
        self._client = client
        # Hosted trial keys are rate-limited (~40 RPM); keep evaluation runs polite.
        self._sem = asyncio.Semaphore(max_concurrency)

    @property
    def model(self) -> str:
        return self._model

    def _body(self, system: str, user: str, max_tokens: int, *, stream: bool) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": self._model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "max_tokens": max_tokens,
            "temperature": 0.0,
            "top_p": 0.9,
            "stream": stream,
        }
        if stream:
            body["stream_options"] = {"include_usage": True}
        return body

    def _result(self, text: str, usage: dict[str, Any] | None, system: str, user: str) -> LLMResult:
        # NIM reports usage on every completion; some streams omit it → tokenizer estimate.
        if usage:
            return LLMResult(
                text=text,
                input_tokens=int(usage.get("prompt_tokens", 0)),
                output_tokens=int(usage.get("completion_tokens", 0)),
                model=self._model,
            )
        return LLMResult(
            text=text,
            input_tokens=count_tokens(system) + count_tokens(user),
            output_tokens=count_tokens(text),
            model=self._model,
        )

    async def generate(self, system: str, user: str, *, max_tokens: int = 1024) -> LLMResult:
        async with self._sem:
            try:
                res = await self._client.post(
                    "/chat/completions", json=self._body(system, user, max_tokens, stream=False)
                )
            except httpx.TimeoutException as exc:
                raise ProviderTimeoutError(f"nvidia chat timed out: {exc}") from exc
            except httpx.HTTPError as exc:
                raise ProviderError(f"nvidia chat failed: {exc}", retryable=True) from exc
        _raise_for_status(res)
        payload = res.json()
        choices = payload.get("choices") or []
        if not choices:
            raise ProviderError("nvidia chat returned no choices")
        text = str(choices[0].get("message", {}).get("content") or "")
        return self._result(text, payload.get("usage"), system, user)

    async def generate_stream(
        self, system: str, user: str, *, max_tokens: int = 1024
    ) -> AsyncIterator[StreamEvent]:
        text_parts: list[str] = []
        usage: dict[str, Any] | None = None
        async with self._sem:
            try:
                async with self._client.stream(
                    "POST",
                    "/chat/completions",
                    json=self._body(system, user, max_tokens, stream=True),
                ) as res:
                    if res.status_code >= 400:
                        await res.aread()
                        _raise_for_status(res)
                    async for line in res.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if data == "[DONE]":
                            break
                        chunk = json.loads(data)
                        if chunk.get("usage"):
                            usage = chunk["usage"]
                        for choice in chunk.get("choices") or []:
                            delta = choice.get("delta", {}).get("content") or ""
                            if delta:
                                text_parts.append(delta)
                                yield StreamEvent(delta=delta)
            except httpx.TimeoutException as exc:
                raise ProviderTimeoutError(f"nvidia stream timed out: {exc}") from exc
            except httpx.HTTPError as exc:
                raise ProviderError(f"nvidia stream failed: {exc}", retryable=True) from exc
        yield StreamEvent(done=True, result=self._result("".join(text_parts), usage, system, user))


def _raise_for_status(res: httpx.Response) -> None:
    if res.status_code < 400:
        return
    detail = res.text[:300]
    raise ProviderError(
        f"nvidia chat HTTP {res.status_code}: {detail}",
        retryable=res.status_code in _RETRYABLE_STATUS,
    )
