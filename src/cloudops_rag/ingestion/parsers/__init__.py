"""Parsers turn raw corpus files into normalised Markdown with manifest metadata attached."""

from pathlib import Path

from cloudops_rag.ingestion.documents import ManifestEntry
from cloudops_rag.ingestion.parsers.html import parse_aws_html
from cloudops_rag.ingestion.parsers.markdown import parse_markdown
from cloudops_rag.ingestion.parsers.models import ParsedDocument


def parse_entry(entry: ManifestEntry, repo_root: Path) -> ParsedDocument:
    """Dispatch on file type. Raises FileNotFoundError for unfetched public docs."""
    path = repo_root / entry.path
    raw = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix == ".html":
        body = parse_aws_html(raw)
    else:
        body = parse_markdown(raw)
    return ParsedDocument(
        metadata=entry.metadata, body=body, source_path=entry.path, content_hash=entry.content_hash
    )


__all__ = ["ParsedDocument", "parse_aws_html", "parse_entry", "parse_markdown"]
