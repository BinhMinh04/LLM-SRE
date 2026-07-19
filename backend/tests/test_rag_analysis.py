"""Tests for RAG-grounded analysis (US-011): query building, evidence rendering, RagAnalyzer."""

import os
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.application.incidents.rag_analyzer import RagAnalyzer
from app.domain.documents.entities import RetrievedChunk
from app.domain.incidents.entities import AnalysisDraft
from app.domain.incidents.prompts import build_retrieval_query, build_user_message
from app.infrastructure.db.orm import (
    EMBED_DIM,
    AnalysisCacheRow,
    AnalysisRow,
    Base,
    DocChunkRow,
    DocumentRow,
    IncidentRow,
)
from app.interface.http.deps import get_base_analyzer, get_embedder, get_session
from app.main import app

_CTX = {
    "service": "GCM",
    "sample_logs": [{"message": "java.lang.OutOfMemoryError: Java heap space"}],
    "recent_deploy": {"version": "1.8.0"},
}


def _chunk(title="GCM OOM Runbook", content="Roll back and raise memory.") -> RetrievedChunk:
    return RetrievedChunk(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        source_type="runbook",
        service="GCM",
        title=title,
        content=content,
        similarity=0.9,
    )


# --- unit: query + prompt (no DB) --------------------------------------------


def test_build_retrieval_query_uses_key_signals():
    q = build_retrieval_query(_CTX)
    assert "service GCM" in q
    assert "OutOfMemoryError" in q
    assert "deploy 1.8.0" in q


def test_build_user_message_renders_evidence_block():
    msg = build_user_message(_CTX, [_chunk()])
    assert "[RETRIEVED KNOWLEDGE]" in msg
    assert "[runbook: GCM OOM Runbook]" in msg
    assert "Roll back and raise memory." in msg


def test_build_user_message_without_evidence_has_no_block():
    assert "[RETRIEVED KNOWLEDGE]" not in build_user_message(_CTX)


# --- unit: RagAnalyzer with fakes (no DB) ------------------------------------


class _Embedder:
    async def embed_documents(self, texts):
        return [[0.1] * 4 for _ in texts]

    async def embed_query(self, text):
        return [0.1] * 4


class _Retriever:
    def __init__(self, chunk):
        self.chunk = chunk
        self.calls = []

    async def search(self, *, query_embedding, service, source_type=None, top_k=6, min_similarity=0.0):
        self.calls.append(service)
        return [self.chunk]


class _CapturingBase:
    def __init__(self):
        self.evidence = None

    async def analyze(self, context, evidence=None):
        self.evidence = evidence
        return AnalysisDraft(
            severity="critical",
            summary="s",
            root_cause="r [runbook: GCM OOM Runbook]",
            recommended_action="a",
            confidence="high",
            model_id="test",
        )


@pytest.mark.asyncio
async def test_rag_analyzer_retrieves_and_grounds():
    chunk = _chunk()
    base, retriever = _CapturingBase(), _Retriever(chunk)
    rag = RagAnalyzer(base=base, embedder=_Embedder(), retriever=retriever)

    draft = await rag.analyze(dict(_CTX))

    assert retriever.calls == ["GCM"]  # searched, filtered by service
    assert base.evidence == [chunk]  # evidence passed to the base analyzer
    assert draft.evidence_chunk_ids == (chunk.id,)  # reported on the draft


# --- http: ingest a doc, analyze, see the citation ---------------------------

_DB_URL = os.environ.get("TEST_DATABASE_URL") or os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://iim:iim@localhost:5432/iim"
)


class _ConstEmbedder:
    """All vectors identical -> any query retrieves any stored chunk (cosine = 1)."""

    async def embed_documents(self, texts):
        return [[0.2] * EMBED_DIM for _ in texts]

    async def embed_query(self, text):
        return [0.2] * EMBED_DIM


class _FakeBaseAnalyzer:
    async def analyze(self, context, evidence=None):
        cites = ", ".join(f"[{c.source_type}: {c.title}]" for c in (evidence or []))
        return AnalysisDraft(
            severity="critical",
            summary="GCM OOM",
            root_cause=f"heap regression {cites}".strip(),
            recommended_action="roll back",
            confidence="high",
            model_id="test-model",
        )


@pytest.mark.asyncio
async def test_analysis_cites_ingested_document():
    engine = create_async_engine(_DB_URL)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:  # noqa: BLE001
        await engine.dispose()
        pytest.skip(f"Postgres not reachable: {exc}")

    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        for tbl in (AnalysisCacheRow, AnalysisRow, IncidentRow, DocChunkRow, DocumentRow):
            await s.execute(delete(tbl))
        await s.commit()

    async def _override_session():
        async with maker() as s:
            yield s

    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_base_analyzer] = lambda: _FakeBaseAnalyzer()
    app.dependency_overrides[get_embedder] = lambda: _ConstEmbedder()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        doc = await c.post(
            "/api/documents",
            json={
                "title": "GCM OOM Runbook",
                "source_type": "runbook",
                "service": "GCM",
                "content": "# GCM OOM\nRoll back and raise container memory.",
            },
        )
        assert doc.status_code == 201, doc.text

        inc = await c.post("/api/incidents", json={"source": "manual", "context": _CTX})
        assert inc.status_code == 201
        detail = await c.get(f"/api/incidents/{inc.json()['incident_id']}")
        analysis = detail.json()["analysis"]

    app.dependency_overrides.clear()
    await engine.dispose()

    assert analysis["_cache"] == "MISS"
    assert len(analysis["evidence"]) == 1
    assert analysis["evidence"][0]["source_type"] == "runbook"
    assert analysis["evidence"][0]["title"] == "GCM OOM Runbook"
    assert "[runbook: GCM OOM Runbook]" in analysis["root_cause"]
