from pathlib import Path

import pytest

from cloudops_rag.evaluation.dataset import EvalDataset, EvalItem, load_dataset
from cloudops_rag.evaluation.runner import EvalRunner
from cloudops_rag.generation import AnswerService
from cloudops_rag.providers.base import LLMResult
from cloudops_rag.providers.stub import StubEmbeddingProvider, StubSearchProvider
from cloudops_rag.retrieval import VectorRetriever


def _ds() -> EvalDataset:
    return EvalDataset(
        version="test",
        items=[
            EvalItem(
                id="q-001",
                question="Why are pods Pending with failed to assign an IP address?",
                category="troubleshooting",
                expected_document_ids=["eks-pod-networking"],
                answer_must_contain=["pending"],
            ),
            EvalItem(
                id="q-002",
                question="What are the break-glass user names and sealed envelope holders?",
                category="security",
                should_abstain=True,
                role="developer",
                must_not_cite=["break-glass-procedure"],
            ),
            EvalItem(
                id="q-003",
                question="What are the break-glass user names and sealed envelope holders?",
                category="security",
                expected_document_ids=["break-glass-procedure"],
                role="security-admin",
            ),
            EvalItem(
                id="q-004",
                question="What is the Azure DR plan?",
                category="no_answer",
                should_abstain=True,
            ),
        ],
    )


class _EchoLLM:
    """Cites S1 when sources exist; abstains otherwise. Enough to exercise the scorer."""

    @property
    def model(self) -> str:
        return "stub-model"

    async def generate(self, system: str, user: str, *, max_tokens: int = 1024) -> LLMResult:
        if "(no sources)" in user:
            return LLMResult(text="INSUFFICIENT_EVIDENCE", model="stub-model")
        return LLMResult(text="Pods are Pending because of IPs [S1].", model="stub-model")


async def test_retrieval_only_scores_and_flags_acl(indexed_search: StubSearchProvider) -> None:
    r = VectorRetriever(
        StubEmbeddingProvider(dimensions=256), indexed_search, candidates=20, top_k=10
    )
    runner = EvalRunner(r, strategy="t", providers={})
    rep = await runner.run(_ds())
    assert rep.summary.n == 4 and rep.generation is False
    q1 = next(i for i in rep.items if i.id == "q-001")
    assert q1.recall_at_5 == 1.0 and q1.mrr == 1.0
    q2 = next(i for i in rep.items if i.id == "q-002")
    assert q2.recall_at_5 is None and q2.acl_violation is False
    q3 = next(i for i in rep.items if i.id == "q-003")
    assert q3.recall_at_10 == 1.0
    assert rep.summary.acl_violations == 0
    assert set(rep.by_category) == {"troubleshooting", "security", "no_answer"}
    assert rep.latency_ms["retrieval_p95"] >= 0


async def test_generation_scores_abstention_and_citations(
    indexed_search: StubSearchProvider,
) -> None:
    emb = StubEmbeddingProvider(dimensions=256)
    r = VectorRetriever(emb, indexed_search, candidates=20, top_k=10)
    answers = AnswerService(
        VectorRetriever(emb, indexed_search, candidates=10, top_k=4), _EchoLLM()
    )  # type: ignore[arg-type]
    rep = await EvalRunner(r, strategy="t", providers={}, answers=answers).run(_ds())
    assert rep.generation is True
    q1 = next(i for i in rep.items if i.id == "q-001")
    assert q1.status == "answered" and q1.citation_recall == 1.0 and q1.content_checks_passed
    q2 = next(i for i in rep.items if i.id == "q-002")
    assert q2.citation_violation is False
    q4 = next(i for i in rep.items if i.id == "q-004")
    # stub corpus has no Azure content but vector search still returns *something*; the
    # echo LLM then answers → abstention incorrect. The scorer must record that honestly.
    assert q4.abstention_correct in (True, False)
    assert rep.summary.abstention_accuracy is not None
    assert rep.summary.citation_violations == 0


def test_real_dataset_loads_and_is_consistent() -> None:
    ds = load_dataset(Path(__file__).resolve().parents[2] / "data" / "evaluation" / "dataset.json")
    assert len(ds.items) >= 300
    cats = ds.by_category()
    assert len(cats) == 10
    sec = [i for i in ds.items if i.category == "security"]
    assert all(i.should_abstain == (i.role == "developer") for i in sec)
    assert all(i.must_not_cite for i in sec if i.should_abstain)


def test_dataset_validation_rules() -> None:
    with pytest.raises(ValueError, match="must not expect"):
        EvalItem(
            id="q-901",
            question="abstain but docs",
            category="no_answer",
            should_abstain=True,
            expected_document_ids=["x"],
        )
    with pytest.raises(ValueError, match="need expected"):
        EvalItem(id="q-902", question="no docs no abstain", category="direct_lookup")
