"""Live NVIDIA NIM check (one small request). Off by default — `make test-nvidia` runs it with
NVIDIA_LIVE_TESTS=1 ALLOW_NVIDIA_CALLS=true and NVIDIA_API_KEY from the environment."""

import os

import pytest

from cloudops_rag.config import Settings
from cloudops_rag.providers.registry import build_providers

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("NVIDIA_LIVE_TESTS") != "1", reason="set NVIDIA_LIVE_TESTS=1 to call NVIDIA"
    ),
]


async def test_nvidia_round_trip_cites_a_source() -> None:
    s = Settings(app_env="test", llm_provider="nvidia")
    llm = build_providers(s).llm
    r = await llm.generate(
        "Answer only from the sources. Cite as [S1].",
        "Sources:\n\n[S1] Acme runbook\nThe pager rotates every Monday at 09:00 UTC.\n\n"
        "Question: when does the pager rotate?",
        max_tokens=64,
    )
    assert "Monday" in r.text and "[S1]" in r.text
    assert r.input_tokens > 0 and r.output_tokens > 0
