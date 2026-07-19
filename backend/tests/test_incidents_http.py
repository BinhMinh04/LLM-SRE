"""End-to-end HTTP tests for the incident endpoints against a real Postgres.

Overrides the interface-layer `get_session` and `get_analyzer` dependencies (no Bedrock call), then
drives the real FastAPI app through the interface -> application -> infrastructure layers. Skipped
when no database is reachable.
"""

import os

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.domain.incidents.entities import AnalysisDraft
from app.infrastructure.db.orm import (
    EMBED_DIM,
    AnalysisCacheRow,
    AnalysisRow,
    Base,
    DocChunkRow,
    DocumentRow,
    IncidentRow,
)
from app.interface.http.deps import get_analyzer, get_embedder, get_session
from app.main import app

pytestmark = pytest.mark.asyncio

_DB_URL = os.environ.get("TEST_DATABASE_URL") or os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://iim:iim@localhost:5432/iim"
)

_CTX = {
    "service": "GCM",
    "sample_logs": [{"message": "java.lang.OutOfMemoryError: Java heap space"}],
    "recent_deploy": {"version": "1.8.0"},
}


class _FakeAnalyzer:
    async def analyze(self, context: dict, evidence=None) -> AnalysisDraft:
        return AnalysisDraft(
            severity="critical",
            summary="GCM OOM after deploy",
            root_cause="heap regression in 1.8.0",
            recommended_action="roll back GCM",
            confidence="high",
            model_id="test-model",
        )


class _FakeEmbedder:
    async def embed_documents(self, texts):
        return [[0.1] * EMBED_DIM for _ in texts]

    async def embed_query(self, text):
        return [0.1] * EMBED_DIM


@pytest.fixture()
async def client():
    engine = create_async_engine(_DB_URL)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:  # noqa: BLE001
        await engine.dispose()
        pytest.skip(f"Postgres not reachable for HTTP test: {exc}")

    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        await s.execute(delete(AnalysisCacheRow))
        await s.execute(delete(AnalysisRow))
        await s.execute(delete(IncidentRow))
        await s.execute(delete(DocChunkRow))
        await s.execute(delete(DocumentRow))
        await s.commit()

    async def _override_session():
        async with maker() as s:
            yield s

    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_analyzer] = lambda: _FakeAnalyzer()
    app.dependency_overrides[get_embedder] = lambda: _FakeEmbedder()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()
    await engine.dispose()


async def test_post_get_and_cache_hit(client):
    r = await client.post("/api/incidents", json={"source": "manual", "context": _CTX})
    assert r.status_code == 201, r.text
    created = r.json()
    incident_id = created["incident_id"]
    assert created["status"] == "analyzed"
    assert created["stream"] == f"/api/incidents/{incident_id}/stream"

    r = await client.get(f"/api/incidents/{incident_id}")
    assert r.status_code == 200
    detail = r.json()
    assert detail["context"]["service"] == "GCM"
    analysis = detail["analysis"]
    assert analysis["_cache"] == "MISS"
    assert analysis["severity"] == "critical"
    assert analysis["confidence"] == pytest.approx(0.9)
    assert analysis["evidence"] == []

    r2 = await client.post("/api/incidents", json={"source": "manual", "context": _CTX})
    assert r2.status_code == 201
    r2_detail = await client.get(f"/api/incidents/{r2.json()['incident_id']}")
    assert r2_detail.json()["analysis"]["_cache"] == "HIT"

    r = await client.get("/api/incidents")
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 2
    assert items[0]["severity"] == "critical"
    assert items[0]["summary"] == "GCM OOM after deploy"

    r = await client.get("/api/incidents", params={"severity": "critical"})
    assert len(r.json()) == 2
    r = await client.get("/api/incidents", params={"severity": "info"})
    assert r.json() == []


async def test_missing_service_returns_422(client):
    r = await client.post("/api/incidents", json={"source": "manual", "context": {}})
    assert r.status_code == 422
    assert r.json()["detail"] == "context.service is required"
