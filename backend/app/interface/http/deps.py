"""FastAPI dependency wiring — the composition root that assembles use cases from adapters.

This is the only place the concrete infrastructure (SQLAlchemy repos, Bedrock analyzer, system
clock) is bound to the domain ports. Tests override `get_session` and `get_analyzer` to run against
a disposable DB without calling Bedrock.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.incidents.ingest import IngestIncident
from app.domain.incidents.ports import Analyzer, IncidentRepository
from app.infrastructure.clock import SystemClock
from app.infrastructure.config import get_settings
from app.infrastructure.db.repositories import (
    SqlAlchemyAnalysisCacheRepository,
    SqlAlchemyIncidentRepository,
    SqlAlchemyUnitOfWork,
)
from app.infrastructure.db.session import SessionLocal
from app.infrastructure.llm.bedrock_analyzer import BedrockAnalyzer


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async DB session for the request."""
    async with SessionLocal() as session:
        yield session


def get_analyzer() -> Analyzer:
    """The analysis backend. M2 = single Bedrock call; M3's LangGraph analyzer swaps in here;
    tests override it to avoid calling Bedrock."""
    return BedrockAnalyzer(get_settings())


def get_incident_repository(
    session: AsyncSession = Depends(get_session),
) -> IncidentRepository:
    return SqlAlchemyIncidentRepository(session)


def get_ingest_incident(
    session: AsyncSession = Depends(get_session),
    analyzer: Analyzer = Depends(get_analyzer),
) -> IngestIncident:
    settings = get_settings()
    return IngestIncident(
        incidents=SqlAlchemyIncidentRepository(session),
        cache=SqlAlchemyAnalysisCacheRepository(session),
        analyzer=analyzer,
        clock=SystemClock(),
        uow=SqlAlchemyUnitOfWork(session),
        cache_ttl_seconds=settings.cache_ttl_seconds,
    )
