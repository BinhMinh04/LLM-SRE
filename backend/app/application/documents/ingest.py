"""IngestDocument use case: split -> embed -> store (RAG slice 1).

Depends only on domain (chunking rule + ports). No framework/DB/provider imports, so it is
unit-testable with a fake embedder and repository.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from app.domain.documents.chunking import DEFAULT_CHUNK_SIZE, DEFAULT_OVERLAP, chunk_markdown
from app.domain.documents.entities import Document, EmbeddedChunk
from app.domain.documents.ports import DocumentRepository, Embedder
from app.domain.shared import UnitOfWork


class EmptyDocumentError(ValueError):
    """The document produced no chunks (empty/whitespace content)."""


@dataclass
class IngestDocument:
    documents: DocumentRepository
    embedder: Embedder
    uow: UnitOfWork
    chunk_size: int = DEFAULT_CHUNK_SIZE
    overlap: int = DEFAULT_OVERLAP

    async def execute(
        self,
        *,
        title: str,
        source_type: str,
        service: str | None,
        tags: Sequence[str],
        content: str,
    ) -> tuple[Document, int]:
        """Chunk + embed + persist one document. Returns the stored document and its chunk count."""
        texts = chunk_markdown(content, self.chunk_size, self.overlap)
        if not texts:
            raise EmptyDocumentError("document content produced no chunks")

        vectors = await self.embedder.embed_documents(texts)
        chunks = [
            EmbeddedChunk(index=i, content=text, embedding=vector)
            for i, (text, vector) in enumerate(zip(texts, vectors))
        ]

        document = await self.documents.add(
            Document(title=title, source_type=source_type, service=service, tags=list(tags)),
            chunks,
        )
        await self.uow.commit()
        return document, len(chunks)
