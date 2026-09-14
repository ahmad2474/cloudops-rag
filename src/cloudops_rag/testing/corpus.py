"""A tiny in-memory corpus with one restricted document, for tests and offline demos."""

from datetime import date

from cloudops_rag.chunking import chunk_document
from cloudops_rag.ingestion.documents import DocumentMetadata, DocumentType, Role, Status
from cloudops_rag.ingestion.parsers.models import ParsedDocument
from cloudops_rag.providers.base import EmbeddingProvider, SearchProvider


def make_doc(
    doc_id: str,
    title: str,
    body: str,
    *,
    permissions: list[Role],
    document_type: DocumentType = "runbook",
    version: str | None = None,
    status: Status = "active",
) -> ParsedDocument:
    meta = DocumentMetadata(
        document_id=doc_id,
        title=title,
        source="acme",
        document_type=document_type,
        version=version,
        permissions=permissions,
        status=status,
        created_at=date(2026, 1, 1),
        updated_at=date(2026, 2, 1),
    )
    return ParsedDocument(
        metadata=meta, body=body, source_path=f"{doc_id}.md", content_hash="sha256:" + doc_id
    )


CORPUS = [
    make_doc(
        "eks-pod-networking",
        "EKS pod networking runbook",
        "## Symptoms\n\nPods stuck in Pending with failed to assign an IP address to pod. "
        "Check awscni_no_available_ip_addresses on the node.\n\n"
        "## Fix\n\nAdd a pod subnet in the exhausted AZ.\n",
        permissions=["developer", "platform-engineer", "security-admin"],
        version="1.31",
    ),
    make_doc(
        "break-glass-procedure",
        "Break-glass procedure",
        "## Credentials\n\nBreak-glass users acme-breakglass-1 and acme-breakglass-2 hold "
        "sealed envelope passwords.\n",
        permissions=["security-admin"],
        document_type="policy",
    ),
    make_doc(
        "rds-connection-failure",
        "RDS connection failure runbook",
        "## Limits\n\nFATAL remaining connection slots are reserved means max_connections "
        "reached on the RDS instance.\n",
        permissions=["developer", "platform-engineer", "security-admin"],
    ),
]


async def seed_search(search: SearchProvider, embedding: EmbeddingProvider) -> None:
    for doc in CORPUS:
        cd = chunk_document(doc)
        vecs = await embedding.embed_documents([c.embedding_text for c in cd.chunks])
        await search.index_chunks(cd.chunks, vecs)
        await search.index_parents(cd.parents)
    await search.refresh()
