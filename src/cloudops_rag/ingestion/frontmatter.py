"""Parse `---` YAML frontmatter from Markdown. Deliberately tiny; no third-party frontmatter lib."""

from typing import Any

import yaml

from cloudops_rag.errors import CloudOpsRagError

DELIMITER = "---"


class FrontmatterError(CloudOpsRagError):
    pass


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Return (metadata, body). Raises FrontmatterError if the block is missing or malformed."""
    if not text.startswith(DELIMITER + "\n"):
        raise FrontmatterError("document must start with a '---' frontmatter block")
    try:
        _, block, body = text.split(DELIMITER + "\n", 2)
    except ValueError as exc:
        raise FrontmatterError("unterminated frontmatter block") from exc
    try:
        loaded = yaml.safe_load(block)
    except yaml.YAMLError as exc:
        raise FrontmatterError(f"invalid YAML in frontmatter: {exc}") from exc
    if not isinstance(loaded, dict):
        raise FrontmatterError("frontmatter must be a mapping")
    return loaded, body
