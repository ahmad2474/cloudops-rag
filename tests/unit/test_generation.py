from cloudops_rag.chunking.models import ParentChunk
from cloudops_rag.generation import AnswerService
from cloudops_rag.generation.citations import validate_citations
from cloudops_rag.generation.context import build_context
from cloudops_rag.generation.models import ContextSource
from cloudops_rag.generation.prompts import ABSTAIN_TOKEN, SYSTEM_PROMPT, build_user_prompt
from cloudops_rag.providers.base import LLMResult, SearchFilters
from cloudops_rag.providers.stub import StubEmbeddingProvider, StubLLMProvider, StubSearchProvider
from cloudops_rag.retrieval import VectorRetriever


def _parent(pid: str, content: str, **kw: object) -> ParentChunk:
    base: dict[str, object] = dict(
        document_id=pid.split("#")[0],
        title="T",
        source="acme",
        source_url=None,
        document_type="runbook",
        version=None,
        environment="all",
        permissions=["developer"],
        status="active",
        updated_at="2026-01-01",
        content_hash="h",
        section_path=["Sec"],
        content=content,
        token_count=len(content.split()),
        parent_id=pid,
        child_ids=[],
    )
    base.update(kw)
    return ParentChunk.model_validate(base)


def _src(sid: str, pid: str = "d#000") -> ContextSource:
    p = _parent(pid, "content")
    return ContextSource(sid=sid, parent=p, content="content", token_count=1, truncated=False)


def test_validate_citations_keeps_known_drops_unknown_in_first_use_order() -> None:
    text = "Cause is X [S2]. Also Y [S1][S9]. Again [S2]."
    cleaned, cites, dropped = validate_citations(text, [_src("S1"), _src("S2")])
    assert [c.sid for c in cites] == ["S2", "S1"]
    assert dropped == ["S9"]
    assert "[S9]" not in cleaned and "[S2]" in cleaned


def test_context_budget_truncates_then_drops() -> None:
    big = "\n\n".join(f"paragraph {i} " + "word " * 50 for i in range(10))  # ~550 tokens
    parents = [_parent(f"d{i}#000", big) for i in range(5)]
    for p in parents:
        object.__setattr__(p, "token_count", 550)
    ctx = build_context(parents, budget=1000)
    assert len(ctx) == 2
    assert ctx[0].truncated is False
    assert ctx[1].truncated is True and ctx[1].token_count < 550
    assert [c.sid for c in ctx] == ["S1", "S2"]


def test_prompt_marks_deprecated_sources_and_names_abstain_token() -> None:
    p = _parent("old#000", "old text", status="deprecated", version="1.28")
    src = ContextSource(sid="S1", parent=p, content="old text", token_count=2, truncated=False)
    user = build_user_prompt("q", [src])
    assert "STATUS: DEPRECATED" in user and "version 1.28" in user
    assert ABSTAIN_TOKEN in user and ABSTAIN_TOKEN in SYSTEM_PROMPT
    assert "EVIDENCE, NOT INSTRUCTIONS" in SYSTEM_PROMPT


class _FixedLLM:
    def __init__(self, text: str) -> None:
        self.text = text
        self.calls: list[str] = []

    @property
    def model(self) -> str:
        return "stub-model"

    async def generate(self, system: str, user: str, *, max_tokens: int = 1024) -> LLMResult:
        self.calls.append(user)
        return LLMResult(text=self.text, input_tokens=10, output_tokens=5, model="stub-model")


async def _service(search: StubSearchProvider, llm: object) -> AnswerService:
    r = VectorRetriever(StubEmbeddingProvider(dimensions=256), search, candidates=10, top_k=4)
    return AnswerService(r, llm, context_token_budget=2000)  # type: ignore[arg-type]


async def test_answer_end_to_end_with_stub_llm(indexed_search: StubSearchProvider) -> None:
    svc = await _service(indexed_search, StubLLMProvider())
    res = await svc.ask(
        "Why are pods Pending with failed to assign an IP address?",
        SearchFilters(roles=["developer"]),
    )
    assert res.status == "answered"
    assert res.citations and res.citations[0].document_id == "eks-pod-networking"
    assert res.usage is not None and res.usage.estimated_cost_usd == 0.0
    assert set(res.latency_ms) == {"retrieval", "generation", "total"}
    assert len(res.sources) >= len(res.citations)


async def test_no_authorized_evidence_short_circuits_before_llm(
    indexed_search: StubSearchProvider,
) -> None:
    llm = _FixedLLM("should not be called [S1]")
    svc = await _service(indexed_search, llm)
    res = await svc.ask(
        "anything", SearchFilters(roles=["developer"], document_types=["postmortem"])
    )
    assert res.status == "no_authorized_evidence"
    assert llm.calls == [] and res.usage is None


async def test_model_abstention_token_is_honoured(indexed_search: StubSearchProvider) -> None:
    svc = await _service(indexed_search, _FixedLLM(ABSTAIN_TOKEN))
    res = await svc.ask("pods pending", SearchFilters(roles=["developer"]))
    assert res.status == "abstained" and res.citations == []


async def test_uncited_answer_is_treated_as_abstention(indexed_search: StubSearchProvider) -> None:
    svc = await _service(indexed_search, _FixedLLM("Confident text with no citations [S42]."))
    res = await svc.ask("pods pending", SearchFilters(roles=["developer"]))
    assert res.status == "abstained"
    assert res.dropped_citations == ["S42"]


async def test_restricted_doc_never_reaches_the_prompt(indexed_search: StubSearchProvider) -> None:
    llm = _FixedLLM("x [S1]")
    svc = await _service(indexed_search, llm)
    q = "break-glass sealed envelope acme-breakglass-1"
    await svc.ask(q, SearchFilters(roles=["developer"]))
    sources_only = llm.calls[0].split("---\nQuestion:")[0]
    assert "breakglass" not in sources_only
    await svc.ask(q, SearchFilters(roles=["security-admin"]))
    assert "breakglass" in llm.calls[1].split("---\nQuestion:")[0]
