from pydantic import BaseModel, ConfigDict, Field

from cloudops_rag.ingestion.documents import DocumentType, Environment, Role, SourceName


class ChunkBase(BaseModel):
    """Fields shared by parents and children — everything retrieval filters or cites on."""

    model_config = ConfigDict(frozen=True)

    document_id: str
    title: str
    source: SourceName
    source_url: str | None
    document_type: DocumentType
    version: str | None
    environment: Environment
    permissions: list[Role]
    status: str
    updated_at: str
    content_hash: str
    section_path: list[str] = Field(description="Heading trail from H1 down, excluding title")
    content: str
    token_count: int


class ParentChunk(ChunkBase):
    parent_id: str
    child_ids: list[str]


class Chunk(ChunkBase):
    chunk_id: str
    parent_id: str
    position: int = Field(description="0-based order within the document")

    @property
    def embedding_text(self) -> str:
        """What gets embedded: title + heading trail gives the vector its context."""
        trail = " > ".join(self.section_path)
        head = f"{self.title} — {trail}" if trail else self.title
        return f"{head}\n\n{self.content}"


class ChunkedDocument(BaseModel):
    model_config = ConfigDict(frozen=True)

    document_id: str
    content_hash: str
    parents: list[ParentChunk]
    chunks: list[Chunk]
