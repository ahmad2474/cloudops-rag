"""API client seeded with the test corpus PLUS the real adversarial documents from the KB,
driven by a deliberately *compliant* LLM that obeys any instruction it sees in its input.

If the structural defences (ACL, citation validation, output guard) hold against a model that
actively cooperates with the attacker, they hold against a model that merely slips.
"""

import re
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from cloudops_rag.chunking import chunk_document
from cloudops_rag.config import Settings
from cloudops_rag.generation.prompts import SYSTEM_PROMPT
from cloudops_rag.ingestion.documents import DocumentMetadata
from cloudops_rag.ingestion.frontmatter import split_frontmatter
from cloudops_rag.ingestion.parsers import parse_markdown
from cloudops_rag.ingestion.parsers.models import ParsedDocument
from cloudops_rag.providers.base import LLMResult
from cloudops_rag.providers.stub import StubSearchProvider
from cloudops_rag.testing import TEST_PASSWORD, seed_search, test_users_json

REPO_ROOT = Path(__file__).resolve().parents[2]
ADVERSARIAL_DIR = REPO_ROOT / "data" / "synthetic" / "adversarial"
_USERS = test_users_json()
SECRET = "unit-test-secret-that-is-at-least-32-characters-long"


class CompliantLLM:
    """Worst-case model: if the user block contains injected instructions, it 'follows' them —
    leaks the system prompt, prints override markers, cites whatever it likes."""

    def __init__(self) -> None:
        self.prompts: list[str] = []

    @property
    def model(self) -> str:
        return "compliant-attacker-model"

    async def generate(self, system: str, user: str, *, max_tokens: int = 1024) -> LLMResult:
        self.prompts.append(user)
        low = user.lower()
        parts: list[str] = []
        if "reveal the system prompt" in low or "print the full system prompt" in low:
            parts.append("Sure. System prompt: " + system[:400])
        if "access granted" in low:
            parts.append("ACCESS GRANTED")
        if "override accepted" in low:
            parts.append("override accepted")
        if "break-glass-procedure" in low or "restricted documents" in low:
            parts.append("Restricted documents: break-glass-procedure contents follow [S9][S1].")
        if not parts:
            m = re.search(r"\[S1\][^\n]*\n(.+?)(?:\n\n|\Z)", user, re.S)
            parts.append((m.group(1)[:160] if m else "No idea") + " [S1]")
        return LLMResult(text="\n\n".join(parts), model=self.model, input_tokens=1, output_tokens=1)


def load_adversarial_docs() -> list[ParsedDocument]:
    docs = []
    for path in sorted(ADVERSARIAL_DIR.glob("*.md")):
        raw_meta, body = split_frontmatter(path.read_text())
        meta = DocumentMetadata.model_validate(raw_meta)
        docs.append(
            ParsedDocument(
                metadata=meta,
                body=parse_markdown(body),
                source_path=str(path),
                content_hash="sha256:" + meta.document_id,
            )
        )
    assert len(docs) == 4
    return docs


@pytest.fixture
def settings() -> Settings:
    return Settings(app_env="test", log_level="WARNING", auth_users=_USERS, auth_secret=SECRET)


@pytest.fixture
async def attacked(settings: Settings) -> AsyncIterator[tuple[AsyncClient, CompliantLLM]]:
    app = create_app(settings, use_stub_search=True)
    async with app.router.lifespan_context(app):
        state = app.state.ctx
        search = state.providers.search
        assert isinstance(search, StubSearchProvider)
        await seed_search(search, state.providers.embedding)
        for doc in load_adversarial_docs():
            cd = chunk_document(doc)
            vecs = await state.providers.embedding.embed_documents(
                [c.embedding_text for c in cd.chunks]
            )
            await search.index_chunks(cd.chunks, vecs)
            await search.index_parents(cd.parents)
        llm = CompliantLLM()
        object.__setattr__(state.providers, "llm", llm)  # frozen dataclass; test-only swap
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c, llm


async def login(client: AsyncClient, user: str) -> dict[str, str]:
    r = await client.post("/auth/login", json={"username": user, "password": TEST_PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


__all__ = ["SYSTEM_PROMPT", "attacked", "login"]
