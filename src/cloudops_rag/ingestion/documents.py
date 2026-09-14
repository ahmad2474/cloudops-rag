"""Document identity model. Every document in the corpus — synthetic or public — carries this."""

import hashlib
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Role = Literal["developer", "platform-engineer", "security-admin"]
ROLES: tuple[Role, ...] = ("developer", "platform-engineer", "security-admin")

SourceName = Literal["acme", "aws", "kubernetes", "terraform"]
DocumentType = Literal[
    "runbook",
    "architecture",
    "policy",
    "postmortem",
    "troubleshooting",
    "incident",
    "technical_documentation",
    "adversarial",
]
Environment = Literal["production", "staging", "development", "all"]
Status = Literal["active", "deprecated", "draft"]
Severity = Literal["SEV-1", "SEV-2", "SEV-3", "SEV-4"]

DOCUMENT_ID_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


class IncidentMeta(BaseModel):
    """Structured fields only incident documents carry."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    incident_id: str = Field(pattern=r"^INC-\d{4}$")
    severity: Severity
    detected_at: str  # ISO-8601 with timezone; kept as str to preserve the author's precision
    resolved_at: str | None = None
    services: list[str] = Field(min_length=1)
    root_cause_category: str


class DocumentMetadata(BaseModel):
    """Frontmatter of a corpus document. Strict: unknown keys are errors."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    document_id: str = Field(pattern=DOCUMENT_ID_PATTERN)
    title: str = Field(min_length=3)
    source: SourceName
    source_url: str | None = None
    document_type: DocumentType
    version: str | None = None
    environment: Environment = "all"
    permissions: list[Role] = Field(min_length=1)
    status: Status = "active"
    supersedes: str | None = Field(default=None, pattern=DOCUMENT_ID_PATTERN)
    created_at: date
    updated_at: date
    tags: list[str] = Field(default_factory=list)
    related: list[str] = Field(default_factory=list)
    license: str | None = None
    incident: IncidentMeta | None = None

    @field_validator("permissions", "tags", "related")
    @classmethod
    def _no_duplicates(cls, v: list[str]) -> list[str]:
        if len(set(v)) != len(v):
            raise ValueError("duplicate entries")
        return v

    @field_validator("updated_at")
    @classmethod
    def _updated_not_before_created(cls, v: date, info: object) -> date:
        # pydantic passes ValidationInfo; typed loosely to keep mypy strict happy without imports
        data = getattr(info, "data", {})
        created = data.get("created_at")
        if created is not None and v < created:
            raise ValueError("updated_at is before created_at")
        return v


class ManifestEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    metadata: DocumentMetadata
    path: str
    content_hash: str
    word_count: int
    fetched: bool = True


class Manifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    generated_at: str
    documents: list[ManifestEntry]

    def ids(self) -> set[str]:
        return {d.metadata.document_id for d in self.documents}


def content_hash(body: str) -> str:
    """Stable hash of the document body (not the frontmatter) — drives change detection."""
    normalised = "\n".join(line.rstrip() for line in body.strip().splitlines())
    return "sha256:" + hashlib.sha256(normalised.encode("utf-8")).hexdigest()
