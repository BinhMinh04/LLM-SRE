"""Integration test: document ingest (repo) + pgvector retrieval against real Postgres.

Uses a deterministic one-hot embedder (identical text -> identical vector, different text ->
orthogonal) so cosine ranking and the service filter are exactly assertable. No Bedrock call.
Skipped when no database is reachable.
"""

import hashlib
import os

import pytest
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.application.documents.ingest import IngestDocument
from app.infrastructure.db.orm import EMBED_DIM, Base, DocChunkRow, DocumentRow
from app.infrastructure.db.repositories import (
    SqlAlchemyDocumentRepository,
    SqlAlchemyRetriever,
    SqlAlchemyUnitOfWork,
)

pytestmark = pytest.mark.asyncio

_DB_URL = os.environ.get("TEST_DATABASE_URL") or os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://iim:iim@localhost:5432/iim"
)

_DIM = EMBED_DIM


def _one_hot(s: str) -> list[float]:
    pos = int(hashlib.sha256(s.encode()).hexdigest(), 16) % _DIM
    vec = [0.0] * _DIM
    vec[pos] = 1.0
    return vec


class OneHotEmbedder:
    async def embed_documents(self, texts):
        return [_one_hot(t) for t in texts]

    async def embed_query(self, text):
        return _one_hot(text)


def _ingest(session, embedder):
    return IngestDocument(
        documents=SqlAlchemyDocumentRepository(session),
        embedder=embedder,
        uow=SqlAlchemyUnitOfWork(session),
    )


@pytest.fixture()
async def sessionmaker_fixture():
    engine = create_async_engine(_DB_URL)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:  # noqa: BLE001
        await engine.dispose()
        pytest.skip(f"Postgres not reachable for integration test: {exc}")

    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        await s.execute(delete(DocChunkRow))
        await s.execute(delete(DocumentRow))
        await s.commit()
    yield maker
    await engine.dispose()


async def test_ingest_then_retrieve_ranks_and_filters_by_service(sessionmaker_fixture):
    maker = sessionmaker_fixture
    embedder = OneHotEmbedder()

    gcm_text = "GCM heap OutOfMemory restart the service"
    async with maker() as s:
        await _ingest(s, embedder).execute(
            title="GCM Runbook", source_type="runbook", service="GCM", tags=[], content=gcm_text
        )
        await _ingest(s, embedder).execute(
            title="PAY Runbook",
            source_type="runbook",
            service="PAY",
            tags=[],
            content="PAY gateway timeout retry",
        )

    # Retrieve with the GCM chunk's own embedding, filtered to service GCM.
    async with maker() as s:
        retriever = SqlAlchemyRetriever(s)
        query = await embedder.embed_query(gcm_text)
        gcm_hits = await retriever.search(query_embedding=query, service="GCM")
        assert gcm_hits, "expected at least one GCM chunk"
        assert gcm_hits[0].content == gcm_text
        assert gcm_hits[0].similarity == pytest.approx(1.0, abs=1e-4)
        assert gcm_hits[0].service == "GCM"

        # Service filter excludes the GCM chunk when searching PAY.
        pay_hits = await retriever.search(query_embedding=query, service="PAY")
        assert all(h.content != gcm_text for h in pay_hits)

        # source_type filter + min_similarity threshold.
        strict = await retriever.search(
            query_embedding=query, service="GCM", source_type="runbook", min_similarity=0.99
        )
        assert [h.content for h in strict] == [gcm_text]


async def test_list_reports_chunk_counts(sessionmaker_fixture):
    maker = sessionmaker_fixture
    embedder = OneHotEmbedder()
    async with maker() as s:
        await _ingest(s, embedder).execute(
            title="Big Runbook",
            source_type="runbook",
            service="GCM",
            tags=["oom"],
            content="\n".join(f"line {i} content here" for i in range(120)),
        )
    async with maker() as s:
        rows = await SqlAlchemyDocumentRepository(s).list()
    assert len(rows) == 1
    document, count = rows[0]
    assert document.title == "Big Runbook"
    assert count >= 1
