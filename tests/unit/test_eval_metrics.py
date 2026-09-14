import math

import pytest

from cloudops_rag.evaluation.metrics import (
    citation_precision,
    citation_recall,
    dedupe_keep_order,
    hit_at_k,
    mrr,
    ndcg_at_k,
    percentile,
    precision_at_k,
    recall_at_k,
)

RANKED = ["a", "b", "c", "d", "e"]


def test_recall_at_k_hand_computed() -> None:
    assert recall_at_k(RANKED, {"a", "c", "z"}, 5) == pytest.approx(2 / 3)
    assert recall_at_k(RANKED, {"a", "c", "z"}, 2) == pytest.approx(1 / 3)
    assert recall_at_k(RANKED, set(), 5) == 0.0


def test_precision_and_hit() -> None:
    assert precision_at_k(RANKED, {"a", "c"}, 4) == 0.5
    assert hit_at_k(RANKED, {"e"}, 4) == 0.0
    assert hit_at_k(RANKED, {"e"}, 5) == 1.0


def test_mrr_first_relevant_rank() -> None:
    assert mrr(RANKED, {"c"}) == pytest.approx(1 / 3)
    assert mrr(RANKED, {"a", "c"}) == 1.0
    assert mrr(RANKED, {"z"}) == 0.0


def test_ndcg_hand_computed() -> None:
    # relevant at ranks 1 and 3 of 3 → DCG = 1 + 1/log2(4) ; IDCG = 1 + 1/log2(3)
    got = ndcg_at_k(["a", "b", "c"], {"a", "c"}, 3)
    expected = (1 + 1 / math.log2(4)) / (1 + 1 / math.log2(3))
    assert got == pytest.approx(expected)
    assert ndcg_at_k(["a", "b"], {"a", "b"}, 2) == 1.0
    assert ndcg_at_k(["x"], {"a"}, 1) == 0.0


def test_citation_metrics() -> None:
    assert citation_precision(["a", "a", "z"], {"a"}) == 0.5
    assert citation_recall(["a"], {"a", "b"}) == 0.5
    assert citation_precision([], {"a"}) == 0.0


def test_helpers() -> None:
    assert dedupe_keep_order(["b", "a", "b", "c", "a"]) == ["b", "a", "c"]
    assert percentile([10, 20, 30, 40], 50) == 20
    assert percentile([10, 20, 30, 40], 95) == 40
    assert percentile([], 50) == 0.0
