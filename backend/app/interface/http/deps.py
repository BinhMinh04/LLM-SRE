"""FastAPI dependency wiring — the composition root that assembles use cases from adapters.

This is the only place the concrete infrastructure (SQLAlchemy repos, Bedrock analyzer, system
clock) is bound to the domain ports. Tests override `get_session` and `get_analyzer` to run against
a disposable DB without calling Bedrock.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.documents.ingest import IngestDocument
from app.application.incidents.analyze_rag import IngestIncidentWithRag
from app.domain.documents.ports import DocumentRepository, Embedder, Retriever
from app.domain.incidents.ports import Analyzer, IncidentRepository
from app.infrastructure.clock import SystemClock
from app.infrastructure.config import Settings, get_settings
from app.infrastructure.db.repositories import (
    SqlAlchemyAnalysisCacheRepository,
    SqlAlchemyDocumentRepository,
    SqlAlchemyIncidentRepository,
    SqlAlchemyRetriever,
    SqlAlchemyUnitOfWork,
)
from app.infrastructure.db.session import SessionLocal
from app.infrastructure.llm.bedrock_analyzer import BedrockAnalyzer
from app.infrastructure.llm.deepseek_analyzer import DeepSeekAnalyzer
from app.infrastructure.llm.jina_embedder import JinaEmbedder
from app.infrastructure.llm.titan_embedder import TitanEmbedder


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async DB session for the request."""
    async with SessionLocal() as session:
        yield session


def select_analyzer(settings: Settings) -> Analyzer:
    """Pick the Analyzer adapter from config (decision 0016). Pure — unit-testable."""
    if settings.llm_provider == "deepseek":
        return DeepSeekAnalyzer(settings)
    return BedrockAnalyzer(settings)


def get_analyzer() -> Analyzer:
    """The analysis backend, selected by LLM_PROVIDER. M3's LangGraph analyzer swaps in here;
    tests override it to avoid calling a real provider."""
    return select_analyzer(get_settings())


def select_embedder(settings: Settings) -> Embedder:
    """Pick the Embedder adapter from config (decision 0016). Pure — unit-testable."""
    if settings.embedding_provider == "jina":
        return JinaEmbedder(settings)
    return TitanEmbedder(settings)


def get_embedder() -> Embedder:
    """The embedding backend, selected by EMBEDDING_PROVIDER. Tests override it to avoid a real call."""
    return select_embedder(get_settings())


def get_incident_repository(
    session: AsyncSession = Depends(get_session),
) -> IncidentRepository:
    return SqlAlchemyIncidentRepository(session)


def get_ingest_incident(
    session: AsyncSession = Depends(get_session),
    analyzer: Analyzer = Depends(get_analyzer),
    embedder: Embedder = Depends(get_embedder),
) -> IngestIncidentWithRag:
    """POST /api/incidents flow: cache-first, RAG-grounded analysis (M3). Degrades to the M2
    single-call baseline when no documents match."""
    settings = get_settings()
    return IngestIncidentWithRag(
        incidents=SqlAlchemyIncidentRepository(session),
        cache=SqlAlchemyAnalysisCacheRepository(session),
        analyzer=analyzer,
        embedder=embedder,
        retriever=SqlAlchemyRetriever(session),
        clock=SystemClock(),
        uow=SqlAlchemyUnitOfWork(session),
        cache_ttl_seconds=settings.cache_ttl_seconds,
    )


def get_document_repository(
    session: AsyncSession = Depends(get_session),
) -> DocumentRepository:
    return SqlAlchemyDocumentRepository(session)


def get_retriever(session: AsyncSession = Depends(get_session)) -> Retriever:
    return SqlAlchemyRetriever(session)


def get_ingest_document(
    session: AsyncSession = Depends(get_session),
    embedder: Embedder = Depends(get_embedder),
) -> IngestDocument:
    return IngestDocument(
        documents=SqlAlchemyDocumentRepository(session),
        embedder=embedder,
        uow=SqlAlchemyUnitOfWork(session),
    )
