"""Fetch curated public documentation listed in data/sources/registry.yaml into data/sources/raw/.

    uv run python apps/ingestion/fetch_sources.py [--only ID ...] [--force]

Raw files are gitignored: public content is fetched, never vendored. Each fetch writes
``<document_id>.<ext>`` plus ``<document_id>.meta.json`` (url, status, etag, fetched_at, bytes).
"""

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY = REPO_ROOT / "data" / "sources" / "registry.yaml"
RAW_DIR = REPO_ROOT / "data" / "sources" / "raw"
USER_AGENT = "cloudops-rag-corpus-fetcher/0.1 (+portfolio project; contact via repo)"


def _ext_for(content_type: str, url: str) -> str:
    if "markdown" in content_type or url.endswith((".md", ".mdx")):
        return "md"
    if "html" in content_type:
        return "html"
    return "txt"


def fetch_one(client: httpx.Client, item: dict[str, Any], force: bool) -> str:
    doc_id = item["document_id"]
    url = item["source_url"]
    meta_path = RAW_DIR / f"{doc_id}.meta.json"
    if meta_path.exists() and not force:
        existing = [p for p in RAW_DIR.glob(f"{doc_id}.*") if p != meta_path]
        if existing:
            return "cached"
    try:
        r = client.get(url)
    except httpx.HTTPError as exc:
        return f"error: {exc}"
    if r.status_code != 200:
        return f"http {r.status_code}"
    ext = _ext_for(r.headers.get("content-type", ""), url)
    for stale in RAW_DIR.glob(f"{doc_id}.*"):
        stale.unlink()
    (RAW_DIR / f"{doc_id}.{ext}").write_bytes(r.content)
    meta_path.write_text(
        json.dumps(
            {
                "document_id": doc_id,
                "url": url,
                "final_url": str(r.url),
                "status": r.status_code,
                "content_type": r.headers.get("content-type"),
                "etag": r.headers.get("etag"),
                "last_modified": r.headers.get("last-modified"),
                "bytes": len(r.content),
                "fetched_at": datetime.now(UTC).isoformat(timespec="seconds"),
            },
            indent=2,
        )
        + "\n"
    )
    return f"ok ({len(r.content) // 1024} KB, .{ext})"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", nargs="*", default=None, help="document_ids to fetch")
    parser.add_argument("--force", action="store_true", help="re-fetch even if cached")
    args = parser.parse_args()

    registry: dict[str, Any] = yaml.safe_load(REGISTRY.read_text())
    items = registry["sources"]
    if args.only:
        items = [i for i in items if i["document_id"] in set(args.only)]
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    failures = 0
    with httpx.Client(
        headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=30.0
    ) as client:
        for item in items:
            result = fetch_one(client, item, args.force)
            ok = result.startswith(("ok", "cached"))
            failures += not ok
            print(f"{'✓' if ok else '✗'} {item['document_id']:<40} {result}")
            if result.startswith("ok"):
                time.sleep(0.5)  # be polite
    print(f"\n{len(items) - failures}/{len(items)} fetched")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
