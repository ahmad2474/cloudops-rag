"""Test support: a tiny deterministic corpus and a seeding helper. Used by tests and demos."""

from cloudops_rag.testing.corpus import (
    CORPUS,
    TEST_PASSWORD,
    make_doc,
    seed_search,
    test_users_json,
)

__all__ = ["CORPUS", "TEST_PASSWORD", "make_doc", "seed_search", "test_users_json"]
