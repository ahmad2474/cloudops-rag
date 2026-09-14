from cloudops_rag.providers.base import SearchFilters
from cloudops_rag.providers.opensearch import build_filter, chunk_mapping, parent_mapping


def test_acl_clause_is_always_first() -> None:
    clauses = build_filter(SearchFilters(roles=["developer"]))
    assert clauses[0] == {"terms": {"permissions": ["developer"]}}


def test_optional_filters_append_clauses() -> None:
    f = SearchFilters(
        roles=["developer", "platform-engineer"],
        document_types=["runbook"],
        environments=["production"],
        version="1.31",
        exclude_adversarial=True,
        statuses=None,
    )
    clauses = build_filter(f)
    assert {"terms": {"document_type": ["runbook"]}} in clauses
    assert {"terms": {"environment": ["production", "all"]}} in clauses
    assert {"terms": {"version": ["1.31"]}} in clauses
    assert {"bool": {"must_not": {"term": {"document_type": "adversarial"}}}} in clauses
    assert not any("status" in c.get("terms", {}) for c in clauses)


def test_mappings_are_strict_and_dimension_driven() -> None:
    m = chunk_mapping(512)
    assert m["mappings"]["dynamic"] == "strict"
    assert m["mappings"]["properties"]["embedding"]["dimension"] == 512
    assert m["mappings"]["properties"]["content"]["fields"]["exact"]["analyzer"] == "technical"
    assert parent_mapping()["mappings"]["properties"]["content"]["index"] is False
