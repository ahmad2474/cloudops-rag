"""Evaluation dataset schema. Relevance is judged at document level: stable across chunkers."""

import json
from collections import Counter
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from cloudops_rag.ingestion.documents import Role

Category = Literal[
    "direct_lookup",
    "troubleshooting",
    "multi_document",
    "exact_terminology",
    "version_sensitive",
    "incident_retrieval",
    "conflicting_documents",
    "no_answer",
    "security",
    "prompt_injection",
]
CATEGORIES: tuple[Category, ...] = (
    "direct_lookup",
    "troubleshooting",
    "multi_document",
    "exact_terminology",
    "version_sensitive",
    "incident_retrieval",
    "conflicting_documents",
    "no_answer",
    "security",
    "prompt_injection",
)


class EvalItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=r"^q-\d{3,4}$")
    question: str = Field(min_length=8)
    category: Category
    expected_document_ids: list[str] = Field(default_factory=list)
    should_abstain: bool = False
    role: Role = "developer"
    must_not_cite: list[str] = Field(
        default_factory=list, description="Documents that must never appear (ACL / injection)"
    )
    answer_must_contain: list[str] = Field(
        default_factory=list, description="Case-insensitive substrings a correct answer includes"
    )
    answer_must_not_contain: list[str] = Field(default_factory=list)
    notes: str = ""

    @model_validator(mode="after")
    def _consistent(self) -> "EvalItem":
        if self.should_abstain and self.expected_document_ids:
            raise ValueError(f"{self.id}: should_abstain items must not expect documents")
        if not self.should_abstain and not self.expected_document_ids:
            raise ValueError(f"{self.id}: non-abstain items need expected_document_ids")
        return self


class EvalDataset(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str
    items: list[EvalItem]

    def by_category(self) -> dict[str, int]:
        return dict(Counter(i.category for i in self.items))

    def ids(self) -> set[str]:
        return {i.id for i in self.items}


def load_dataset(path: Path) -> EvalDataset:
    ds = EvalDataset.model_validate_json(path.read_text(encoding="utf-8"))
    ids = [i.id for i in ds.items]
    dupes = [k for k, v in Counter(ids).items() if v > 1]
    if dupes:
        raise ValueError(f"duplicate question ids: {dupes}")
    return ds


def validate_against_manifest(ds: EvalDataset, known_document_ids: set[str]) -> list[str]:
    problems: list[str] = []
    for item in ds.items:
        for did in [*item.expected_document_ids, *item.must_not_cite]:
            if did not in known_document_ids:
                problems.append(f"{item.id}: unknown document '{did}'")
    return problems


def dump_dataset(ds: EvalDataset, path: Path) -> None:
    path.write_text(json.dumps(ds.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")
