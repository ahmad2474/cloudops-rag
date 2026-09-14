import pytest

from cloudops_rag.retrieval.fusion import rrf, weighted


def test_rrf_hand_computed() -> None:
    fused = rrf([["a", "b", "c"], ["b", "d"]], k=60)
    scores = dict(fused)
    assert scores["b"] == pytest.approx(1 / 62 + 1 / 61)
    assert scores["a"] == pytest.approx(1 / 61)
    assert scores["d"] == pytest.approx(1 / 62)
    assert scores["c"] == pytest.approx(1 / 63)
    assert [c for c, _ in fused] == ["b", "a", "d", "c"]


def test_rrf_ties_break_deterministically_by_id() -> None:
    fused = rrf([["x"], ["y"]])
    assert [c for c, _ in fused] == ["x", "y"]


def test_weighted_normalises_each_source_and_combines() -> None:
    vec = {"a": 0.9, "b": 0.5, "c": 0.1}  # → a=1, b=0.5, c=0
    bm = {"c": 20.0, "a": 10.0}  # → c=1, a=0
    fused = dict(weighted([vec, bm], [0.5, 0.5]))
    assert fused["a"] == pytest.approx(0.5)
    assert fused["c"] == pytest.approx(0.5)
    assert fused["b"] == pytest.approx(0.25)


def test_weighted_handles_constant_scores_and_bad_weights() -> None:
    assert dict(weighted([{"a": 3.0, "b": 3.0}], [1.0])) == {"a": 1.0, "b": 1.0}
    with pytest.raises(ValueError):
        weighted([{"a": 1.0}], [0.0])
    with pytest.raises(ValueError):
        weighted([{"a": 1.0}], [1.0, 1.0])
