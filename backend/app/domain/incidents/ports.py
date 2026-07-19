"""Ports (interfaces) the incident use cases depend on. Implemented in the infrastructure layer.

Defining these here inverts the dependency: the application layer talks to abstractions owned by the
domain, and infrastructure adapters (SQLAlchemy, Bedrock, system clock) implement them. Inner layers
never import concrete clients.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Protocol

from app.domain.incidents.entities import Analysis, AnalysisDraft, Incident
from app.domain.shared import Clock, UnitOfWork  # re-exported for existing imports

__all__ = [
    "Analyzer",
    "IncidentRepository",
    "AnalysisCacheRepository",
    "Clock",
    "UnitOfWork",
]


class Analyzer(Protocol):
    """Produces an analysis draft for an incident context (M2: one LLM call; M3: the agent graph)."""

    async def analyze(self, context: dict) -> AnalysisDraft: ...


class IncidentRepository(Protocol):
    """Persistence for incidents and their analyses."""

    async def add(self, incident: Incident) -> Incident: ...

    async def get(self, incident_id: uuid.UUID) -> Incident | None: ...

    async def list(
        self,
        *,
        service: str | None = None,
        severity: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[tuple[Incident, Analysis | None]]: ...

    async def add_analysis(self, analysis: Analysis) -> Analysis: ...

    async def latest_analysis(self, incident_id: uuid.UUID) -> Analysis | None: ...

    async def set_status(self, incident_id: uuid.UUID, status: str) -> None: ...


class AnalysisCacheRepository(Protocol):
    """Fingerprint-keyed cache mapping to a previously computed analysis, honoring a TTL."""

    async def get_valid(self, fingerprint: str, now: datetime) -> Analysis | None: ...

    async def put(self, fingerprint: str, analysis_id: uuid.UUID, expires_at: datetime) -> None: ...
