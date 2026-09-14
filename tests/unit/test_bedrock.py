import io
import json

import boto3
import pytest
from botocore.response import StreamingBody
from botocore.stub import Stubber

from cloudops_rag.config import Settings
from cloudops_rag.errors import ConfigurationError, ProviderError
from cloudops_rag.providers.bedrock import BedrockEmbeddingProvider, BedrockLLMProvider
from cloudops_rag.providers.registry import build_providers


def _client():  # type: ignore[no-untyped-def]
    return boto3.client(
        "bedrock-runtime", region_name="us-east-1", aws_access_key_id="x", aws_secret_access_key="y"
    )


def test_bedrock_refuses_without_allow_flag() -> None:
    with pytest.raises(ConfigurationError, match="ALLOW_AWS_CALLS"):
        BedrockEmbeddingProvider(allow_aws_calls=False)
    with pytest.raises(ConfigurationError, match="ALLOW_AWS_CALLS"):
        build_providers(
            Settings(embedding_provider="bedrock", allow_aws_calls=False), use_stub_search=True
        )


async def test_titan_embedding_request_and_response_shape() -> None:
    client = _client()
    vec = [0.1] * 256
    body = json.dumps({"embedding": vec, "inputTextTokenCount": 5}).encode()
    with Stubber(client) as stub:
        stub.add_response(
            "invoke_model",
            {"body": StreamingBody(io.BytesIO(body), len(body)), "contentType": "application/json"},
            {
                "modelId": "amazon.titan-embed-text-v2:0",
                "body": json.dumps({"inputText": "hello", "dimensions": 256, "normalize": True}),
                "accept": "application/json",
                "contentType": "application/json",
            },
        )
        p = BedrockEmbeddingProvider(dimensions=256, client=client)
        assert await p.embed_query("hello") == vec


async def test_titan_embedding_rejects_wrong_dimension() -> None:
    client = _client()
    body = json.dumps({"embedding": [0.1] * 10}).encode()
    with Stubber(client) as stub:
        stub.add_response(
            "invoke_model",
            {"body": StreamingBody(io.BytesIO(body), len(body)), "contentType": "application/json"},
        )
        p = BedrockEmbeddingProvider(dimensions=256, client=client)
        with pytest.raises(ProviderError, match="unexpected payload"):
            await p.embed_query("hello")


async def test_converse_request_and_usage_mapping() -> None:
    client = _client()
    with Stubber(client) as stub:
        stub.add_response(
            "converse",
            {
                "output": {
                    "message": {"role": "assistant", "content": [{"text": "Cause is X [S1]."}]}
                },
                "stopReason": "end_turn",
                "usage": {"inputTokens": 120, "outputTokens": 9, "totalTokens": 129},
                "metrics": {"latencyMs": 300},
            },
            {
                "modelId": "amazon.nova-lite-v1:0",
                "system": [{"text": "sys"}],
                "messages": [{"role": "user", "content": [{"text": "user"}]}],
                "inferenceConfig": {"maxTokens": 256, "temperature": 0.0, "topP": 0.9},
            },
        )
        p = BedrockLLMProvider(client=client)
        r = await p.generate("sys", "user", max_tokens=256)
        assert r.text == "Cause is X [S1]."
        assert (r.input_tokens, r.output_tokens, r.model) == (120, 9, "amazon.nova-lite-v1:0")


async def test_converse_errors_become_provider_errors() -> None:
    client = _client()
    with Stubber(client) as stub:
        stub.add_client_error("converse", "ThrottlingException", "slow down")
        p = BedrockLLMProvider(client=client)
        with pytest.raises(ProviderError, match="converse failed"):
            await p.generate("s", "u")
