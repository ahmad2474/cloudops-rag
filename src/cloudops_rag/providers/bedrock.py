"""AWS Bedrock providers: Titan Text Embeddings V2 and any Converse-API chat model.

Cost guard: construction requires ``allow_aws_calls=True`` (Settings.ALLOW_AWS_CALLS). Nothing
here is reachable unless the operator flipped that switch for an approved run.

boto3 is synchronous; calls are wrapped in ``asyncio.to_thread`` with bounded concurrency so
the event loop is never blocked and Bedrock's per-model TPS quotas aren't hammered.
"""

import asyncio
import json
from collections.abc import Sequence
from typing import Any

import boto3
from botocore.config import Config

from cloudops_rag.errors import ConfigurationError, ProviderError
from cloudops_rag.providers.base import LLMResult

_RETRY = Config(
    retries={"max_attempts": 6, "mode": "adaptive"}, read_timeout=60, connect_timeout=10
)


def _client(region: str, allow: bool, client: Any | None) -> Any:
    if client is not None:
        return client
    if not allow:
        raise ConfigurationError(
            "Bedrock provider requested but ALLOW_AWS_CALLS is not true. "
            "Get a cost estimate approved, then set ALLOW_AWS_CALLS=true for the run."
        )
    return boto3.client("bedrock-runtime", region_name=region, config=_RETRY)


class BedrockEmbeddingProvider:
    """amazon.titan-embed-text-v2:0 — one text per invoke, normalised output."""

    def __init__(
        self,
        model: str = "amazon.titan-embed-text-v2:0",
        dimensions: int = 1024,
        region: str = "us-east-1",
        *,
        allow_aws_calls: bool = False,
        concurrency: int = 8,
        client: Any | None = None,
    ) -> None:
        self._model = model
        self._dimensions = dimensions
        self._client = _client(region, allow_aws_calls, client)
        self._sem = asyncio.Semaphore(concurrency)

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def _invoke(self, text: str) -> list[float]:
        body = json.dumps({"inputText": text, "dimensions": self._dimensions, "normalize": True})
        try:
            res = self._client.invoke_model(
                modelId=self._model,
                body=body,
                accept="application/json",
                contentType="application/json",
            )
        except Exception as exc:  # botocore raises many classes; keep provider boundary clean
            raise ProviderError(f"bedrock embed failed: {exc}") from exc
        payload = json.loads(res["body"].read())
        emb = payload.get("embedding")
        if not isinstance(emb, list) or len(emb) != self._dimensions:
            raise ProviderError("bedrock embed returned unexpected payload")
        return [float(x) for x in emb]

    async def _one(self, text: str) -> list[float]:
        async with self._sem:
            return await asyncio.to_thread(self._invoke, text)

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return list(await asyncio.gather(*(self._one(t) for t in texts)))

    async def embed_query(self, text: str) -> list[float]:
        return await self._one(text)


class BedrockLLMProvider:
    """Any Converse-API model (Nova, DeepSeek, Llama, Claude…). Temperature 0 for grounding."""

    def __init__(
        self,
        model: str = "amazon.nova-lite-v1:0",
        region: str = "us-east-1",
        *,
        allow_aws_calls: bool = False,
        client: Any | None = None,
    ) -> None:
        self._model = model
        self._client = _client(region, allow_aws_calls, client)

    @property
    def model(self) -> str:
        return self._model

    def _converse(self, system: str, user: str, max_tokens: int) -> LLMResult:
        try:
            res = self._client.converse(
                modelId=self._model,
                system=[{"text": system}],
                messages=[{"role": "user", "content": [{"text": user}]}],
                inferenceConfig={"maxTokens": max_tokens, "temperature": 0.0, "topP": 0.9},
            )
        except Exception as exc:
            raise ProviderError(f"bedrock converse failed: {exc}") from exc
        parts = res.get("output", {}).get("message", {}).get("content", [])
        text = "".join(p.get("text", "") for p in parts)
        usage = res.get("usage", {})
        return LLMResult(
            text=text,
            input_tokens=int(usage.get("inputTokens", 0)),
            output_tokens=int(usage.get("outputTokens", 0)),
            model=self._model,
        )

    async def generate(self, system: str, user: str, *, max_tokens: int = 1024) -> LLMResult:
        return await asyncio.to_thread(self._converse, system, user, max_tokens)
