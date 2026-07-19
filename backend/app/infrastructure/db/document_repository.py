"""SQLAlchemy document repository + pgvector retriever (implements the RAG ports).

`SqlAlchemyDocumentRepository` persists a document and its chunks and lists documents with chunk
counts. `SqlAlchemyRetriever` runs the cosine-similarity search from docs/product/rag.md 7.3 using
pgvector's `<=>` (`cosine_distance`), pre-filtered by service/source_type. No ORM type leaks out.
"""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.documents.entities import Document, EmbeddedChunk, RetrievedChunk
from app.infrastructure.db.orm import DocChunkRow, DocumentRow


def _document_to_domain(row: DocumentRow) -> Document:
    return Document(
        title=row.title,
        source_type=row.source_type,
        service=row.service,
        tags=list(row.tags or []),
        id=row.id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlAlchemyDocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def add(self, document: Document, chunks: list[EmbeddedChunk]) -> Document:
        row = DocumentRow(
            title=document.title,
            source_type=document.source_type,
            service=document.service,
            tags=list(document.tags),
        )
        self._s.add(row)
        await self._s.flush()
        await self._s.refresh(row)
        for chunk in chunks:
            self._s.add(
                DocChunkRow(
                    document_id=row.id,
                    source_type=row.source_type,
                    service=row.service,
                    chunk_index=chunk.index,
                    content=chunk.content,
                    embedding=chunk.embedding,
                )
            )
        await self._s.flush()
        return _document_to_domain(row)

    async def list(self) -> list[tuple[Document, int]]:
        stmt = (
            select(DocumentRow, func.count(DocChunkRow.id))
            .join(DocChunkRow, DocChunkRow.document_id == DocumentRow.id, isouter=True)
            .group_by(DocumentRow.id)
            .order_by(DocumentRow.created_at.desc())
        )
        rows = (await self._s.execute(stmt)).all()
        return [(_document_to_domain(doc), count) for doc, count in rows]


class SqlAlchemyRetriever:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def search(
        self,
        *,
        query_embedding: list[float],
        service: str | None,
        source_type: str | None = None,
        top_k: int = 6,
        min_similarity: float = 0.0,
    ) -> list[RetrievedChunk]:
        distance = DocChunkRow.embedding.cosine_distance(query_embedding)
        stmt = select(DocChunkRow, distance.label("distance"))
        if service is not None:
            stmt = stmt.where(or_(DocChunkRow.service == service, DocChunkRow.service.is_(None)))
        if source_type is not None:
            stmt = stmt.where(DocChunkRow.source_type == source_type)
        stmt = stmt.order_by(distance).limit(top_k)

        rows = (await self._s.execute(stmt)).all()
        results: list[RetrievedChunk] = []
        for row, dist in rows:
            similarity = 1.0 - float(dist)
            if similarity >= min_similarity:
                results.append(
                    RetrievedChunk(
                        id=row.id,
                        document_id=row.document_id,
                        source_type=row.source_type,
                        service=row.service,
                        content=row.content,
                        similarity=similarity,
                    )
                )
        return results
