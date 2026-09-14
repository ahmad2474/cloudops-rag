"""Index the corpus into OpenSearch (or the in-memory stub) from data/manifest.json.

    uv run python apps/ingestion/index_corpus.py            # incremental (by content hash)
    uv run python apps/ingestion/index_corpus.py --dry-run  # plan + token/cost estimate only
    uv run python apps/ingestion/index_corpus.py --full     # re-embed everything
    uv run python apps/ingestion/index_corpus.py --drop     # drop indices first (schema change)

Bedrock embedding requires EMBEDDING_PROVIDER=bedrock and ALLOW_AWS_CALLS=true; run --dry-run
first and get the printed estimate approved.
"""

import argparse
import asyncio
import sys
from pathlib import Path

from cloudops_rag.config import load_settings
from cloudops_rag.ingestion.documents import Manifest
from cloudops_rag.ingestion.indexer import Indexer
from cloudops_rag.logging import configure_logging
from cloudops_rag.providers.opensearch import OpenSearchProvider
from cloudops_rag.providers.registry import build_providers

REPO_ROOT = Path(__file__).resolve().parents[2]


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--drop", action="store_true", help="drop indices before indexing")
    args = parser.parse_args()

    settings = load_settings()
    configure_logging("WARNING")
    providers = build_providers(settings)
    manifest = Manifest.model_validate_json((REPO_ROOT / "data" / "manifest.json").read_text())

    print(
        f"embedding={settings.embedding_provider}:{settings.embedding_model} "
        f"dims={settings.embedding_dimensions} search={settings.opensearch_url} "
        f"prefix={settings.opensearch_index_prefix} allow_aws_calls={settings.allow_aws_calls}"
    )
    try:
        if args.drop and not args.dry_run and isinstance(providers.search, OpenSearchProvider):
            await providers.search.drop_indices()
            print("dropped indices")
        indexer = Indexer(providers.embedding, providers.search, repo_root=REPO_ROOT)
        r = await indexer.run(manifest, full=args.full, dry_run=args.dry_run)
    finally:
        await providers.search.close()

    verb = "would index" if args.dry_run else "indexed"
    print(f"\n{verb} {len(r.indexed)} documents → {r.parents} parents, {r.chunks} chunks")
    print(
        f"skipped unchanged: {len(r.skipped_unchanged)}   "
        f"unfetched: {len(r.skipped_unfetched)}   removed: {len(r.removed)}"
    )
    print(
        f"embedding tokens ≈ {r.embed_tokens:,} → est. ${r.cost_usd(settings.embedding_model):.4f} "
        f"({settings.embedding_model}) in {r.seconds}s"
    )
    if r.failed:
        print(f"\n✗ {len(r.failed)} failed:")
        for did, err in r.failed.items():
            print(f"  - {did}: {err}")
        return 1
    if not args.dry_run:
        stats = await _stats(settings)
        print(f"index totals: {stats}")
    return 0


async def _stats(settings) -> dict:  # type: ignore[no-untyped-def,type-arg]
    s = OpenSearchProvider(
        settings.opensearch_url,
        settings.opensearch_index_prefix,
        auth=settings.opensearch_auth,
        region=settings.aws_region,
    )
    try:
        return await s.stats()
    finally:
        await s.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
