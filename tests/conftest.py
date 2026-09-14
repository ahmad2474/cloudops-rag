import os

import pytest

from cloudops_rag.config import Settings


@pytest.fixture(autouse=True)
def _no_external_llm_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hosted providers stay off during tests unless a live run is requested explicitly."""
    if os.environ.get("NVIDIA_LIVE_TESTS") != "1":
        monkeypatch.setenv("ALLOW_NVIDIA_CALLS", "false")
        monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.setenv("ALLOW_AWS_CALLS", "false")


@pytest.fixture
def settings() -> Settings:
    return Settings(app_env="test")
