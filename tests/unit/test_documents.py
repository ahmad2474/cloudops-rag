from datetime import date

import pytest
from pydantic import ValidationError

from cloudops_rag.ingestion.documents import DocumentMetadata, IncidentMeta, content_hash

BASE = {
    "document_id": "eks-pod-networking",
    "title": "EKS Pod Networking Runbook",
    "source": "acme",
    "document_type": "runbook",
    "permissions": ["platform-engineer"],
    "created_at": date(2026, 1, 5),
    "updated_at": date(2026, 3, 1),
}


def test_valid_metadata_parses() -> None:
    m = DocumentMetadata.model_validate(BASE)
    assert m.environment == "all"
    assert m.status == "active"


def test_unknown_keys_are_rejected() -> None:
    with pytest.raises(ValidationError, match="extra"):
        DocumentMetadata.model_validate({**BASE, "owner": "someone"})


def test_permissions_must_be_known_roles_and_non_empty() -> None:
    with pytest.raises(ValidationError):
        DocumentMetadata.model_validate({**BASE, "permissions": []})
    with pytest.raises(ValidationError):
        DocumentMetadata.model_validate({**BASE, "permissions": ["root"]})


def test_document_id_is_kebab_case() -> None:
    with pytest.raises(ValidationError):
        DocumentMetadata.model_validate({**BASE, "document_id": "EKS_Networking"})


def test_updated_at_cannot_precede_created_at() -> None:
    with pytest.raises(ValidationError, match="before created_at"):
        DocumentMetadata.model_validate({**BASE, "updated_at": date(2025, 1, 1)})


def test_duplicate_tags_rejected() -> None:
    with pytest.raises(ValidationError, match="duplicate"):
        DocumentMetadata.model_validate({**BASE, "tags": ["eks", "eks"]})


def test_incident_meta_requires_incident_id_format() -> None:
    with pytest.raises(ValidationError):
        IncidentMeta(
            incident_id="1042",
            severity="SEV-2",
            detected_at="2026-02-01T10:00:00Z",
            services=["eks"],
            root_cause_category="capacity",
        )


def test_content_hash_ignores_trailing_whitespace_and_outer_blank_lines() -> None:
    a = content_hash("# Title\n\nBody line.  \n\n")
    b = content_hash("\n# Title\n\nBody line.\n")
    assert a == b
    assert a.startswith("sha256:")
    assert content_hash("different") != a
