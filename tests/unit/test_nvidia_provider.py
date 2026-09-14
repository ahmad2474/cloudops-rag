"""NVIDIA NIM provider against an in-process httpx transport — no network."""

import json
from typing import Any

import httpx
import pytest

from cloudops_rag.config import Settings
from cloudops_rag.errors import ConfigurationError, ProviderError, ProviderTimeoutError
from cloudops_rag.providers.nvidia import NvidiaLLMProvider
from cloudops_rag.providers.registry import build_providers


def _client(handler: Any) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://nim.test/v1")


def _sse(*chunks: dict[str, Any]) -> str:
    return "".join(f"data: {json.dumps(c)}\n\n" for c in chunks) + "data: [DONE]\n\n"


async def test_generate_parses_openai_shape_and_sends_grounding_params() -> None:
    seen: dict[str, Any] = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen["path"] = req.url.path
        seen["body"] = json.loads(req.content)
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"role": "assistant", "content": "Pods pend. [S1]"}}],
                "usage": {"prompt_tokens": 40, "completion_tokens": 5},
            },
        )

    p = NvidiaLLMProvider("meta/llama-3.3-70b-instruct", api_key=None, client=_client(handler))
    r = await p.generate("sys", "user", max_tokens=99)
    assert r.text == "Pods pend. [S1]" and (r.input_tokens, r.output_tokens) == (40, 5)
    assert r.model == "meta/llama-3.3-70b-instruct"
    assert seen["path"] == "/v1/chat/completions"
    assert seen["body"]["temperature"] == 0.0 and seen["body"]["max_tokens"] == 99
    assert seen["body"]["stream"] is False
    assert [m["role"] for m in seen["body"]["messages"]] == ["system", "user"]


async def test_stream_yields_deltas_then_done_with_usage() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        assert json.loads(req.content)["stream_options"] == {"include_usage": True}
        body = _sse(
            {"choices": [{"delta": {"content": "Hel"}}]},
            {"choices": [{"delta": {"content": "lo"}}]},
            {"choices": [], "usage": {"prompt_tokens": 7, "completion_tokens": 2}},
        )
        return httpx.Response(200, content=body, headers={"content-type": "text/event-stream"})

    p = NvidiaLLMProvider(api_key=None, client=_client(handler))
    events = [e async for e in p.generate_stream("s", "u")]
    assert [e.delta for e in events[:-1]] == ["Hel", "lo"]
    done = events[-1]
    assert done.done and done.result is not None
    assert done.result.text == "Hello" and done.result.input_tokens == 7


async def test_missing_usage_falls_back_to_tokenizer_estimate() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "four words in here"}}]}
        )

    r = await NvidiaLLMProvider(api_key=None, client=_client(handler)).generate("system", "user")
    assert r.output_tokens >= 3 and r.input_tokens >= 2


@pytest.mark.parametrize(
    ("status", "retryable"), [(429, True), (503, True), (400, False), (401, False)]
)
async def test_http_errors_map_to_provider_error(status: int, retryable: bool) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status, text="nope")

    p = NvidiaLLMProvider(api_key=None, client=_client(handler))
    with pytest.raises(ProviderError) as ei:
        await p.generate("s", "u")
    assert ei.value.retryable is retryable and f"HTTP {status}" in str(ei.value)


async def test_stream_http_error_is_raised_before_any_delta() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="slow down")

    p = NvidiaLLMProvider(api_key=None, client=_client(handler))
    with pytest.raises(ProviderError, match="429"):
        async for _ in p.generate_stream("s", "u"):
            pass


async def test_timeout_is_a_timeout_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow")

    with pytest.raises(ProviderTimeoutError):
        await NvidiaLLMProvider(api_key=None, client=_client(handler)).generate("s", "u")


def test_refuses_without_explicit_gate_or_key() -> None:
    with pytest.raises(ConfigurationError, match="ALLOW_NVIDIA_CALLS"):
        NvidiaLLMProvider(api_key="nvapi-x", allow_nvidia_calls=False)
    with pytest.raises(ConfigurationError, match="NVIDIA_API_KEY"):
        NvidiaLLMProvider(api_key=None, allow_nvidia_calls=True)


def test_registry_wires_nvidia_and_settings_hide_the_key() -> None:
    s = Settings(
        app_env="test",
        llm_provider="nvidia",
        llm_model="meta/llama-3.3-70b-instruct",
        nvidia_api_key="nvapi-secret",
        allow_nvidia_calls=True,
    )
    assert "nvapi-secret" not in repr(s) and "nvapi-secret" not in s.model_dump_json()
    p = build_providers(s)
    assert isinstance(p.llm, NvidiaLLMProvider) and p.llm.model == "meta/llama-3.3-70b-instruct"


def test_nvidia_is_rejected_for_the_aws_environment() -> None:
    s = Settings(app_env="aws", llm_provider="nvidia", auth_secret="x" * 40, auth_users="[]")
    assert any("nvidia" in p for p in s.validate_for_environment())
