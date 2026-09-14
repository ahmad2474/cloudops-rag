import pytest

from cloudops_rag.ingestion.frontmatter import FrontmatterError, split_frontmatter


def test_splits_metadata_and_body() -> None:
    meta, body = split_frontmatter("---\ntitle: X\ntags: [a, b]\n---\n# Heading\n\ntext\n")
    assert meta == {"title": "X", "tags": ["a", "b"]}
    assert body == "# Heading\n\ntext\n"


def test_body_may_contain_horizontal_rules() -> None:
    _, body = split_frontmatter("---\nk: v\n---\npara\n\n---\n\nmore\n")
    assert "---" in body


def test_missing_frontmatter_is_an_error() -> None:
    with pytest.raises(FrontmatterError, match="must start"):
        split_frontmatter("# no frontmatter\n")


def test_unterminated_block_is_an_error() -> None:
    with pytest.raises(FrontmatterError, match="unterminated"):
        split_frontmatter("---\nk: v\n")


def test_non_mapping_frontmatter_is_an_error() -> None:
    with pytest.raises(FrontmatterError, match="mapping"):
        split_frontmatter("---\n- a\n- b\n---\nbody\n")
