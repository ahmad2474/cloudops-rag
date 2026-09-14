from pydantic import BaseModel, ConfigDict

from cloudops_rag.ingestion.documents import DocumentMetadata


class ParsedDocument(BaseModel):
    """Normalised Markdown body plus the manifest metadata. Title always comes from the manifest."""

    model_config = ConfigDict(frozen=True)

    metadata: DocumentMetadata
    body: str
    source_path: str
    content_hash: str = ""

    @property
    def title(self) -> str:
        return self.metadata.title
