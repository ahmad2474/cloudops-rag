import pytest

from cloudops_rag.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(app_env="test")
