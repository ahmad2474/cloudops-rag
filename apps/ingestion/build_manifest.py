"""Validate the corpus and write data/manifest.json.

    uv run python apps/ingestion/build_manifest.py [--check]

--check: validate and compare against the committed manifest without writing (CI mode).
"""

import argparse
import json
import sys
from pathlib import Path

from cloudops_rag.ingestion.documents import Manifest
from cloudops_rag.ingestion.manifest import ManifestError, build_manifest, comparable

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "data" / "manifest.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate only; fail if stale")
    args = parser.parse_args()

    try:
        manifest = build_manifest(REPO_ROOT)
    except ManifestError as exc:
        print(f"✗ corpus invalid — {len(exc.problems)} problem(s):", file=sys.stderr)
        for p in exc.problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    # generated_at is excluded from the staleness comparison.
    payload = manifest.model_dump(mode="json")
    if args.check:
        if not MANIFEST_PATH.exists():
            print("✗ data/manifest.json missing; run without --check", file=sys.stderr)
            return 1
        committed = Manifest.model_validate_json(MANIFEST_PATH.read_text())
        if comparable(committed) != comparable(manifest):
            print("✗ data/manifest.json is stale; run build_manifest.py", file=sys.stderr)
            return 1
        print(f"✓ manifest up to date ({len(manifest.documents)} documents)")
        return 0

    MANIFEST_PATH.write_text(json.dumps(payload, indent=2) + "\n")
    by_type: dict[str, int] = {}
    unfetched = 0
    for d in manifest.documents:
        by_type[d.metadata.document_type] = by_type.get(d.metadata.document_type, 0) + 1
        unfetched += not d.fetched
    print(f"✓ wrote {MANIFEST_PATH.relative_to(REPO_ROOT)} — {len(manifest.documents)} documents")
    for t, n in sorted(by_type.items()):
        print(f"  {t:<24}{n:>4}")
    if unfetched:
        print(f"  ({unfetched} public documents not fetched; run fetch_sources.py)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
