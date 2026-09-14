"""Run the evaluation suite.

    uv run python apps/evaluation/run.py                     # retrieval only (cheap)
    uv run python apps/evaluation/run.py --generation        # + answers, citations, abstention
    uv run python apps/evaluation/run.py --judge             # + LLM-judge faithfulness
    uv run python apps/evaluation/run.py --compare evaluation/reports/<baseline>.json
    uv run python apps/evaluation/run.py --gate evaluation/reports/<baseline>.json --threshold 0.02

Writes evaluation/reports/<strategy>-<timestamp>.json (and --out to name it).
"""

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from cloudops_rag.config import load_settings
from cloudops_rag.evaluation.dataset import load_dataset, validate_against_manifest
from cloudops_rag.evaluation.report import EvalReport, MetricBlock
from cloudops_rag.evaluation.runner import EvalRunner
from cloudops_rag.generation import AnswerService
from cloudops_rag.ingestion.documents import Manifest
from cloudops_rag.logging import configure_logging
from cloudops_rag.providers.registry import build_providers
from cloudops_rag.retrieval import Strategy
from cloudops_rag.retrieval.factory import make_retriever

REPO_ROOT = Path(__file__).resolve().parents[2]
REPORTS = REPO_ROOT / "evaluation" / "reports"


def _fmt(b: MetricBlock) -> str:
    s = (
        f"R@5 {b.recall_at_5:.3f}  R@10 {b.recall_at_10:.3f}  MRR {b.mrr:.3f}  "
        f"NDCG {b.ndcg_at_10:.3f}  ACLviol {b.acl_violations}"
    )
    if b.abstention_accuracy is not None:
        s += f"  | abst {b.abstention_accuracy:.3f}"
    if b.citation_precision is not None:
        s += f"  citeP {b.citation_precision:.3f} citeR {b.citation_recall or 0:.3f}"
    if b.injection_success_rate is not None:
        s += f"  inj {b.injection_success_rate:.3f}"
    if b.faithfulness is not None:
        s += f"  faith {b.faithfulness:.3f}"
    return s


def print_report(r: EvalReport) -> None:
    print(f"\n== {r.strategy}  dataset v{r.dataset_version}  generation={r.generation}")
    print(f"   providers: {r.providers}")
    print(f"   overall (n={r.summary.n}): {_fmt(r.summary)}")
    for cat, b in r.by_category.items():
        print(f"   {cat:<22} n={b.n:<3} {_fmt(b)}")
    print(f"   latency ms: {r.latency_ms}")
    print(f"   cost: {r.cost}")


def compare(new: EvalReport, base: EvalReport) -> dict[str, float]:
    deltas = {
        "recall_at_5": new.summary.recall_at_5 - base.summary.recall_at_5,
        "recall_at_10": new.summary.recall_at_10 - base.summary.recall_at_10,
        "mrr": new.summary.mrr - base.summary.mrr,
        "ndcg_at_10": new.summary.ndcg_at_10 - base.summary.ndcg_at_10,
    }
    print(f"\n   vs {base.strategy} ({base.generated_at}):")
    for k, v in deltas.items():
        print(f"     {k:<12} {v:+.3f}")
    return deltas


async def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", default=str(REPO_ROOT / "data" / "evaluation" / "dataset.json"))
    p.add_argument(
        "--strategy",
        default=None,
        choices=["vector", "bm25", "hybrid_rrf", "hybrid_weighted"],
        help="retrieval strategy (default: RETRIEVAL_STRATEGY setting)",
    )
    p.add_argument("--rerank", action="store_true", help="enable reranking (RERANKER_PROVIDER)")
    p.add_argument("--generation", action="store_true")
    p.add_argument(
        "--judge", action="store_true", help="LLM-judge faithfulness (implies --generation)"
    )
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--candidates", type=int, default=50)
    p.add_argument("--top-k", type=int, default=20, help="children considered for ranking")
    p.add_argument("--out", default=None)
    p.add_argument("--compare", default=None)
    p.add_argument("--gate", default=None, help="fail if recall@5/MRR drop more than --threshold")
    p.add_argument("--threshold", type=float, default=0.02)
    args = p.parse_args()
    if args.judge:
        args.generation = True

    settings = load_settings()
    configure_logging("WARNING")
    manifest = Manifest.model_validate_json((REPO_ROOT / "data" / "manifest.json").read_text())
    ds = load_dataset(Path(args.dataset))
    problems = validate_against_manifest(ds, {d.metadata.document_id for d in manifest.documents})
    if problems:
        print("✗ dataset references unknown documents:", *problems[:10], sep="\n  ")
        return 1

    providers = build_providers(settings)
    provider_labels = {
        "embedding": f"{settings.embedding_provider}:{settings.embedding_model}",
        "llm": f"{settings.llm_provider}:{settings.llm_model}",
        "search": settings.search_provider,
    }
    strategy: Strategy | None = args.strategy
    rerank = True if args.rerank else None
    retriever = make_retriever(
        providers,
        settings,
        strategy=strategy,
        rerank=rerank,
        candidates=args.candidates,
        top_k=args.top_k,
    )
    label = retriever.label
    provider_labels["reranker"] = (
        f"{settings.reranker_provider}:{settings.reranker_model}" if retriever._reranker else "off"
    )
    answers = None
    if args.generation:
        answers = AnswerService(
            make_retriever(providers, settings, strategy=strategy, rerank=rerank),
            providers.llm,
            context_token_budget=settings.context_token_budget,
            max_tokens=settings.llm_max_tokens,
        )
    judge = providers.llm if args.judge else None
    if args.judge and settings.llm_provider == "stub":
        print("note: --judge with the stub LLM produces no faithfulness scores")

    try:
        runner = EvalRunner(
            retriever,
            strategy=label,
            providers=provider_labels,
            answers=answers,
            judge=judge,
        )
        report = await runner.run(ds, limit=args.limit)
    finally:
        await providers.search.close()

    print_report(report)
    REPORTS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    out = Path(args.out) if args.out else REPORTS / f"{label}-{stamp}.json"
    await asyncio.to_thread(
        out.write_text, json.dumps(report.model_dump(mode="json"), indent=2) + "\n"
    )
    shown = out.relative_to(REPO_ROOT) if out.is_relative_to(REPO_ROOT) else out
    print(f"\n   wrote {shown}")

    base_path = args.gate or args.compare
    if base_path:
        base = EvalReport.model_validate_json(await asyncio.to_thread(Path(base_path).read_text))
        deltas = compare(report, base)
        if args.gate:
            regressed = [k for k in ("recall_at_5", "mrr") if deltas[k] < -args.threshold]
            if regressed:
                print(f"\n✗ regression beyond {args.threshold}: {regressed}")
                return 2
            print(f"\n✓ no regression beyond {args.threshold}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
